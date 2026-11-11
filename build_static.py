"""Builds static JSON data and graphics for GitHub Pages with multi-day support."""

import json
import os
import shutil
import sys
from datetime import datetime

# Ensure this directory is in path
sys.path.insert(0, os.path.dirname(__file__))

from config import DAYS_CONFIG, get_active_day_id
from generate_card import create_battle_card, create_og_card
from generate_summary import create_summary_card
from scraper import fetch_all_data

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "history.db")


def calculate_momentum(history: list[dict], minutes: int = 5) -> dict:
    """Calculates viewer delta over the last N minutes from history points."""
    if not history or len(history) < 2:
        return {"goe_delta": 0, "nerva_delta": 0, "minutes": minutes}

    latest = history[-1]
    curr_goe = latest.get("goe_total", 0)
    curr_nerva = latest.get("nerva_total", 0)

    try:
        t_latest = datetime.strptime(latest["timestamp"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        t_latest = datetime.now()

    best_pt = None
    target_seconds = minutes * 60

    for pt in reversed(history[:-1]):
        try:
            pt_time = datetime.strptime(pt["timestamp"], "%Y-%m-%d %H:%M:%S")
            diff = (t_latest - pt_time).total_seconds()
            if diff >= target_seconds:
                best_pt = pt
                break
            best_pt = pt
        except Exception:
            continue

    if not best_pt:
        best_pt = history[0]

    old_goe = best_pt.get("goe_total", 0)
    old_nerva = best_pt.get("nerva_total", 0)

    return {
        "goe_delta": curr_goe - old_goe,
        "nerva_delta": curr_nerva - old_nerva,
        "minutes": minutes,
    }


def export_csv_from_history(history: list[dict], filepath: str):
    """Exports history array to CSV with bot attack details and flexible stream mapping."""
    import csv

    fieldnames = [
        "timestamp",
        "goe_total",
        "goe_total_raw",
        "is_bot_attack",
        "nerva_total",
        "goe_stream_viewers",
        "goe_yt_viewers",
        "goe_yt_raw_viewers",
        "nerva_twitch_viewers",
        "nerva_yt_viewers",
        "nerva_costream",
        "tobias_costream",
        "nerva_costream_ciekawostka",
    ]

    from config import get_known_stream_ids
    from db import (
        extract_goe_yt_viewers,
        extract_nerva_costream_viewers,
        extract_nerva_yt_viewers,
    )

    known_ids = get_known_stream_ids()

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pt in history:
            streams = pt.get("streams", {})

            # 1. GoE Twitch
            goe_tw_v = streams.get("goe_stream", {}).get("viewers", 0)

            # 2. GoE YouTube (sum across any restarted/active YT streams)
            goe_yt_v, goe_yt_raw_v = extract_goe_yt_viewers(
                streams, filter_bots=True, known_ids=known_ids
            )

            # 3. Nervarien Twitch
            nerva_tw_v = streams.get("nervarien", {}).get("viewers", 0)

            # 4. Nervarien Official YouTube
            nerva_yt_v = extract_nerva_yt_viewers(streams, known_ids=known_ids)

            # 5. Co-streams (Nerva & Tobiasz)
            nerva_costream_v = extract_nerva_costream_viewers(
                streams, known_ids=known_ids
            )
            tobias_costream_v = streams.get("ttobias_lol", {}).get("viewers", 0)

            writer.writerow(
                {
                    "timestamp": pt.get("timestamp", ""),
                    "goe_total": pt.get("goe_total", 0),
                    "goe_total_raw": pt.get("goe_total_raw", pt.get("goe_total", 0)),
                    "is_bot_attack": 1 if pt.get("is_bot_attack") else 0,
                    "nerva_total": pt.get("nerva_total", 0),
                    "goe_stream_viewers": goe_tw_v,
                    "goe_yt_viewers": goe_yt_v,
                    "goe_yt_raw_viewers": goe_yt_raw_v,
                    "nerva_twitch_viewers": nerva_tw_v,
                    "nerva_yt_viewers": nerva_yt_v,
                    "nerva_costream": nerva_costream_v,
                    "tobias_costream": tobias_costream_v,
                    "nerva_costream_ciekawostka": nerva_costream_v,
                }
            )


def _heal_transient_fetch_errors(data: dict, history: list[dict]) -> None:
    """Prevents zero-viewer dips if a stream encountered a transient HTTP error
    while the latest history snapshot (< 360s old) still had that stream live."""
    if not history:
        return
    last_pt = history[-1]
    try:
        t_last = datetime.strptime(
            last_pt["timestamp"].split(".")[0], "%Y-%m-%d %H:%M:%S"
        )
        t_curr = datetime.strptime(data["timestamp"].split(".")[0], "%Y-%m-%d %H:%M:%S")
        if (t_curr - t_last).total_seconds() > 360:
            return
    except Exception:
        return

    prev_streams = last_pt.get("streams", {})
    changed = False
    for grp in data.get("groups", {}).values():
        grp_sum = 0
        for s in grp.get("streams", []):
            sid = s.get("id")
            if s.get("fetch_error") and sid in prev_streams:
                prev_s = prev_streams[sid]
                if prev_s.get("is_live") and prev_s.get("viewers", 0) > 0:
                    s["is_live"] = True
                    s["viewers"] = prev_s["viewers"]
                    s["title"] = prev_s.get("title", s.get("title", ""))
                    s["fetch_error"] = False
                    changed = True
            if s.get("is_live") and (
                grp["id"] == "TOBIASZ"
                or (not s.get("is_costream") and not s.get("is_curiosity"))
            ):
                grp_sum += s.get("viewers", 0)
        grp["total_viewers"] = grp_sum

    if changed:
        goe_v = data.get("groups", {}).get("GOE", {}).get("total_viewers", 0)
        nerva_v = data.get("groups", {}).get("NERVA", {}).get("total_viewers", 0)
        tot = sum(g.get("total_viewers", 0) for g in data.get("groups", {}).values())
        data["total_viewers"] = tot
        data["diff"] = abs(goe_v - nerva_v)
        data["leader"] = (
            "GOE" if goe_v > nerva_v else ("NERVA" if nerva_v > goe_v else "REMIS")
        )
        data["ratio_goe"] = round((goe_v / tot * 100), 1) if tot > 0 else 50.0
        data["ratio_nerva"] = round((nerva_v / tot * 100), 1) if tot > 0 else 50.0


def build_day(
    day_id: str,
    active_day: str,
    days_manifest: list[dict],
    force: bool = False,
    preloaded_data: dict | None = None,
) -> dict:
    """Builds static artifacts for a specific day."""
    print(f"\n==================== [Build: {day_id.upper()}] ====================")
    day_cfg = DAYS_CONFIG[day_id]
    is_active = day_id == active_day

    from db import (
        filter_bot_attacks,
        get_detailed_history,
        get_summary_stats,
        save_snapshot,
    )

    day_hist_path = os.path.join(BASE_DIR, f"history_{day_id}.json")
    day_data_path = os.path.join(BASE_DIR, f"data_{day_id}.json")
    day_csv_path = os.path.join(BASE_DIR, f"stream_data_{day_id}.csv")
    day_card_path = os.path.join(BASE_DIR, f"battle_card_{day_id}.png")
    day_goe_clean_path = os.path.join(BASE_DIR, f"goe_summary_{day_id}.png")
    day_goe_raw_path = os.path.join(BASE_DIR, f"goe_summary_raw_{day_id}.png")
    day_comp_clean_path = os.path.join(BASE_DIR, f"stream_summary_{day_id}.png")
    day_comp_raw_path = os.path.join(BASE_DIR, f"stream_summary_raw_{day_id}.png")
    day_camps_clean_path = os.path.join(BASE_DIR, f"camps_summary_{day_id}.png")
    day_camps_raw_path = os.path.join(BASE_DIR, f"camps_summary_raw_{day_id}.png")

    # 1. Fetch current status of streams for this day (only scrape live for active day)
    if preloaded_data is not None and is_active and not day_cfg.get("is_finished"):
        data = preloaded_data
    elif is_active and not day_cfg.get("is_finished"):
        data = fetch_all_data(groups_config=day_cfg["groups"], day_id=day_id)
    elif day_cfg.get("is_finished") and os.path.exists(day_data_path):
        try:
            with open(day_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = fetch_all_data(groups_config=day_cfg["groups"], day_id=day_id)
    else:
        # Upcoming or clean day - initialize clean offline placeholder
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "timestamp": now_str,
            "total_viewers": 0,
            "leader": "REMIS",
            "diff": 0,
            "ratio_goe": 50.0,
            "ratio_nerva": 50.0,
            "groups": {},
        }
        for grp_id, grp in day_cfg["groups"].items():
            streams_list = []
            for tw in grp.get("twitch", []):
                streams_list.append(
                    {
                        "id": tw,
                        "platform": "Twitch",
                        "channel": tw,
                        "title": "Stream offline",
                        "category": "",
                        "is_live": False,
                        "viewers": 0,
                        "url": f"https://www.twitch.tv/{tw}",
                        "avatar_url": "",
                        "group": grp_id,
                    }
                )
            for yt in grp.get("youtube", []):
                streams_list.append(
                    {
                        "id": yt,
                        "platform": "YouTube",
                        "channel": grp["name"],
                        "title": "Stream offline",
                        "category": "YouTube Live",
                        "is_live": False,
                        "viewers": 0,
                        "url": (
                            f"https://www.youtube.com/{yt}"
                            if yt.startswith("@")
                            else f"https://www.youtube.com/watch?v={yt}"
                        ),
                        "avatar_url": "",
                        "group": grp_id,
                    }
                )
            data["groups"][grp_id] = {
                "id": grp_id,
                "name": grp["name"],
                "color": grp["color"],
                "total_viewers": 0,
                "streams": streams_list,
            }

    # 2. Load History for this day (before live append so we can heal transient fetch errors)
    history = []
    if os.path.exists(day_hist_path):
        try:
            with open(day_hist_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    if os.path.exists(DB_PATH):
        db_hist = get_detailed_history(limit=5000, day_id=day_id)
        if not day_cfg.get("is_finished") and db_hist:
            # Merge JSON + DB histories chronologically by timestamp so cloud backup & local points fuse
            merged_by_ts = {}
            for pt in history:
                if pt.get("timestamp"):
                    merged_by_ts[pt["timestamp"]] = pt
            for pt in db_hist:
                if pt.get("timestamp"):
                    merged_by_ts[pt["timestamp"]] = pt
            history = [merged_by_ts[k] for k in sorted(merged_by_ts.keys())]
        elif len(db_hist) > len(history):
            history = db_hist

    if day_cfg.get("is_finished"):
        any_live = False
        data["total_viewers"] = 0
        data["is_live"] = False
        data["is_finished"] = True
        for grp in data.get("groups", {}).values():
            grp["total_viewers"] = 0
            for s in grp.get("streams", []):
                s["is_live"] = False
                s["viewers"] = 0
    else:
        if is_active:
            _heal_transient_fetch_errors(data, history)
        any_live = any(
            s.get("is_live", False)
            for grp in data["groups"].values()
            for s in grp.get("streams", [])
            if not s.get("is_costream") and not s.get("is_curiosity")
        )

        if is_active and any_live:
            if preloaded_data is None:
                save_snapshot(data, day_id=day_id)

            all_s_map = {}
            for grp in data["groups"].values():
                for s in grp.get("streams", []):
                    all_s_map[s["id"]] = s

            new_point = {
                "timestamp": data["timestamp"],
                "goe_total": data["groups"]["GOE"]["total_viewers"],
                "goe_total_raw": data["groups"]["GOE"]["total_viewers"],
                "is_bot_attack": False,
                "nerva_total": data["groups"]["NERVA"]["total_viewers"],
                "streams": {
                    sid: {
                        "id": sid,
                        "channel": s.get("channel", sid),
                        "viewers": s.get("viewers", 0),
                        "platform": s.get("platform", "YouTube"),
                        "group": s.get("group", ""),
                        "is_live": s.get("is_live", False),
                        "is_costream": s.get("is_costream", False),
                        "is_curiosity": s.get("is_curiosity", False),
                    }
                    for sid, s in all_s_map.items()
                },
            }
            if not history or history[-1].get("timestamp") < new_point["timestamp"]:
                history.append(new_point)

    # 3. Clean history
    history = filter_bot_attacks(history, enabled=True)
    if len(history) > 5000:
        history = history[-5000:]

    # 4. Momentum & stats
    momentum = calculate_momentum(history, minutes=5)
    data["day_id"] = day_id
    data["day_name"] = day_cfg["name"]
    data["day_date"] = day_cfg["date"]
    data["match"] = day_cfg.get("match", "")
    data["match_short"] = day_cfg.get("match_short", "")
    data["score"] = day_cfg.get("score", "")
    data["winner"] = day_cfg.get("winner", "")
    data["stage"] = day_cfg.get("stage", "quarters")
    data["disclaimers"] = day_cfg.get("disclaimers", [])
    data["schedule"] = day_cfg.get("schedule", {})
    data["goe_start_time"] = day_cfg.get("schedule", {}).get("goe_start_iso", "")
    data["events"] = day_cfg.get("events", [])
    data["is_finished"] = day_cfg.get("is_finished", False)
    data["is_active"] = is_active and not data["is_finished"]
    data["momentum"] = momentum
    data["is_live"] = any_live and not data["is_finished"]
    data["summary_stats"] = get_summary_stats(custom_history=history, filter_bots=True)
    data["summary_stats_raw"] = get_summary_stats(
        custom_history=history, filter_bots=False
    )
    data["active_day_id"] = active_day
    data["days"] = days_manifest

    # 5. Save static JSONs & CSV
    with open(day_data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Zapisano: {day_data_path}")

    with open(day_hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)
    print(f"✅ Zapisano: {day_hist_path} ({len(history)} punktów)")

    export_csv_from_history(history, day_csv_path)
    print(f"✅ Zapisano: {day_csv_path}")

    # 6. Generate graphics (skip re-rendering for finished days if images already exist)
    all_graphics_exist = (
        os.path.exists(day_card_path)
        and os.path.exists(day_goe_clean_path)
        and os.path.exists(day_comp_clean_path)
        and os.path.exists(day_camps_clean_path)
    )

    if force or not (day_cfg.get("is_finished") and all_graphics_exist):
        try:
            create_battle_card(data, day_card_path)
            print(f"📸 Karta LIVE ({day_id}): {day_card_path}")
        except Exception as e:
            print(f"⚠️ Błąd karty LIVE ({day_id}): {e}")

        try:
            create_summary_card(
                day_goe_clean_path,
                mode="GOE",
                custom_history=history,
                filter_bots=True,
            )
            print(f"📊 Wykres GoE ({day_id}): {day_goe_clean_path}")
            create_summary_card(
                day_goe_raw_path,
                mode="GOE",
                custom_history=history,
                filter_bots=False,
            )
            print(f"📊 Wykres GoE surowy ({day_id}): {day_goe_raw_path}")
        except Exception as e:
            print(f"⚠️ Błąd wykresu GoE ({day_id}): {e}")

        try:
            create_summary_card(
                day_comp_clean_path,
                mode="COMPARISON",
                custom_history=history,
                filter_bots=True,
            )
            print(f"⚖️ Wykres Porównania ({day_id}): {day_comp_clean_path}")
            create_summary_card(
                day_comp_raw_path,
                mode="COMPARISON",
                custom_history=history,
                filter_bots=False,
            )
            print(f"⚖️ Wykres Porównania surowy ({day_id}): {day_comp_raw_path}")
        except Exception as e:
            print(f"⚠️ Błąd wykresu porównania ({day_id}): {e}")

        try:
            create_summary_card(
                day_camps_clean_path,
                mode="CAMPS",
                custom_history=history,
                filter_bots=True,
            )
            print(f"🏕️ Wykres 3 Obozów ({day_id}): {day_camps_clean_path}")
            create_summary_card(
                day_camps_raw_path,
                mode="CAMPS",
                custom_history=history,
                filter_bots=False,
            )
            print(f"🏕️ Wykres 3 Obozów surowy ({day_id}): {day_camps_raw_path}")
        except Exception as e:
            print(f"⚠️ Błąd wykresu 3 obozów ({day_id}): {e}")

    return {
        "data_path": day_data_path,
        "hist_path": day_hist_path,
        "csv_path": day_csv_path,
        "card_path": day_card_path,
        "goe_clean_path": day_goe_clean_path,
        "goe_raw_path": day_goe_raw_path,
        "comp_clean_path": day_comp_clean_path,
        "comp_raw_path": day_comp_raw_path,
        "camps_clean_path": day_camps_clean_path,
        "camps_raw_path": day_camps_raw_path,
    }


def build(
    force: bool = False,
    preloaded_data: dict | None = None,
    preloaded_day_id: str | None = None,
):
    import sys

    force = force or ("--force" in sys.argv)
    active_day = get_active_day_id()
    print(f"🌟 [Multi-Day Build] Aktywny dzień (wg reguły 12:00 UTC): {active_day}")

    days_manifest = [
        {
            "id": d_id,
            "name": cfg["name"],
            "label": cfg["label"],
            "date": cfg["date"],
            "match": cfg.get("match", ""),
            "match_short": cfg.get("match_short", ""),
            "score": cfg.get("score", ""),
            "winner": cfg.get("winner", ""),
            "stage": cfg.get("stage", "quarters"),
            "disclaimers": cfg.get("disclaimers", []),
            "schedule": cfg.get("schedule", {}),
            "is_finished": cfg.get("is_finished", False),
            "is_active": (d_id == active_day),
            "data_url": f"./data_{d_id}.json",
            "history_url": f"./history_{d_id}.json",
            "csv_url": f"./stream_data_{d_id}.csv",
            "summary_card": f"./stream_summary_{d_id}.png",
            "goe_card": f"./goe_summary_{d_id}.png",
            "camps_card": f"./camps_summary_{d_id}.png",
        }
        for d_id, cfg in DAYS_CONFIG.items()
    ]

    day_outputs = {}
    for day_id in DAYS_CONFIG:
        # Force re-rendering only for active day unless global force
        day_force = force or (day_id == active_day)
        day_preloaded = (
            preloaded_data
            if (
                preloaded_data is not None
                and day_id == (preloaded_day_id or active_day)
            )
            else None
        )
        day_outputs[day_id] = build_day(
            day_id,
            active_day,
            days_manifest,
            force=day_force,
            preloaded_data=day_preloaded,
        )

    # Mirror active day artifacts to standard root names for backward compatibility & GitHub Pages root
    print(
        f"\n🔄 [Mirroring] Kopiowanie aktywnego dnia ({active_day}) do plików głównych..."
    )
    act_out = day_outputs[active_day]

    shutil.copyfile(act_out["data_path"], os.path.join(BASE_DIR, "data.json"))
    shutil.copyfile(act_out["hist_path"], os.path.join(BASE_DIR, "history.json"))
    shutil.copyfile(act_out["csv_path"], os.path.join(BASE_DIR, "stream_data.csv"))
    shutil.copyfile(act_out["card_path"], os.path.join(BASE_DIR, "battle_card.png"))
    shutil.copyfile(
        act_out["goe_clean_path"], os.path.join(BASE_DIR, "goe_summary.png")
    )
    shutil.copyfile(
        act_out["goe_raw_path"], os.path.join(BASE_DIR, "goe_summary_raw.png")
    )
    shutil.copyfile(
        act_out["comp_clean_path"], os.path.join(BASE_DIR, "stream_summary.png")
    )
    shutil.copyfile(
        act_out["comp_raw_path"], os.path.join(BASE_DIR, "stream_summary_raw.png")
    )
    shutil.copyfile(
        act_out["camps_clean_path"], os.path.join(BASE_DIR, "camps_summary.png")
    )
    shutil.copyfile(
        act_out["camps_raw_path"], os.path.join(BASE_DIR, "camps_summary_raw.png")
    )

    # Generate 1200x630 OpenGraph card for social media share previews
    og_path = os.path.join(BASE_DIR, "og_preview.png")
    try:
        with open(act_out["data_path"], "r", encoding="utf-8") as f:
            active_data = json.load(f)
        create_og_card(active_data, og_path)
        print(f"🖼️ [OpenGraph] Wygenerowano kartę podglądu: {og_path}")
    except Exception as e:
        print(f"⚠️ Błąd generowania og_preview.png: {e}")

    # Generate multi-stage & tournament analytics and cards
    try:
        from analytics import generate_tournament_analytics
        from generate_summary import create_stage_summary_card

        generate_tournament_analytics()
        q_path = os.path.join(BASE_DIR, "quarters_summary.png")
        s_path = os.path.join(BASE_DIR, "semis_summary.png")
        t_path = os.path.join(BASE_DIR, "tournament_summary.png")

        create_stage_summary_card("quarters", q_path)
        create_stage_summary_card("semis", s_path)
        create_stage_summary_card("tournament", t_path)
        print("📊 [Stage Cards] Wygenerowano karty etapów: quarters, semis, tournament")
    except Exception as e:
        print(f"⚠️ Błąd generowania analityki etapowej: {e}")

    print(
        "🎉 [Build] Zakończono! Wszystkie pliki dniowe oraz główne zostały przygotowane."
    )


if __name__ == "__main__":
    build()
