"""Tournament & Multi-Stage Analytics Engine for Worlds 2026.

Calculates accurate per-streamer live broadcast windows, true live averages (free from
offline distortion), watch-hours (widzogodziny), and stage aggregates (Quarters, Semis, Overall).
"""

import json
import os
from datetime import datetime

from config import DAYS_CONFIG, STAGES_CONFIG, get_known_stream_ids
from db import compute_trapezoidal_window_stats, extract_goe_yt_viewers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def detect_streamer_window(history: list[dict], camp_key: str) -> dict:
    """Detects the exact active broadcasting window for a camp, eliminating offline penalties.

    Returns true live average, time-integrated watch-hours (Δt), peak, peak time,
    start, end, and duration.
    """
    known_ids = get_known_stream_ids()

    if camp_key == "GOE":
        get_v = lambda p: p.get("goe_total", 0)
    elif camp_key == "NERVA":
        get_v = lambda p: p.get("nerva_total", 0)
    elif camp_key == "TOBIASZ":
        get_v = lambda p: p.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
    elif camp_key == "GOE_YT":
        get_v = lambda p: extract_goe_yt_viewers(
            p.get("streams", {}), filter_bots=True, known_ids=known_ids
        )[0]
    elif camp_key == "GOE_TW":
        get_v = lambda p: p.get("streams", {}).get("goe_stream", {}).get("viewers", 0)
    else:
        get_v = lambda p: 0

    stats = compute_trapezoidal_window_stats(history, get_v)
    stats["camp"] = camp_key
    return stats


def compute_match_analytics(day_id: str) -> dict:
    """Computes comprehensive analytics for a single day/match."""
    cfg = DAYS_CONFIG.get(day_id, {})
    hist_path = os.path.join(BASE_DIR, f"history_{day_id}.json")

    history = []
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            history = json.load(f)

    goe_stats = detect_streamer_window(history, "GOE")
    goe_yt_stats = detect_streamer_window(history, "GOE_YT")
    goe_tw_stats = detect_streamer_window(history, "GOE_TW")
    nerva_stats = detect_streamer_window(history, "NERVA")
    tobias_stats = detect_streamer_window(history, "TOBIASZ")

    # Combined scene peak across all 3 camps
    total_peak = 0
    total_peak_time = "--"
    for p in history:
        gv = p.get("goe_total", 0)
        nv = p.get("nerva_total", 0)
        tv = p.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
        tot = gv + nv + tv
        if tot > total_peak:
            total_peak = tot
            total_peak_time = p.get("timestamp", "")[11:16]

    total_watch_hours = (
        goe_stats["watch_hours"]
        + nerva_stats["watch_hours"]
        + tobias_stats["watch_hours"]
    )
    goe_share = (
        round((goe_stats["watch_hours"] / total_watch_hours) * 100, 1)
        if total_watch_hours > 0
        else 0.0
    )
    nerva_share = (
        round((nerva_stats["watch_hours"] / total_watch_hours) * 100, 1)
        if total_watch_hours > 0
        else 0.0
    )
    tobias_share = (
        round((tobias_stats["watch_hours"] / total_watch_hours) * 100, 1)
        if total_watch_hours > 0
        else 0.0
    )

    return {
        "day_id": day_id,
        "name": cfg.get("name", day_id),
        "date": cfg.get("date", ""),
        "match": cfg.get("match", ""),
        "match_short": cfg.get("match_short", ""),
        "score": cfg.get("score", ""),
        "winner": cfg.get("winner", ""),
        "stage": cfg.get("stage", "quarters"),
        "is_finished": cfg.get("is_finished", False),
        "schedule": cfg.get("schedule", {}),
        "disclaimers": cfg.get("disclaimers", []),
        "points_count": len(history),
        "total_peak": total_peak,
        "total_peak_time": total_peak_time,
        "total_watch_hours": total_watch_hours,
        "goe": goe_stats,
        "goe_yt": goe_yt_stats,
        "goe_tw": goe_tw_stats,
        "nerva": nerva_stats,
        "tobias": tobias_stats,
        "market_share": {
            "goe": goe_share,
            "nerva": nerva_share,
            "tobias": tobias_share,
        },
    }


def compute_stage_summary(stage_id: str, matches: list[dict]) -> dict:
    """Aggregates a stage (Quarters, Semis, Finals, or All) across its constituent matches."""
    cfg = STAGES_CONFIG.get(stage_id, {})
    target_day_ids = cfg.get("days", [])
    stage_matches = [m for m in matches if m["day_id"] in target_day_ids]
    played_matches = [m for m in stage_matches if m.get("points_count", 0) > 0]

    total_pts = sum(m["points_count"] for m in stage_matches)

    # Watch-hours
    goe_vh = sum(m["goe"]["watch_hours"] for m in stage_matches)
    nerva_vh = sum(m["nerva"]["watch_hours"] for m in stage_matches)
    tobias_vh = sum(m["tobias"]["watch_hours"] for m in stage_matches)
    total_vh = goe_vh + nerva_vh + tobias_vh

    # Live durations
    goe_dur = sum(m["goe"]["duration_hours"] for m in stage_matches)
    nerva_dur = sum(m["nerva"]["duration_hours"] for m in stage_matches)
    tobias_dur = sum(m["tobias"]["duration_hours"] for m in stage_matches)

    # True live averages across the whole stage
    goe_avg = round(goe_vh / goe_dur) if goe_dur > 0 else 0
    nerva_avg = round(nerva_vh / nerva_dur) if nerva_dur > 0 else 0
    tobias_avg = round(tobias_vh / tobias_dur) if tobias_dur > 0 else 0

    # Peaks and peak sources
    goe_peak = max((m["goe"]["peak"] for m in stage_matches), default=0)
    nerva_peak = max((m["nerva"]["peak"] for m in stage_matches), default=0)
    tobias_peak = max((m["tobias"]["peak"] for m in stage_matches), default=0)
    total_camp_peak = max((m["total_peak"] for m in stage_matches), default=0)

    # Identify which match produced the record peaks
    best_match_goe = (
        next((m for m in stage_matches if m["goe"]["peak"] == goe_peak), None)
        if goe_peak > 0
        else None
    )
    best_match_nerva = (
        next((m for m in stage_matches if m["nerva"]["peak"] == nerva_peak), None)
        if nerva_peak > 0
        else None
    )
    best_match_scene = (
        next((m for m in stage_matches if m["total_peak"] == total_camp_peak), None)
        if total_camp_peak > 0
        else None
    )

    goe_share = round((goe_vh / total_vh) * 100, 1) if total_vh > 0 else 0.0
    nerva_share = round((nerva_vh / total_vh) * 100, 1) if total_vh > 0 else 0.0
    tobias_share = round((tobias_vh / total_vh) * 100, 1) if total_vh > 0 else 0.0

    return {
        "id": stage_id,
        "name": cfg.get("name", stage_id),
        "short_name": cfg.get("short_name", stage_id),
        "icon": cfg.get("icon", "📊"),
        "subtitle": cfg.get("subtitle", ""),
        "days": target_day_ids,
        "matches_count": len(played_matches),
        "scheduled_matches_count": len(stage_matches),
        "total_points": total_pts,
        "total_watch_hours": total_vh,
        "total_scene_peak": total_camp_peak,
        "total_scene_peak_match": (
            best_match_scene["match_short"] if best_match_scene else ""
        ),
        "goe": {
            "peak": goe_peak,
            "peak_match": (best_match_goe["match_short"] if best_match_goe else ""),
            "live_avg": goe_avg,
            "watch_hours": goe_vh,
            "duration_hours": round(goe_dur, 1),
            "share": goe_share,
        },
        "nerva": {
            "peak": nerva_peak,
            "peak_match": (best_match_nerva["match_short"] if best_match_nerva else ""),
            "live_avg": nerva_avg,
            "watch_hours": nerva_vh,
            "duration_hours": round(nerva_dur, 1),
            "share": nerva_share,
        },
        "tobias": {
            "peak": tobias_peak,
            "live_avg": tobias_avg,
            "watch_hours": tobias_vh,
            "duration_hours": round(tobias_dur, 1),
            "share": tobias_share,
        },
        "market_share": {
            "goe": goe_share,
            "nerva": nerva_share,
            "tobias": tobias_share,
        },
        "matches": stage_matches,
    }


def generate_tournament_analytics() -> dict:
    """Builds and saves the complete tournament & stage analytics JSON."""
    matches = [compute_match_analytics(did) for did in DAYS_CONFIG]

    stages = {sid: compute_stage_summary(sid, matches) for sid in STAGES_CONFIG}

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": "Worlds 2026 • Podsumowanie Oglądalności Polskiej Sceny",
        "stages": stages,
        "matches": matches,
    }

    out_path = os.path.join(BASE_DIR, "tournament_analytics.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(
        f"✅ Wygenerowano analitykę turniejową: {out_path} ({len(matches)} meczów, {len(stages)} etapy)"
    )
    return payload


if __name__ == "__main__":
    generate_tournament_analytics()
