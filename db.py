"""SQLite persistence, platform filtering, momentum calculation, CSV export, and granular stream history."""

import csv
from datetime import datetime
import io
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")


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

        conn.commit()


def save_snapshot(data: dict) -> int:
    """Saves a fresh scrape snapshot into SQLite."""
    init_db()
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
                diff, leader, ratio_goe, ratio_nerva
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        snapshot_id = cur.lastrowid

        for grp_key in ["GOE", "NERVA"]:
            grp = data["groups"].get(grp_key, {})
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


def get_detailed_history(limit: int = 2000) -> list[dict]:
    """Retrieves chronological snapshots with granular per-stream viewer data."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.timestamp, s.unix_time, s.total_viewers, s.goe_total, s.nerva_total,
                   r.channel_id, r.channel_name, r.platform, r.group_id, r.viewers, r.is_live
            FROM (SELECT * FROM snapshots ORDER BY id DESC LIMIT ?) s
            JOIN stream_records r ON s.id = r.snapshot_id
            ORDER BY s.id ASC
        """,
            (limit,),
        ).fetchall()

        snapshots_map = {}
        for r in rows:
            sid = r["id"]
            if sid not in snapshots_map:
                snapshots_map[sid] = {
                    "id": sid,
                    "timestamp": r["timestamp"],
                    "unix_time": r["unix_time"],
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
                "GOE"
                if goe_total > nerva_total
                else ("NERVA" if nerva_total > goe_total else "REMIS")
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


def get_summary_stats(platform: str = "ALL") -> dict:
    """Calculates peak, average, and summary statistics across recorded history per platform."""
    history = get_history(limit=2000, platform=platform)
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
        }

    goe_peak = 0
    nerva_peak = 0
    goe_peak_time = ""
    nerva_peak_time = ""
    goe_sum = 0
    nerva_sum = 0

    for pt in history:
        gv = pt["goe_total"]
        nv = pt["nerva_total"]
        if gv > goe_peak:
            goe_peak = gv
            goe_peak_time = pt["timestamp"].split(" ")[-1]
        if nv > nerva_peak:
            nerva_peak = nv
            nerva_peak_time = pt["timestamp"].split(" ")[-1]
        goe_sum += gv
        nerva_sum += nv

    count = len(history)
    return {
        "count": count,
        "goe_peak": goe_peak,
        "nerva_peak": nerva_peak,
        "goe_peak_time": goe_peak_time,
        "nerva_peak_time": nerva_peak_time,
        "goe_avg": int(round(goe_sum / count)) if count > 0 else 0,
        "nerva_avg": int(round(nerva_sum / count)) if count > 0 else 0,
        "start_time": history[0]["timestamp"],
        "end_time": history[-1]["timestamp"],
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


def export_to_csv(filepath: str = None) -> str:
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
