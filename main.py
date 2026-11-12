"""Main CLI and entry point for GoE vs Nervarien scraper with platform filtering."""

import argparse
import os
import time

from db import export_to_csv, get_summary_stats, save_snapshot
from generate_card import create_battle_card
from generate_summary import create_summary_card
from scraper import fetch_all_data
from server import run_server


def print_cli_summary(data: dict, platform: str = "ALL"):
    """Prints a clean ASCII summary to the terminal."""
    goe_raw = data["groups"]["GOE"]["streams"]
    nerva_raw = data["groups"]["NERVA"]["streams"]

    if platform.upper() == "TWITCH":
        goe_streams = [s for s in goe_raw if s["platform"] == "Twitch"]
        nerva_streams = [s for s in nerva_raw if s["platform"] == "Twitch"]
    elif platform.upper() == "YOUTUBE":
        goe_streams = [s for s in goe_raw if s["platform"] == "YouTube"]
        nerva_streams = [s for s in nerva_raw if s["platform"] == "YouTube"]
    else:
        goe_streams = goe_raw
        nerva_streams = nerva_raw

    goe_total = sum(s.get("viewers", 0) for s in goe_streams)
    nerva_total = sum(s.get("viewers", 0) for s in nerva_streams)
    tot = goe_total + nerva_total
    ratio_goe = round(goe_total / tot * 100, 1) if tot > 0 else 50.0
    ratio_nerva = round(nerva_total / tot * 100, 1) if tot > 0 else 50.0
    diff = abs(goe_total - nerva_total)
    leader = (
        "GOE"
        if goe_total > nerva_total
        else ("NERVA" if nerva_total > goe_total else "REMIS")
    )

    tag = f"[{platform.upper()}] " if platform.upper() != "ALL" else ""

    print("\n" + "=" * 64)
    print(f"🎙️  CO-STREAM GOE vs NERVARIEN {tag}| {data['timestamp']}")
    print("=" * 64)

    print(f"\n🔴 GOE:   {goe_total:,} widzów ({ratio_goe}%)".replace(",", " "))
    print(f"⚪ NERVA: {nerva_total:,} widzów ({ratio_nerva}%)".replace(",", " "))
    print(f"\n🏆 Lider: {leader} (+{diff:,} widzów)".replace(",", " "))
    print("-" * 64)

    print("\n[GOE]")
    for st in goe_streams:
        status = "🔴 LIVE " if st["is_live"] else "⚫ OFFLINE"
        print(
            f"  • [{st['platform']:7}] {status} | {st['viewers']:>5} widzów | {st['channel']} - {st['title'][:32]}"
        )

    print("\n[NERVARIEN]")
    for st in nerva_streams:
        status = "🔴 LIVE " if st["is_live"] else "⚫ OFFLINE"
        print(
            f"  • [{st['platform']:7}] {status} | {st['viewers']:>5} widzów | {st['channel']} - {st['title'][:32]}"
        )

    print("=" * 64 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CO-STREAM GOE vs NERVARIEN")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Uruchom serwer WWW ze zbieraniem w tle co 15s (http://localhost:5050)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="Port serwera WWW (domyślnie 5050)",
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="ALL",
        choices=["ALL", "Twitch", "YouTube", "all", "twitch", "youtube"],
        help="Filtruj platformę (ALL, Twitch, YouTube)",
    )
    parser.add_argument(
        "--card",
        action="store_true",
        help="Wygeneruj kartę live (battle_card.png) i zakończ",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Wygeneruj podsumowanie liniowe (stream_summary.png lub goe_summary.png)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="COMPARISON",
        choices=["GOE", "COMPARISON", "goe", "comparison"],
        help="Tryb wykresu podsumowania: GOE lub COMPARISON (domyślnie COMPARISON)",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        nargs="?",
        const="stream_history.csv",
        help="Eksportuj historię do pliku CSV (domyślnie stream_history.csv)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        nargs="?",
        const=15,
        default=0,
        help="Pętla monitorowania co N sekund (domyślnie 15s)",
    )

    args = parser.parse_args()
    platform = args.platform.upper()

    if args.web:
        run_server(args.port)
        return

    if args.export_csv:
        csv_file = export_to_csv(args.export_csv)
        print(f"📁 Wyeksportowano dane do pliku: {csv_file}")
        return

    card_path = os.path.join(os.path.dirname(__file__), "battle_card.png")
    summary_path = os.path.join(os.path.dirname(__file__), "stream_summary.png")

    if args.summary:
        mode = args.mode.upper()
        summary_filename = "goe_summary.png" if mode == "GOE" else "stream_summary.png"
        summary_path = os.path.join(os.path.dirname(__file__), summary_filename)
        create_summary_card(summary_path, mode=mode, platform=platform)
        stats = get_summary_stats(platform=platform)
        print(
            f"📊 Tryb: {mode} | Próbki w bazie ({platform}): {stats['count']} (od {stats['start_time']} do {stats['end_time']})"
        )
        print(
            f"🔴 Pik GOE:   {stats['goe_peak']:,} (o {stats['goe_peak_time']}) | Średnia: {stats['goe_avg']:,}".replace(
                ",", " "
            )
        )
        if mode == "COMPARISON":
            print(
                f"⚪ Pik NERVA: {stats['nerva_peak']:,} (o {stats['nerva_peak_time']}) | Średnia: {stats['nerva_avg']:,}".replace(
                    ",", " "
                )
            )
        print(f"📸 Zapisano podsumowanie liniowe ({mode}): {summary_path}")
        return

    if args.loop > 0:
        print(f"Pętla zbierania danych co {args.loop}s. Ctrl+C aby zatrzymać.\n")
        try:
            while True:
                data = fetch_all_data()
                save_snapshot(data)
                print_cli_summary(data, platform=platform)
                create_battle_card(data, card_path, platform=platform)
                create_summary_card(summary_path, platform=platform)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nZatrzymano.")
            return

    # Single run
    data = fetch_all_data()
    save_snapshot(data)
    print_cli_summary(data, platform=platform)
    create_battle_card(data, card_path, platform=platform)
    create_summary_card(summary_path, platform=platform)
    print(f"📸 Karta LIVE:           {card_path}")
    print(f"📊 Podsumowanie liniowe: {summary_path}")


if __name__ == "__main__":
    main()
