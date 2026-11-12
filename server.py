"""Interactive Web Dashboard & Background Data Collector in GoE Aesthetic with Two Distinct Charts (GoE & Comparison)."""

import json
import os
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import DAYS_CONFIG, get_active_day_id
from db import (
    export_to_csv,
    get_detailed_history,
    get_history,
    get_momentum,
    save_snapshot,
)
from generate_card import create_battle_card
from generate_summary import create_summary_card
from scraper import fetch_all_data

PORT = 5050
POLL_INTERVAL = 15
OFFLINE_TIMEOUT_SECONDS = 30 * 60  # 30 consecutive minutes offline to end collection


class DashboardHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        platform = params.get("platform", ["ALL"])[0]

        if path == "/" or path == "/index.html":
            html_file = os.path.join(os.path.dirname(__file__), "index.html")
            if os.path.exists(html_file):
                with open(html_file, "rb") as f:
                    content = f.read()
            else:
                content = b"<h1>Dashboard index.html not found</h1>"

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)

        elif path == "/api/data":
            active_day = get_active_day_id()
            data_file = os.path.join(
                os.path.dirname(__file__), f"data_{active_day}.json"
            )
            if not os.path.exists(data_file):
                data_file = os.path.join(os.path.dirname(__file__), "data.json")

            data = None
            if os.path.exists(data_file):
                try:
                    with open(data_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = None

            if not data:
                day_cfg = DAYS_CONFIG.get(active_day, {})
                data = fetch_all_data(
                    groups_config=day_cfg.get("groups"), day_id=active_day
                )
                save_snapshot(data, day_id=active_day)
                data["day_id"] = active_day
                data["day_name"] = day_cfg.get("name")
                data["schedule"] = day_cfg.get("schedule", {})
                data["is_finished"] = day_cfg.get("is_finished", False)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif path == "/api/detailed-history":
            limit = int(params.get("limit", [5000])[0])
            history = get_detailed_history(limit=limit)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(history).encode("utf-8"))

        elif path == "/api/history":
            history = get_history(limit=500, platform=platform)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(history).encode("utf-8"))

        elif path == "/api/momentum":
            mom = get_momentum(minutes=5)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(mom).encode("utf-8"))

        elif path == "/api/card":
            data = fetch_all_data()
            save_snapshot(data)
            card_path = os.path.join(os.path.dirname(__file__), "battle_card.png")
            create_battle_card(data, card_path, platform=platform)

            try:
                with open(card_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header(
                    "Content-Disposition", 'inline; filename="battle_card.png"'
                )
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

        elif path == "/api/summary-card":
            mode_param = params.get("mode", ["comparison"])[0].lower()
            if mode_param == "goe":
                mode = "GOE"
                summary_filename = "goe_summary.png"
            elif mode_param == "camps":
                mode = "CAMPS"
                summary_filename = "camps_summary.png"
            else:
                mode = "COMPARISON"
                summary_filename = "stream_summary.png"

            summary_path = os.path.join(os.path.dirname(__file__), summary_filename)
            create_summary_card(summary_path, mode=mode, platform=platform)

            try:
                with open(summary_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header(
                    "Content-Disposition",
                    f'inline; filename="{summary_filename}"',
                )
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

        elif path == "/api/export-csv":
            csv_data = export_to_csv()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Content-Disposition", 'attachment; filename="stream_data.csv"'
            )
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8"))

        else:
            # Serve static repository files if requested (e.g. data_day-2.json, battle_card.png)
            rel_path = path.lstrip("/")
            file_path = os.path.join(os.path.dirname(__file__), rel_path)
            if os.path.isfile(file_path):
                content_type = "application/octet-stream"
                if file_path.endswith(".json"):
                    content_type = "application/json; charset=utf-8"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                elif file_path.endswith(".csv"):
                    content_type = "text/csv; charset=utf-8"
                elif file_path.endswith(".html"):
                    content_type = "text/html; charset=utf-8"
                elif file_path.endswith(".js"):
                    content_type = "application/javascript"
                elif file_path.endswith(".css"):
                    content_type = "text/css"

                with open(file_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return

            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        return


def background_collector_loop():
    """Background thread collecting data every 15 seconds while streams are live,
    updating static dashboard files and generating cards."""
    from build_static import build

    print(f"[Collector] Uruchomiono zbieranie danych co {POLL_INTERVAL}s.")
    print("[Collector] Monitorowanie aktywne dopóki trwają transmisje.")

    base_dir = (
        os.path.dirname(os.path.abspath(__file__))
        if "__file__" in globals()
        else os.getcwd()
    )
    card_path = os.path.join(base_dir, "battle_card.png")
    goe_summary_path = os.path.join(base_dir, "goe_summary.png")
    comparison_summary_path = os.path.join(base_dir, "stream_summary.png")

    consecutive_offline_seconds = 0
    had_live_stream = False

    while True:
        try:
            active_day = get_active_day_id()
            day_cfg = DAYS_CONFIG.get(active_day, {})
            day_finished = day_cfg.get("is_finished", False)
            data = fetch_all_data(
                groups_config=day_cfg.get("groups"), day_id=active_day
            )
            all_streams = [
                s
                for grp in data.get("groups", {}).values()
                for s in grp.get("streams", [])
            ]
            main_streams = [
                s
                for s in all_streams
                if not s.get("is_costream") and not s.get("is_curiosity")
            ]
            any_live = any(s.get("is_live", False) for s in main_streams)

            if any_live and not day_finished:
                had_live_stream = True
                consecutive_offline_seconds = 0
                save_snapshot(data, day_id=active_day)
                build(preloaded_data=data, preloaded_day_id=active_day)
                ts = datetime.now().strftime("%H:%M:%S")
                goe_v = data["groups"]["GOE"]["total_viewers"]
                nerva_v = data["groups"]["NERVA"]["total_viewers"]
                tobias_v = (
                    data["groups"]["TOBIASZ"]["total_viewers"]
                    if "TOBIASZ" in data.get("groups", {})
                    else 0
                )
                print(
                    f"[{ts}] Zapisano: GOE={goe_v:,} | NERVA={nerva_v:,} | TOBIASZ={tobias_v:,}".replace(
                        ",", " "
                    )
                )
            else:
                consecutive_offline_seconds += POLL_INTERVAL
                offline_mins = consecutive_offline_seconds // 60
                ts = datetime.now().strftime("%H:%M:%S")
                if consecutive_offline_seconds % 60 == 0:
                    status_note = (
                        "oczekiwanie na start..."
                        if not had_live_stream
                        else f"offline {offline_mins} min"
                    )
                    print(f"[{ts}] Wszystkie streamy offline ({status_note})...")

                if (
                    had_live_stream
                    and consecutive_offline_seconds >= OFFLINE_TIMEOUT_SECONDS
                ):
                    print(
                        f"[{ts}] Transmisje zakończone (30 min offline). Generowanie podsumowań..."
                    )
                    build()
                    print(
                        "[Collector] Podsumowania zapisane. Przejście w tryb czuwania na kolejne mecze."
                    )
                    had_live_stream = False
                    consecutive_offline_seconds = 0
        except Exception as e:
            print(f"[Collector Error] {e}")

        time.sleep(POLL_INTERVAL)


def run_server(port: int = PORT):
    collector_thread = threading.Thread(target=background_collector_loop, daemon=True)
    collector_thread.start()

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print("\n==========================================================")
    print(f"🚀 Serwer działa w tle na porcie {port}")
    print(f"👉 Główna strona (Spis GoE & Filtry): http://localhost:{port}")
    print("⏱️ Inteligentne zbieranie danych dopóki trwają transmisje!")
    print("==========================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymano serwer.")
        server.server_close()


if __name__ == "__main__":
    p = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        p = int(sys.argv[1])
    run_server(p)
