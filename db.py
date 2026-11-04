"""SQLite persistence, platform filtering, momentum calculation, CSV export, and granular stream history."""

import csv
import io
import os
import sqlite3
import time
from datetime import datetime

from config import COSTREAM_STREAMS, get_active_day_id

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")

# Confirmed bot attack windows on GoE YouTube
BOT_ATTACK_WINDOWS = [
    {
        "name": "Atak 1",
        "start": "2026-11-04 00:18:25",
        "end": "2026-11-04 00:39:09",
        "yt_start": 2152,
        "yt_end": 2166,
    },
    {
        "name": "Atak 2",
        "start": "2026-11-04 00:48:08",
        "end": "2026-11-04 01:06:51",
        "yt_start": 2140,
        "yt_end": 1785,
    },
]


def apply_adaptive_anomaly_detection(
    points: list[dict], enabled: bool = True
) -> list[dict]:
    """Adaptive rolling anomaly detector for Day 2+ stream points.
    Automatically detects sudden artificial viewer surges (>800 in <3 minutes)
    without corresponding Twitch movement and normalizes them to genuine baseline.
    """
    if len(points) < 8:
        return points

    import statistics

    yt_raw_series = []
    for p in points:
        raw_val = p.get("goe_total_raw", p.get("goe_total", 0))
        yt_raw_series.append(raw_val)

    in_spike = False
    spike_start = None
    base_start = 0
    spike_windows = []

    for i in range(5, len(points)):
        prev_pts = yt_raw_series[max(0, i - 10) : i]
        prev_median = statistics.median(prev_pts)
        curr = yt_raw_series[i]

        if not in_spike:
            if prev_median > 400 and (curr - prev_median) > 800:
                in_spike = True
                spike_start = i
                base_start = prev_median
        else:
            if curr <= base_start + 350 or (i - spike_start > 200):
                in_spike = False
                spike_windows.append((spike_start, i, base_start, curr, i - spike_start + 1))

    if in_spike:
        spike_windows.append(
            (spike_start, len(points) - 1, base_start, base_start, len(points) - spike_start + 1)
        )

    for s_idx, e_idx, b_start, b_end, dur_steps in spike_windows:
        for idx in range(s_idx, min(e_idx + 1, len(points))):
            p = points[idx]
            p["is_bot_attack"] = True
            p["goe_total_raw"] = p.get("goe_total_raw", p.get("goe_total", 0))

            if enabled and dur_steps > 1:
                prog = (idx - s_idx) / float(dur_steps)
                clean_yt = int(b_start + prog * (b_end - b_start))

                for sid, s in p.get("streams", {}).items():
                    if s.get("group") == "GOE" and s.get("platform") == "YouTube":
                        s["viewers_raw"] = s.get("viewers_raw", s.get("viewers", clean_yt))
                        s["viewers"] = clean_yt
                        s["is_bot_attack"] = True

                tw_v = p.get("streams", {}).get("goe_stream", {}).get("viewers", 0)
                p["goe_total"] = tw_v + clean_yt
                nerva_v = p.get("nerva_total", 0)
                p["total_viewers"] = p["goe_total"] + nerva_v
                p["diff"] = abs(p["goe_total"] - nerva_v)
                p["leader"] = "GOE" if p["goe_total"] > nerva_v else ("NERVA" if nerva_v > p["goe_total"] else "REMIS")
            elif not enabled:
                p["goe_total"] = p.get("goe_total_raw", p.get("goe_total", 0))
                nerva_v = p.get("nerva_total", 0)
                p["total_viewers"] = p["goe_total"] + nerva_v
                p["diff"] = abs(p["goe_total"] - nerva_v)

    return points


def filter_bot_attacks(points: list[dict], enabled: bool = True) -> list[dict]:
    """Normalizes the 2 YouTube viewbotting spikes for GoE:
    - Attack 1: 2026-11-04 00:18:25 to 2026-11-04 00:39:09
    - Attack 2: 2026-11-04 00:48:08 to 2026-11-04 01:06:51
    Interpolates genuine YouTube baseline, keeps Twitch untouched, and strips corrupted post-stream VOD snapshots.
    """
    if not points:
        return []

    windows = []
    for w in BOT_ATTACK_WINDOWS:
        dt_s = datetime.strptime(w["start"], "%Y-%m-%d %H:%M:%S")
        dt_e = datetime.strptime(w["end"], "%Y-%m-%d %H:%M:%S")
        windows.append(
            {
                "start": dt_s,
                "end": dt_e,
                "dur": (dt_e - dt_s).total_seconds(),
                "yt_start": w["yt_start"],
                "yt_end": w["yt_end"],
            }
        )

    cleaned = []
    for pt in points:
        ts_str = pt.get("timestamp", "")
        # Drop any corrupted post-stream records (>15000 viewers after 03:00)
        if ts_str >= "2026-11-04 03:05:00" and (
            pt.get("goe_total", 0) > 10000 or pt.get("nerva_total", 0) > 15000
        ):
            continue

        try:
            dt = datetime.strptime(ts_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            cleaned.append(dict(pt))
            continue

        p = dict(pt)
        streams = {k: dict(v) for k, v in p.get("streams", {}).items()}
        # Mark costream streams (not counted in official duel)
        for cid, cinfo in COSTREAM_STREAMS.items():
            if cid in streams:
                streams[cid]["channel"] = cinfo.get(
                    "name", streams[cid].get("channel", "Co-stream")
                )
                streams[cid]["is_costream"] = True
                streams[cid]["is_curiosity"] = True

        nerva_tw = streams.get("nervarien", {}).get("viewers", 0)
        nerva_yt = 0
        for sid, s in streams.items():
            if s.get("group") == "NERVA" and s.get("platform") == "YouTube":
                if (
                    sid not in COSTREAM_STREAMS
                    and not s.get("is_costream")
                    and not s.get("is_curiosity")
                ):
                    nerva_yt += s.get("viewers", 0)
            elif sid in ("SGAaZFSc3Zk", "00uONX5EBiA"):
                nerva_yt += s.get("viewers", 0)

        nerva_tot = nerva_tw + nerva_yt
        p["nerva_total"] = nerva_tot

        # Locate GoE YouTube stream dynamically
        yt_stream = None
        yt_stream_id = None
        for sid, s in streams.items():
            if s.get("group") == "GOE" and s.get("platform") == "YouTube":
                yt_stream = s
                yt_stream_id = sid
                break
        if not yt_stream:
            if "I2E60nEUXWo" in streams:
                yt_stream = streams["I2E60nEUXWo"]
                yt_stream_id = "I2E60nEUXWo"
            elif "@gadaja_" in streams:
                yt_stream = streams["@gadaja_"]
                yt_stream_id = "@gadaja_"

        tw_stream = streams.get("goe_stream")

        goe_tot = p.get("goe_total", 0)
        p["goe_total_raw"] = p.get("goe_total_raw", goe_tot)
        p["is_bot_attack"] = False

        for w in windows:
            if w["start"] <= dt <= w["end"]:
                p["is_bot_attack"] = True
                if enabled and w["dur"] > 0:
                    prog = max(
                        0.0, min(1.0, (dt - w["start"]).total_seconds() / w["dur"])
                    )
                    clean_yt = int(w["yt_start"] + prog * (w["yt_end"] - w["yt_start"]))
                    tw_v = tw_stream.get("viewers", 0) if tw_stream else 0

                    if yt_stream and yt_stream_id:
                        yt_stream["viewers_raw"] = yt_stream.get(
                            "viewers_raw", yt_stream.get("viewers", clean_yt)
                        )
                        yt_stream["viewers"] = clean_yt
                        yt_stream["is_bot_attack"] = True
                        streams[yt_stream_id] = yt_stream

                    clean_goe = tw_v + clean_yt
                    p["goe_total"] = clean_goe
                elif not enabled:
                    raw_goe = p.get("goe_total_raw", p.get("goe_total", 0))
                    p["goe_total"] = raw_goe
                    if yt_stream:
                        yt_stream["viewers"] = yt_stream.get(
                            "viewers_raw", yt_stream.get("viewers", 0)
                        )
                break

        tot = p["goe_total"] + nerva_tot
        p["total_viewers"] = tot
        p["diff"] = abs(p["goe_total"] - nerva_tot)
        p["leader"] = (
            "GOE"
            if p["goe_total"] > nerva_tot
            else ("NERVA" if nerva_tot > p["goe_total"] else "REMIS")
        )
        p["ratio_goe"] = round((p["goe_total"] / tot * 100), 1) if tot > 0 else 50.0
        p["ratio_nerva"] = round((nerva_tot / tot * 100), 1) if tot > 0 else 50.0

        p["streams"] = streams
        cleaned.append(p)

    # For Day 2+ points, apply adaptive rolling anomaly detection
    day2_cutoff_str = "2026-11-04 12:00:00"
    day1_pts = [p for p in cleaned if p.get("timestamp", "") < day2_cutoff_str]
    day2_pts = [p for p in cleaned if p.get("timestamp", "") >= day2_cutoff_str]

    if day2_pts:
        day2_pts = apply_adaptive_anomaly_detection(day2_pts, enabled=enabled)
        return day1_pts + day2_pts

    return cleaned


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            unix_time REAL NOT NULL,
            total_viewers INTEGER NOT NULL,
            goe_total INTEGER NOT NULL,
            nerva_total INTEGER NOT NULL,
            diff INTEGER NOT NULL,
            leader TEXT NOT NULL,
            ratio_goe REAL NOT NULL,
            ratio_nerva REAL NOT NULL
        );
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS stream_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            group_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            viewers INTEGER NOT NULL,
            is_live INTEGER NOT NULL,
            title TEXT,
            avatar_url TEXT DEFAULT '',
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (id) ON DELETE CASCADE
        );
        """
        )
        try:
            conn.execute(
                "ALTER TABLE stream_records ADD COLUMN avatar_url TEXT DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE snapshots ADD COLUMN day_id TEXT DEFAULT 'day-1'")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE snapshots ADD COLUMN day_id TEXT DEFAULT 'day-1'")
        except sqlite3.OperationalError:
            pass

        conn.commit()


def save_snapshot(data: dict, day_id: str | None = None) -> int:
    """Saves a fresh scrape snapshot into SQLite with day association."""
    init_db()
    if day_id is None:
        day_id = get_active_day_id()

    now_ts = data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unix_time = time.time()

    goe = data["groups"].get("GOE", {})
    nerva = data["groups"].get("NERVA", {})
    goe_total = goe.get("total_viewers", 0)
    nerva_total = nerva.get("total_viewers", 0)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO snapshots (
                timestamp, unix_time, total_viewers, goe_total, nerva_total,
                diff, leader, ratio_goe, ratio_nerva, day_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                now_ts,
                unix_time,
                data.get("total_viewers", 0),
                goe_total,
                nerva_total,
                data.get("diff", 0),
                data.get("leader", ""),
                data.get("ratio_goe", 50.0),
                data.get("ratio_nerva", 50.0),
                day_id,
            ),
        )
        snapshot_id = cur.lastrowid

        for grp_key, grp in data.get("groups", {}).items():
            for st in grp.get("streams", []):
                cur.execute(
                    """
                    INSERT INTO stream_records (
                        snapshot_id, group_id, platform, channel_id,
                        channel_name, viewers, is_live, title, avatar_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        snapshot_id,
                        grp_key,
                        st.get("platform", ""),
                        st.get("id", ""),
                        st.get("channel", ""),
                        st.get("viewers", 0),
                        1 if st.get("is_live") else 0,
                        st.get("title", ""),
                        st.get("avatar_url", ""),
                    ),
                )
        conn.commit()
        return snapshot_id


def get_detailed_history(limit: int = 2000, day_id: str | None = None) -> list[dict]:
    """Retrieves chronological snapshots with granular per-stream viewer data, optionally filtered by day_id."""
    init_db()
    with get_connection() as conn:
        where_clause = ""
        params = []
        if day_id:
            where_clause = "WHERE day_id = ? "
            params.append(day_id)
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT s.id, s.timestamp, s.unix_time, s.total_viewers, s.goe_total, s.nerva_total, s.day_id,
                   r.channel_id, r.channel_name, r.platform, r.group_id, r.viewers, r.is_live
            FROM (SELECT * FROM snapshots {where_clause}ORDER BY id DESC LIMIT ?) s
            JOIN stream_records r ON s.id = r.snapshot_id
            ORDER BY s.id ASC
        """,
            tuple(params),
        ).fetchall()

        snapshots_map = {}
        for r in rows:
            sid = r["id"]
            if sid not in snapshots_map:
                snapshots_map[sid] = {
                    "id": sid,
                    "timestamp": r["timestamp"],
                    "unix_time": r["unix_time"],
                    "day_id": r.get("day_id", "day-1"),
                    "total_viewers": r["total_viewers"],
                    "goe_total": r["goe_total"],
                    "nerva_total": r["nerva_total"],
                    "streams": {},
                }
            snapshots_map[sid]["streams"][r["channel_id"]] = {
                "id": r["channel_id"],
                "channel": r["channel_name"],
                "viewers": r["viewers"],
                "platform": r["platform"],
                "group": r["group_id"],
                "is_live": bool(r["is_live"]),
            }
        return list(snapshots_map.values())


def get_history(limit: int = 500, platform: str = "ALL") -> list[dict]:
    """Retrieves chronological snapshots filtered by platform (ALL, Twitch, YouTube)."""
    init_db()
    platform_clean = platform.upper()

    with get_connection() as conn:
        if platform_clean == "ALL":
            rows = conn.execute(
                """
                SELECT * FROM snapshots ORDER BY id ASC LIMIT ?
            """,
                (limit,),
            ).fetchall()

            result = []
            for r in rows:
                result.append(
                    {
                        "id": r["id"],
                        "timestamp": r["timestamp"],
                        "unix_time": r["unix_time"],
                        "total_viewers": r["total_viewers"],
                        "goe_total": r["goe_total"],
                        "nerva_total": r["nerva_total"],
                        "diff": r["diff"],
                        "leader": r["leader"],
                        "ratio_goe": r["ratio_goe"],
                        "ratio_nerva": r["ratio_nerva"],
                    }
                )
            return result

        target_platform = "Twitch" if "TWITCH" in platform_clean else "YouTube"

        rows = conn.execute(
            """
            SELECT 
                s.id, s.timestamp, s.unix_time,
                COALESCE(SUM(CASE WHEN r.group_id = 'GOE' THEN r.viewers ELSE 0 END), 0) AS goe_total,
                COALESCE(SUM(CASE WHEN r.group_id = 'NERVA' THEN r.viewers ELSE 0 END), 0) AS nerva_total
            FROM snapshots s
            JOIN stream_records r ON s.id = r.snapshot_id
            WHERE r.platform = ?
            GROUP BY s.id
            ORDER BY s.id ASC
            LIMIT ?
        """,
            (target_platform, limit),
        ).fetchall()

        result = []
        for r in rows:
            goe_v = r["goe_total"]
            nerva_v = r["nerva_total"]
            tot = goe_v + nerva_v
            diff = abs(goe_v - nerva_v)
            leader = (
                "GOE" if goe_v > nerva_v else ("NERVA" if nerva_v > goe_v else "REMIS")
            )
            ratio_goe = round((goe_v / tot * 100), 1) if tot > 0 else 50.0
            ratio_nerva = round((nerva_v / tot * 100), 1) if tot > 0 else 50.0

            result.append(
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "unix_time": r["unix_time"],
                    "total_viewers": tot,
                    "goe_total": goe_v,
                    "nerva_total": nerva_v,
                    "diff": diff,
                    "leader": leader,
                    "ratio_goe": ratio_goe,
                    "ratio_nerva": ratio_nerva,
                }
            )
        return result


def get_summary_stats(
    platform: str = "ALL",
    custom_history: list[dict] | None = None,
    filter_bots: bool = True,
) -> dict:
    """Calculates peak, average, and summary statistics across recorded history per platform,
    with automatic bot attack filtering and corrupted snapshot removal."""
    if custom_history is not None:
        history = [dict(p) for p in custom_history]
    else:
        history = get_detailed_history(limit=5000)

    if filter_bots:
        history = filter_bot_attacks(history, enabled=True)
    else:
        history = filter_bot_attacks(history, enabled=False)

    if not history:
        return {
            "count": 0,
            "goe_peak": 0,
            "nerva_peak": 0,
            "goe_peak_time": "",
            "nerva_peak_time": "",
            "goe_avg": 0,
            "nerva_avg": 0,
            "start_time": "",
            "end_time": "",
            "goe_raw_peak": 0,
            "goe_raw_peak_time": "",
            "is_bot_filtered": filter_bots,
            "nerva_costream_peak": 0,
            "nerva_costream_peak_time": "",
            "nerva_costream_avg": 0,
            "tobias_costream_peak": 0,
            "tobias_costream_peak_time": "",
            "tobias_costream_avg": 0,
            "camp_peak": 0,
            "camp_peak_time": "",
            "camp_avg": 0,
        }

    goe_peak = 0
    goe_raw_peak = 0
    nerva_peak = 0
    goe_peak_time = ""
    goe_raw_peak_time = ""
    nerva_peak_time = ""
    goe_sum = 0
    nerva_sum = 0

    nerva_costream_peak = 0
    nerva_costream_peak_time = ""
    nerva_costream_sum = 0

    tobias_costream_peak = 0
    tobias_costream_peak_time = ""
    tobias_costream_sum = 0

    camp_peak = 0
    camp_peak_time = ""
    camp_sum = 0

    for pt in history:
        gv_clean = pt.get("goe_total", 0)
        gv_raw = pt.get("goe_total_raw", gv_clean)
        gv = gv_clean if filter_bots else gv_raw
        nv = pt.get("nerva_total", 0)
        ts_short = pt.get("timestamp", "").split(" ")[-1]
        if ":" in ts_short and len(ts_short) > 5:
            ts_short = ts_short[:5]  # HH:MM

        if gv > goe_peak:
            goe_peak = gv
            goe_peak_time = ts_short
        if gv_raw > goe_raw_peak:
            goe_raw_peak = gv_raw
            goe_raw_peak_time = ts_short
        if nv > nerva_peak:
            nerva_peak = nv
            nerva_peak_time = ts_short

        goe_sum += gv
        nerva_sum += nv

        # Co-stream metrics
        streams = pt.get("streams", {})
        nc_v = 0
        for vid in ("woX6jXefVdw", "N3i_DQlKL_U"):
            if vid in streams:
                nc_v = streams[vid].get("viewers", 0)
                break
        if nc_v == 0:
            for sid, s in streams.items():
                if sid != "ttobias_lol" and (
                    s.get("is_costream") or s.get("is_curiosity")
                ):
                    nc_v = s.get("viewers", 0)
                    break

        tb_v = streams.get("ttobias_lol", {}).get("viewers", 0)
        # Obóz Nervariena jest liczony bez Tobiasza (Tobiasz to osobny obóz)
        camp_v = nv + nc_v

        if nc_v > nerva_costream_peak:
            nerva_costream_peak = nc_v
            nerva_costream_peak_time = ts_short
        if tb_v > tobias_costream_peak:
            tobias_costream_peak = tb_v
            tobias_costream_peak_time = ts_short
        if camp_v > camp_peak:
            camp_peak = camp_v
            camp_peak_time = ts_short

        nerva_costream_sum += nc_v
        tobias_costream_sum += tb_v
        camp_sum += camp_v

    count = len(history)
    start_ts = history[0].get("timestamp", "").split(" ")[-1]
    end_ts = history[-1].get("timestamp", "").split(" ")[-1]
    if ":" in start_ts and len(start_ts) > 5:
        start_ts = start_ts[:5]
    if ":" in end_ts and len(end_ts) > 5:
        end_ts = end_ts[:5]

    return {
        "count": count,
        "goe_peak": goe_peak,
        "nerva_peak": nerva_peak,
        "goe_peak_time": goe_peak_time,
        "nerva_peak_time": nerva_peak_time,
        "goe_avg": round(goe_sum / count) if count > 0 else 0,
        "nerva_avg": round(nerva_sum / count) if count > 0 else 0,
        "start_time": start_ts,
        "end_time": end_ts,
        "goe_raw_peak": goe_raw_peak,
        "goe_raw_peak_time": goe_raw_peak_time,
        "is_bot_filtered": filter_bots,
        "nerva_costream_peak": nerva_costream_peak,
        "nerva_costream_peak_time": nerva_costream_peak_time,
        "nerva_costream_avg": round(nerva_costream_sum / count) if count > 0 else 0,
        "tobias_costream_peak": tobias_costream_peak,
        "tobias_costream_peak_time": tobias_costream_peak_time,
        "tobias_costream_avg": round(tobias_costream_sum / count) if count > 0 else 0,
        "tobias_peak": tobias_costream_peak,
        "tobias_peak_time": tobias_costream_peak_time,
        "tobias_avg": round(tobias_costream_sum / count) if count > 0 else 0,
        "nerva_camp_peak": camp_peak,
        "nerva_camp_peak_time": camp_peak_time,
        "nerva_camp_avg": round(camp_sum / count) if count > 0 else 0,
        "camp_peak": camp_peak,
        "camp_peak_time": camp_peak_time,
        "camp_avg": round(camp_sum / count) if count > 0 else 0,
    }


def get_momentum(minutes: int = 5) -> dict:
    """Calculates the change in viewers over the last N minutes."""
    init_db()
    now_unix = time.time()
    cutoff_unix = now_unix - (minutes * 60)

    with get_connection() as conn:
        latest = conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        past = conn.execute(
            "SELECT * FROM snapshots WHERE unix_time <= ? ORDER BY unix_time DESC LIMIT 1",
            (cutoff_unix,),
        ).fetchone()

        if not latest or not past:
            return {"goe_delta": 0, "nerva_delta": 0, "minutes": minutes}

        return {
            "goe_delta": latest["goe_total"] - past["goe_total"],
            "nerva_delta": latest["nerva_total"] - past["nerva_total"],
            "minutes": minutes,
        }


def export_to_csv(filepath: str | None = None) -> str:
    """Exports entire recorded history to a CSV string or file."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT 
                s.timestamp, s.total_viewers, s.goe_total, s.nerva_total, s.diff, s.leader,
                r.group_id, r.platform, r.channel_name, r.viewers, r.is_live, r.title
            FROM snapshots s
            JOIN stream_records r ON s.id = r.snapshot_id
            ORDER BY s.id ASC, r.id ASC
        """
        ).fetchall()

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            [
                "timestamp",
                "total_viewers",
                "goe_total",
                "nerva_total",
                "diff",
                "leader",
                "group",
                "platform",
                "channel_name",
                "viewers",
                "is_live",
                "title",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["timestamp"],
                    r["total_viewers"],
                    r["goe_total"],
                    r["nerva_total"],
                    r["diff"],
                    r["leader"],
                    r["group_id"],
                    r["platform"],
                    r["channel_name"],
                    r["viewers"],
                    r["is_live"],
                    r["title"],
                ]
            )

        csv_content = out.getvalue()
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(csv_content)
            return filepath
        return csv_content
