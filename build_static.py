"""Builds static JSON data and graphics for GitHub Pages without requiring an active backend."""

from datetime import datetime
import json
import os
import sys

# Ensure this directory is in path
sys.path.insert(0, os.path.dirname(__file__))

from generate_card import create_battle_card
from generate_summary import create_summary_card
from scraper import fetch_all_data

DATA_JSON_PATH = os.path.join(os.path.dirname(__file__), "data.json")
HISTORY_JSON_PATH = os.path.join(os.path.dirname(__file__), "history.json")
CSV_PATH = os.path.join(os.path.dirname(__file__), "stream_data.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")
CARD_PATH = os.path.join(os.path.dirname(__file__), "battle_card.png")
GOE_SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "goe_summary.png")
COMP_SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "stream_summary.png")
GOE_SUMMARY_RAW_PATH = os.path.join(os.path.dirname(__file__), "goe_summary_raw.png")
COMP_SUMMARY_RAW_PATH = os.path.join(
    os.path.dirname(__file__), "stream_summary_raw.png"
)


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
    """Exports history array to CSV with bot attack details."""
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
        "nerva_yt1_viewers",
        "nerva_yt2_viewers",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pt in history:
            streams = pt.get("streams", {})
            yt_s = streams.get("I2E60nEUXWo", {})
            writer.writerow(
                {
                    "timestamp": pt.get("timestamp", ""),
                    "goe_total": pt.get("goe_total", 0),
                    "goe_total_raw": pt.get("goe_total_raw", pt.get("goe_total", 0)),
                    "is_bot_attack": 1 if pt.get("is_bot_attack") else 0,
                    "nerva_total": pt.get("nerva_total", 0),
                    "goe_stream_viewers": streams.get("goe_stream", {}).get(
                        "viewers", 0
                    ),
                    "goe_yt_viewers": yt_s.get("viewers", 0),
                    "goe_yt_raw_viewers": yt_s.get(
                        "viewers_raw", yt_s.get("viewers", 0)
                    ),
                    "nerva_twitch_viewers": streams.get("nervarien", {}).get(
                        "viewers", 0
                    ),
                    "nerva_yt1_viewers": streams.get("woX6jXefVdw", {}).get(
                        "viewers", 0
                    ),
                    "nerva_yt2_viewers": streams.get("SGAaZFSc3Zk", {}).get(
                        "viewers", 0
                    ),
                }
            )


def build():
    print("⏳ [Build] Pobieranie aktualnych danych o transmisjach...")
    data = fetch_all_data()

    any_live = any(
        s.get("is_live", False)
        for s in data["groups"]["GOE"]["streams"] + data["groups"]["NERVA"]["streams"]
    )

    from db import (
        filter_bot_attacks,
        get_detailed_history,
        get_summary_stats,
        save_snapshot,
    )

    # Load history
    history = []
    if os.path.exists(DB_PATH):
        if any_live:
            save_snapshot(data)
        history = get_detailed_history(limit=5000)
        print(f"📦 [Build] Załadowano {len(history)} próbek z lokalnej bazy SQLite.")
    elif os.path.exists(HISTORY_JSON_PATH):
        try:
            with open(HISTORY_JSON_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    # Clean history: strip corrupted post-stream records and filter bot attacks
    history = filter_bot_attacks(history, enabled=True)

    # Format new snapshot point if streams are live
    if any_live:
        goe_streams = {s["id"]: s for s in data["groups"]["GOE"]["streams"]}
        nerva_streams = {s["id"]: s for s in data["groups"]["NERVA"]["streams"]}
        all_s_map = {**goe_streams, **nerva_streams}

        new_point = {
            "timestamp": data["timestamp"],
            "goe_total": data["groups"]["GOE"]["total_viewers"],
            "goe_total_raw": data["groups"]["GOE"]["total_viewers"],
            "is_bot_attack": False,
            "nerva_total": data["groups"]["NERVA"]["total_viewers"],
            "streams": {
                sid: {
                    "viewers": s.get("viewers", 0),
                    "is_live": s.get("is_live", False),
                }
                for sid, s in all_s_map.items()
            },
        }

        if not history or history[-1].get("timestamp") != new_point["timestamp"]:
            history.append(new_point)

    # Keep at most 5000 points
    if len(history) > 5000:
        history = history[-5000:]

    # Calculate momentum and summary statistics
    momentum = calculate_momentum(history, minutes=5)
    data["momentum"] = momentum
    data["is_live"] = any_live
    data["summary_stats"] = get_summary_stats(custom_history=history, filter_bots=True)
    data["summary_stats_raw"] = get_summary_stats(
        custom_history=history, filter_bots=False
    )

    # Save data.json
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ [Build] Zapisano: {DATA_JSON_PATH}")

    # Save history.json
    with open(HISTORY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)
    print(f"✅ [Build] Zapisano: {HISTORY_JSON_PATH} ({len(history)} punktów)")

    # Save CSV
    export_csv_from_history(history, CSV_PATH)
    print(f"✅ [Build] Zapisano: {CSV_PATH}")

    # Generate graphics (clean and raw)
    try:
        create_battle_card(data, CARD_PATH)
        print(f"📸 [Build] Karta LIVE: {CARD_PATH}")
    except Exception as e:
        print(f"⚠️ [Build] Błąd karty LIVE: {e}")

    try:
        create_summary_card(
            GOE_SUMMARY_PATH, mode="GOE", custom_history=history, filter_bots=True
        )
        print(f"📊 [Build] Wykres GoE (Oczyszczony): {GOE_SUMMARY_PATH}")
        create_summary_card(
            GOE_SUMMARY_RAW_PATH, mode="GOE", custom_history=history, filter_bots=False
        )
        print(f"📊 [Build] Wykres GoE (Surowy z botami): {GOE_SUMMARY_RAW_PATH}")
    except Exception as e:
        print(f"⚠️ [Build] Błąd wykresu GoE: {e}")

    try:
        create_summary_card(
            COMP_SUMMARY_PATH,
            mode="COMPARISON",
            custom_history=history,
            filter_bots=True,
        )
        print(f"⚖️ [Build] Wykres Porównania (Oczyszczony): {COMP_SUMMARY_PATH}")
        create_summary_card(
            COMP_SUMMARY_RAW_PATH,
            mode="COMPARISON",
            custom_history=history,
            filter_bots=False,
        )
        print(f"⚖️ [Build] Wykres Porównania (Surowy z botami): {COMP_SUMMARY_RAW_PATH}")
    except Exception as e:
        print(f"⚠️ [Build] Błąd wykresu porównania: {e}")

    print("\n🎉 [Build] Gotowe! Wszystkie pliki statyczne zostały wygenerowane.")


if __name__ == "__main__":
    build()
