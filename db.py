"""SQLite persistence, platform filtering, momentum calculation, CSV export, and granular stream history."""

import csv
import io
import os
import sqlite3
import time
from datetime import datetime

from config import COSTREAM_STREAMS, get_active_day_id, get_known_stream_ids

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


def _is_goe_yt_stream(sid: str, s: dict, known_ids: dict[str, set[str]]) -> bool:
    """Checks whether a stream entry belongs to GoE YouTube."""
    if sid == "goe_stream":
        return False
    if s.get("group") == "GOE" and s.get("platform") == "YouTube":
        return True
    return sid in known_ids["goe_yt"]


def _is_nerva_yt_official(sid: str, s: dict, known_ids: dict[str, set[str]]) -> bool:
    """Checks whether a stream entry belongs to Nervarien's official YouTube broadcast."""
    if sid in COSTREAM_STREAMS or sid in known_ids["nerva_costream"]:
        return False
    if s.get("is_costream") or s.get("is_curiosity"):
        return False
    if s.get("group") == "NERVA" and s.get("platform") == "YouTube":
        return True
    return sid in known_ids["nerva_yt"]


def extract_goe_yt_viewers(
    streams: dict,
    filter_bots: bool = True,
    known_ids: dict[str, set[str]] | None = None,
) -> tuple[int, int]:
    """Returns (effective_viewers, raw_viewers) summed across all GoE YouTube streams."""
    if known_ids is None:
        known_ids = get_known_stream_ids()
    eff = 0
    raw = 0
    for sid, s in streams.items():
        if _is_goe_yt_stream(sid, s, known_ids):
            v_raw = s.get("viewers_raw", s.get("viewers", 0))
            v_eff = s.get("viewers", 0) if filter_bots else v_raw
            eff += v_eff
            raw += v_raw
    return eff, raw


def extract_nerva_yt_viewers(
    streams: dict, known_ids: dict[str, set[str]] | None = None
) -> int:
    """Returns viewers summed across Nervarien's official YouTube streams."""
    if known_ids is None:
        known_ids = get_known_stream_ids()
    return sum(
        s.get("viewers", 0)
        for sid, s in streams.items()
        if _is_nerva_yt_official(sid, s, known_ids)
    )


def extract_nerva_costream_viewers(
    streams: dict, known_ids: dict[str, set[str]] | None = None
) -> int:
    """Returns max viewers across Nervarien's secondary co-stream channels."""
    if known_ids is None:
        known_ids = get_known_stream_ids()
    candidates = [
        s.get("viewers", 0)
        for sid, s in streams.items()
        if sid != "ttobias_lol"
        and (
            s.get("is_costream")
            or s.get("is_curiosity")
            or sid in known_ids["nerva_costream"]
        )
    ]
    return max(candidates, default=0)


def compute_trapezoidal_window_stats(
    history: list[dict], value_fn, max_live_gap: float = 3600.0
) -> dict:
    """Computes physically accurate live duration, live average, peak, and watch-hours
    by integrating over true timestamp intervals (Δt) with the trapezoidal rule.

    Eliminates inflation caused by duplicate/irregular sampling cadences (e.g., 15s vs 5min).
    """
    parsed = []
    for p in history:
        ts_str = p.get("timestamp", "")
        if not ts_str:
            continue
        try:
            dt = datetime.strptime(ts_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        val = max(0, int(value_fn(p) or 0))
        parsed.append((dt, ts_str, val))

    active_pts = [(dt, ts_str, val) for (dt, ts_str, val) in parsed if val > 0]
    if not active_pts:
        return {
            "is_live_any": False,
            "start_time": "--",
            "end_time": "--",
            "points_count": 0,
            "duration_hours": 0.0,
            "duration_str": "0h 00m",
            "peak": 0,
            "peak_time": "--",
            "live_avg": 0,
            "watch_hours": 0,
        }

    first_ts = active_pts[0][1]
    last_ts = active_pts[-1][1]
    peak_val = 0
    peak_time = "--"
    for _, ts_str, v in active_pts:
        if v > peak_val:
            peak_val = v
            peak_time = ts_str[11:16] if len(ts_str) >= 16 else ts_str

    total_sec = 0.0
    total_view_sec = 0.0

    for i in range(len(parsed) - 1):
        t1, _, v1 = parsed[i]
        t2, _, v2 = parsed[i + 1]
        dt = (t2 - t1).total_seconds()
        if dt <= 0:
            continue
        if v1 > 0 and v2 > 0:
            eff_dt = min(dt, max_live_gap)
            total_sec += eff_dt
            total_view_sec += ((v1 + v2) / 2.0) * eff_dt
        elif v1 > 0 and v2 == 0:
            eff_dt = min(dt, 30.0)
            total_sec += eff_dt
            total_view_sec += v1 * eff_dt
        elif v1 == 0 and v2 > 0:
            eff_dt = min(dt, 30.0)
            total_sec += eff_dt
            total_view_sec += v2 * eff_dt

    # Edge case: only 1 isolated live point with zero adjacent duration
    if total_sec <= 0 and active_pts:
        total_sec = 15.0
        total_view_sec = active_pts[0][2] * total_sec

    duration_hours = total_sec / 3600.0
    watch_hours = total_view_sec / 3600.0
    live_avg = round(total_view_sec / total_sec) if total_sec > 0 else 0

    dur_mins = round(duration_hours * 60)
    dur_h = dur_mins // 60
    dur_m = dur_mins % 60
    dur_str = f"{dur_h}h {dur_m:02d}m"

    return {
        "is_live_any": True,
        "start_time": first_ts[11:16] if len(first_ts) >= 16 else first_ts,
        "end_time": last_ts[11:16] if len(last_ts) >= 16 else last_ts,
        "points_count": len(active_pts),
        "duration_hours": round(duration_hours, 2),
        "duration_str": dur_str,
        "peak": peak_val,
        "peak_time": peak_time,
        "live_avg": live_avg,
        "watch_hours": round(watch_hours),
    }


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

        # Ignore outage recoveries: if recent history had an outage (< 600) or curr is within 30-min peak
        broader_pts = yt_raw_series[max(0, i - 40) : i]
        broader_max = max(broader_pts) if broader_pts else curr
        had_recent_outage = any(v < 600 for v in prev_pts)

        if not in_spike:
            # A real bot attack is a massive artificial surge (>1500) above previous 30-min peak, curr > 3600
            if (
                not had_recent_outage
                and prev_median > 800
                and (curr - prev_median) > 1500
                and curr > broader_max + 1000
                and curr > 3600
            ):
                in_spike = True
                spike_start = i
                base_start = prev_median
        else:
            if curr <= base_start + 400 or (i - spike_start > 50):
                # If it didn't drop within 50 steps (~12 mins), it's legitimate audience growth, not a spike
                if curr <= base_start + 400:
                    spike_windows.append(
                        (spike_start, i, base_start, curr, i - spike_start + 1)
                    )
                in_spike = False

    if in_spike and (len(points) - 1 - spike_start <= 40):
        # Only flatten an unfinished trailing surge if it jumped as an extreme vertical bot wall
        step_jump = (
            yt_raw_series[spike_start] - yt_raw_series[spike_start - 1]
            if spike_start > 0
            else 0
        )
        end_val = yt_raw_series[-1]
        if step_jump > 2000 and end_val >= base_start * 2.0:
            spike_windows.append(
                (
                    spike_start,
                    len(points) - 1,
                    base_start,
                    base_start,
                    len(points) - spike_start + 1,
                )
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
                        s["viewers_raw"] = s.get(
                            "viewers_raw", s.get("viewers", clean_yt)
                        )
                        s["viewers"] = clean_yt
                        s["is_bot_attack"] = True

                tw_v = p.get("streams", {}).get("goe_stream", {}).get("viewers", 0)
                p["goe_total"] = tw_v + clean_yt
                nerva_v = p.get("nerva_total", 0)
                p["total_viewers"] = p["goe_total"] + nerva_v
                p["diff"] = abs(p["goe_total"] - nerva_v)
                p["leader"] = (
                    "GOE"
                    if p["goe_total"] > nerva_v
                    else ("NERVA" if nerva_v > p["goe_total"] else "REMIS")
                )
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

    known_ids = get_known_stream_ids()
    cleaned = []
    for pt in points:
        ts_str = pt.get("timestamp", "")
        # Drop corrupted Day 1 post-stream VOD records strictly between 03:05 and 12:00 UTC on Nov 4
        if "2026-11-04 03:05:00" <= ts_str < "2026-11-04 12:00:00" and (
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
        nerva_yt = extract_nerva_yt_viewers(streams, known_ids=known_ids)
        nerva_tot = nerva_tw + nerva_yt
        p["nerva_total"] = nerva_tot

        # Locate GoE YouTube stream dynamically
        yt_stream = None
        yt_stream_id = None
        for sid, s in streams.items():
            if _is_goe_yt_stream(sid, s, known_ids):
                yt_stream = s
                yt_stream_id = sid
                break

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
                    "day_id": r["day_id"] if "day_id" in r.keys() else "day-1",
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
        history = get_detailed_history(limit=5000, day_id=get_active_day_id())

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
            "tobias_peak": 0,
            "tobias_peak_time": "",
            "tobias_avg": 0,
            "nerva_camp_peak": 0,
            "nerva_camp_peak_time": "",
            "nerva_camp_avg": 0,
            "camp_peak": 0,
            "camp_peak_time": "",
            "camp_avg": 0,
            "yt_peak": 0,
            "yt_peak_time": "",
            "tw_peak": 0,
            "tw_peak_time": "",
            "yt_avg": 0,
            "tw_avg": 0,
            "yt_watch_hours": 0,
            "tw_watch_hours": 0,
            "goe_live_avg": 0,
            "nerva_live_avg": 0,
            "tobias_live_avg": 0,
            "goe_watch_hours": 0,
            "nerva_watch_hours": 0,
            "tobias_watch_hours": 0,
        }

    known_ids = get_known_stream_ids()

    def _goe_val(pt: dict) -> int:
        clean = pt.get("goe_total", 0)
        return clean if filter_bots else pt.get("goe_total_raw", clean)

    def _goe_raw_val(pt: dict) -> int:
        return pt.get("goe_total_raw", pt.get("goe_total", 0))

    def _nerva_val(pt: dict) -> int:
        return pt.get("nerva_total", 0)

    def _yt_val(pt: dict) -> int:
        eff, raw = extract_goe_yt_viewers(
            pt.get("streams", {}), filter_bots=filter_bots, known_ids=known_ids
        )
        return eff

    def _tw_val(pt: dict) -> int:
        return pt.get("streams", {}).get("goe_stream", {}).get("viewers", 0)

    def _nc_val(pt: dict) -> int:
        return extract_nerva_costream_viewers(
            pt.get("streams", {}), known_ids=known_ids
        )

    def _tb_val(pt: dict) -> int:
        return pt.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)

    def _camp_val(pt: dict) -> int:
        return _nerva_val(pt) + _nc_val(pt)

    goe_win = compute_trapezoidal_window_stats(history, _goe_val)
    goe_raw_win = compute_trapezoidal_window_stats(history, _goe_raw_val)
    nerva_win = compute_trapezoidal_window_stats(history, _nerva_val)
    yt_win = compute_trapezoidal_window_stats(history, _yt_val)
    tw_win = compute_trapezoidal_window_stats(history, _tw_val)
    nc_win = compute_trapezoidal_window_stats(history, _nc_val)
    tb_win = compute_trapezoidal_window_stats(history, _tb_val)
    camp_win = compute_trapezoidal_window_stats(history, _camp_val)

    count = len(history)
    hist_start = history[0].get("timestamp", "").split(" ")[-1][:5]
    hist_end = history[-1].get("timestamp", "").split(" ")[-1][:5]
    start_ts = goe_win["start_time"] if goe_win["is_live_any"] else hist_start
    end_ts = goe_win["end_time"] if goe_win["is_live_any"] else hist_end

    return {
        "count": count,
        "goe_peak": goe_win["peak"],
        "nerva_peak": nerva_win["peak"],
        "goe_peak_time": goe_win["peak_time"],
        "nerva_peak_time": nerva_win["peak_time"],
        "goe_avg": goe_win["live_avg"],
        "nerva_avg": nerva_win["live_avg"],
        "start_time": start_ts,
        "end_time": end_ts,
        "goe_raw_peak": goe_raw_win["peak"],
        "goe_raw_peak_time": goe_raw_win["peak_time"],
        "is_bot_filtered": filter_bots,
        "nerva_costream_peak": nc_win["peak"],
        "nerva_costream_peak_time": nc_win["peak_time"],
        "nerva_costream_avg": nc_win["live_avg"],
        "tobias_costream_peak": tb_win["peak"],
        "tobias_costream_peak_time": tb_win["peak_time"],
        "tobias_costream_avg": tb_win["live_avg"],
        "tobias_peak": tb_win["peak"],
        "tobias_peak_time": tb_win["peak_time"],
        "tobias_avg": tb_win["live_avg"],
        "nerva_camp_peak": camp_win["peak"],
        "nerva_camp_peak_time": camp_win["peak_time"],
        "nerva_camp_avg": camp_win["live_avg"],
        "camp_peak": camp_win["peak"],
        "camp_peak_time": camp_win["peak_time"],
        "camp_avg": camp_win["live_avg"],
        "yt_peak": yt_win["peak"],
        "yt_peak_time": yt_win["peak_time"],
        "tw_peak": tw_win["peak"],
        "tw_peak_time": tw_win["peak_time"],
        "yt_avg": yt_win["live_avg"],
        "tw_avg": tw_win["live_avg"],
        "yt_watch_hours": yt_win["watch_hours"],
        "tw_watch_hours": tw_win["watch_hours"],
        "goe_live_avg": goe_win["live_avg"],
        "nerva_live_avg": nerva_win["live_avg"],
        "tobias_live_avg": tb_win["live_avg"],
        "goe_watch_hours": goe_win["watch_hours"],
        "nerva_watch_hours": nerva_win["watch_hours"],
        "tobias_watch_hours": tb_win["watch_hours"],
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
