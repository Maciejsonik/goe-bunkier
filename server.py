"""Interactive Web Dashboard & Background Data Collector in GoE Aesthetic with Two Distinct Charts (GoE & Comparison)."""

from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys
import threading
import time
import urllib.parse

from db import (
    export_to_csv,
    get_detailed_history,
    get_history,
    get_momentum,
    get_summary_stats,
    save_snapshot,
)
from generate_card import create_battle_card
from generate_summary import create_summary_card
from scraper import fetch_all_data

PORT = 5050
POLL_INTERVAL = 15
OFFLINE_TIMEOUT_SECONDS = 30 * 60  # 30 consecutive minutes offline to end collection

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CO-STREAM GOE • Spis Widzów & Porównanie</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-dark: #08080a;
            --card-bg: #0e0e12;
            --card-border: #ff1824;
            --goe-red: #ff1824;
            --goe-dark-red: #8f0e15;
            --text-main: #ffffff;
            --text-muted: #a1a1aa;
            --twitch-color: #9146ff;
            --yt-color: #ff0000;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            padding: 24px;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(255, 24, 36, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(255, 24, 36, 0.08) 0%, transparent 40%);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--goe-dark-red);
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-emblem {
            font-size: 14px;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .header-title h1 {
            font-size: 34px;
            font-weight: 900;
            letter-spacing: -0.5px;
            color: var(--goe-red);
            text-transform: uppercase;
            font-style: italic;
        }

        .header-title p {
            color: var(--text-muted);
            font-size: 14px;
            margin-top: 4px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        button, select {
            background-color: #141418;
            color: white;
            border: 1px solid #27272a;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        button:hover {
            border-color: var(--goe-red);
            background-color: #1f1f24;
        }

        .btn-primary { background-color: #27272a; border-color: #3f3f46; }
        .btn-red { background-color: var(--goe-red); border-color: var(--goe-red); color: white; }
        .btn-red:hover { background-color: #d6131d; box-shadow: 0 0 15px rgba(255, 24, 36, 0.4); }
        .btn-summary { background: linear-gradient(135deg, #18181b, #27272a); border: 1px solid var(--goe-red); color: white; }

        /* Main View Mode Selector Tabs */
        .mode-tabs {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            border-bottom: 1px solid #27272a;
            padding-bottom: 12px;
        }

        .mode-tab {
            background: #101014;
            border: 1px solid #27272a;
            padding: 10px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 800;
            color: #a1a1aa;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .mode-tab.active {
            background: var(--goe-red);
            border-color: var(--goe-red);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 24, 36, 0.3);
        }

        /* Granular Stream Filter Bar */
        .filter-section {
            background: #101014;
            border: 1px solid #27272a;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 24px;
        }

        .filter-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .filter-title {
            font-size: 12px;
            font-weight: 800;
            color: #a1a1aa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .preset-buttons {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .preset-btn {
            background: #18181b;
            border: 1px solid #3f3f46;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            color: #d4d4d8;
        }

        .preset-btn:hover {
            border-color: var(--goe-red);
            color: white;
        }

        .stream-chips {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .stream-chip {
            background: #141418;
            border: 1.5px solid #27272a;
            padding: 7px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            color: #71717a;
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 8px;
            user-select: none;
        }

        .stream-chip.selected {
            border-color: var(--goe-red);
            color: #ffffff;
            background: rgba(255, 24, 36, 0.12);
        }

        .stream-chip.selected.nerva-chip {
            border-color: #ffffff;
            background: rgba(255, 255, 255, 0.1);
        }

        .chip-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #52525b;
        }

        .stream-chip.selected .chip-dot {
            background: var(--goe-red);
            box-shadow: 0 0 8px var(--goe-red);
        }

        .stream-chip.selected.nerva-chip .chip-dot {
            background: #ffffff;
            box-shadow: 0 0 8px #ffffff;
        }

        /* GoE Viewers Hub (Main Page) */
        .goe-hub {
            margin-bottom: 24px;
        }

        .hero-goe-card {
            background: var(--card-bg);
            border: 2px solid var(--goe-red);
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 20px;
            box-shadow: 0 4px 30px rgba(255, 24, 36, 0.15);
        }

        .hero-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .hero-title-group h2 {
            font-size: 14px;
            font-weight: 800;
            color: var(--goe-red);
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .hero-total-viewers {
            font-size: 68px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1;
            margin-top: 6px;
        }

        .momentum-badge {
            font-size: 13px;
            font-weight: 800;
            padding: 5px 12px;
            border-radius: 6px;
            display: inline-block;
            background: rgba(255, 255, 255, 0.05);
            color: #a1a1aa;
        }

        .momentum-up { color: #4ade80; background: rgba(74, 222, 128, 0.1); }
        .momentum-down { color: #f87171; background: rgba(248, 113, 113, 0.1); }

        /* GoE Breakdown Subcards */
        .goe-breakdown {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }

        @media (max-width: 640px) {
            .goe-breakdown { grid-template-columns: 1fr; }
        }

        .breakdown-box {
            background: #141418;
            border: 1px solid #27272a;
            border-radius: 10px;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .breakdown-platform {
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            color: #a1a1aa;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .breakdown-val {
            font-size: 28px;
            font-weight: 900;
            color: #ffffff;
        }

        .breakdown-pct {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 700;
        }

        .goe-bar-container {
            width: 100%;
            height: 12px;
            background: #18181b;
            border-radius: 6px;
            overflow: hidden;
            display: flex;
        }

        .goe-bar-yt { background: #ff0000; height: 100%; transition: width 0.4s; }
        .goe-bar-tw { background: #9146ff; height: 100%; transition: width 0.4s; }

        /* Battle View Scoreboard */
        .battle-view {
            display: none;
            margin-bottom: 24px;
        }

        .scoreboard {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 20px;
            align-items: center;
            margin-bottom: 20px;
        }

        @media (max-width: 768px) {
            .scoreboard { grid-template-columns: 1fr; }
        }

        .team-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            border: 2px solid var(--goe-red);
            position: relative;
            box-shadow: 0 4px 25px rgba(255, 24, 36, 0.1);
        }

        .team-card.nerva { border-color: #3f3f46; box-shadow: none; }
        .team-name { font-size: 14px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; color: var(--goe-red); }
        .team-card.nerva .team-name { color: #a1a1aa; }
        .team-score { font-size: 54px; font-weight: 900; line-height: 1; margin-bottom: 6px; color: #ffffff; }
        .team-share { font-size: 14px; color: var(--text-muted); font-weight: 700; margin-bottom: 8px; }

        .vs-badge {
            font-size: 20px;
            font-weight: 900;
            background: #141418;
            color: #ffffff;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid var(--goe-red);
            margin: 0 auto;
        }

        .battle-bar-container {
            width: 100%;
            height: 18px;
            background: #141418;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            margin-bottom: 20px;
            border: 1px solid #27272a;
        }

        .bar-segment-goe { height: 100%; background: var(--goe-red); transition: width 0.4s; }
        .bar-segment-nerva { height: 100%; background: #3f3f46; transition: width 0.4s; }

        /* Switch Battle Promo Banner */
        .battle-banner {
            background: #141418;
            border: 1px dashed var(--goe-red);
            border-radius: 8px;
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .battle-banner:hover {
            background: rgba(255, 24, 36, 0.08);
            border-style: solid;
        }

        /* Streams Grid */
        .streams-section {
            margin-bottom: 24px;
        }

        .column-title {
            font-size: 14px;
            font-weight: 800;
            color: var(--text-main);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .streams-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        @media (max-width: 860px) {
            .streams-grid { grid-template-columns: 1fr; }
        }

        .stream-item {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 14px;
            border: 1.5px solid #27272a;
            display: flex;
            align-items: center;
            gap: 14px;
            transition: all 0.2s;
            text-decoration: none;
            color: inherit;
        }

        .stream-item:hover {
            border-color: var(--goe-red);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 24, 36, 0.15);
        }

        .avatar-box {
            width: 52px;
            height: 52px;
            border-radius: 6px;
            border: 2px solid var(--goe-red);
            overflow: hidden;
            flex-shrink: 0;
            background: #18181b;
        }

        .avatar-box img { width: 100%; height: 100%; object-fit: cover; }
        .stream-info { flex-grow: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
        .stream-item-header { display: flex; justify-content: space-between; align-items: center; }
        .platform-badge { font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; color: white; text-transform: uppercase; }
        .badge-twitch { background-color: var(--twitch-color); }
        .badge-yt { background-color: var(--yt-color); }
        .channel-name { font-weight: 800; font-size: 15px; display: flex; align-items: center; gap: 6px; }
        .live-dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--goe-red); box-shadow: 0 0 10px var(--goe-red); display: inline-block; }
        .offline-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #52525b; display: inline-block; }
        .stream-viewers { font-size: 18px; font-weight: 900; color: #ffffff; flex-shrink: 0; }
        .stream-title { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        /* Chart container */
        .chart-box {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 2px solid #27272a;
            margin-top: 20px;
            margin-bottom: 24px;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .chart-title { font-size: 14px; font-weight: 800; color: var(--text-main); text-transform: uppercase; letter-spacing: 1px; }

        .chart-wrapper {
            position: relative;
            height: 350px;
            width: 100%;
        }

        .time-range-group {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }

        .time-btn {
            background: #141418;
            border: 1px solid #27272a;
            color: #a1a1aa;
            padding: 5px 11px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s;
        }

        .time-btn:hover {
            border-color: #52525b;
            color: #ffffff;
        }

        .time-btn.active {
            background: var(--goe-red);
            border-color: var(--goe-red);
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(255, 24, 36, 0.3);
        }

        footer { text-align: center; padding-top: 16px; border-top: 1px solid #27272a; color: #71717a; font-size: 13px; }
        .roster-pipes { color: #d4d4d8; font-weight: 800; letter-spacing: 1px; margin-bottom: 6px; font-size: 14px; }

        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #18181b;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            border: 1px solid var(--goe-red);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: none;
            z-index: 100;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <div class="header-emblem">🎙️  |  WORLDS 2026</div>
                <h1>CO-STREAM GOE</h1>
                <p id="last-updated">Ładowanie danych...</p>
            </div>
            <div class="header-controls">
                <select id="auto-refresh-select" onchange="setupAutoRefresh()">
                    <option value="15" selected>Auto: 15s</option>
                    <option value="30">Auto: 30s</option>
                    <option value="60">Auto: 60s</option>
                    <option value="0">Auto: wyłączone</option>
                </select>
                <button class="btn-primary" onclick="loadData(true)">🔄 Odśwież</button>
                <button class="btn-red" onclick="downloadLiveCard()">📸 Karta LIVE</button>
                <button class="btn-summary" onclick="downloadSummaryCard('goe')">📊 Wykres GoE</button>
                <button class="btn-summary" onclick="downloadSummaryCard('comparison')">⚖️ Wykres Porównania</button>
                <button class="btn-primary" onclick="downloadCSV()">📥 CSV</button>
            </div>
        </header>

        <!-- Main View Mode Tabs (GoE Viewers Hub is DEFAULT!) -->
        <div class="mode-tabs">
            <button class="mode-tab active" id="tab-goe" onclick="switchMode('goe')">
                🔴 Spis Widzów GoE
            </button>
            <button class="mode-tab" id="tab-battle" onclick="switchMode('battle')">
                ⚖️ Porównanie z Nervarienem
            </button>
        </div>

        <!-- Granular Stream Filter Bar (Allows selecting down to individual stream) -->
        <div class="filter-section">
            <div class="filter-header">
                <div class="filter-title">🔍 Filtry transmisji (kliknij, aby wybrać pojedyncze streamy):</div>
                <div class="preset-buttons">
                    <button class="preset-btn" onclick="applyPreset('goe_only')">Tylko GoE</button>
                    <button class="preset-btn" onclick="applyPreset('all')">Wszystkie 5</button>
                    <button class="preset-btn" onclick="applyPreset('twitch')">Tylko Twitch</button>
                    <button class="preset-btn" onclick="applyPreset('youtube')">Tylko YouTube</button>
                </div>
            </div>
            <div class="stream-chips" id="stream-chips-container">
                <!-- Dynamically populated stream toggle pills -->
            </div>
        </div>

        <!-- Mode 1: GoE Viewers Hub (Default View) -->
        <div id="view-goe" class="goe-hub">
            <div class="hero-goe-card">
                <div class="hero-header">
                    <div class="hero-title-group">
                        <h2>WIDOWNIA CO-STREAM GOE (Kielecki Bunkier)</h2>
                        <div class="hero-total-viewers" id="goe-hero-total">--</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="momentum-badge" id="goe-hero-momentum">Trend: --</div>
                        <div style="font-size: 13px; color: var(--text-muted); margin-top: 6px;" id="goe-hero-peak">Pik: --</div>
                    </div>
                </div>

                <div class="goe-breakdown">
                    <div class="breakdown-box">
                        <div>
                            <div class="breakdown-platform"><span class="live-dot" style="background:#ff0000; box-shadow: 0 0 8px #ff0000;"></span> YouTube (Gadają o Esporcie)</div>
                            <div class="breakdown-val" id="goe-yt-viewers">--</div>
                        </div>
                        <div class="breakdown-pct" id="goe-yt-pct">--% widowni</div>
                    </div>
                    <div class="breakdown-box">
                        <div>
                            <div class="breakdown-platform"><span class="live-dot" style="background:#9146ff; box-shadow: 0 0 8px #9146ff;"></span> Twitch (GoE_stream)</div>
                            <div class="breakdown-val" id="goe-tw-viewers">--</div>
                        </div>
                        <div class="breakdown-pct" id="goe-tw-pct">--% widowni</div>
                    </div>
                </div>

                <div class="goe-bar-container">
                    <div id="goe-sub-bar-yt" class="goe-bar-yt" style="width: 50%;"></div>
                    <div id="goe-sub-bar-tw" class="goe-bar-tw" style="width: 50%;"></div>
                </div>
            </div>

            <!-- Switch to Comparison Mode Quick Banner -->
            <div class="battle-banner" onclick="switchMode('battle')">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 20px;">⚖️</span>
                    <div>
                        <div style="font-weight: 800; font-size: 14px; color: #ffffff;">Chcesz zobaczyć porównanie z Nervarienem?</div>
                        <div style="font-size: 12px; color: #a1a1aa;">Zobacz aktualny bilans sił, różnicę i proporcje pomiędzy obozami.</div>
                    </div>
                </div>
                <div style="font-weight: 800; color: var(--goe-red); font-size: 13px;">Zobacz Porównanie →</div>
            </div>

            <!-- Dedicated GoE Stream List -->
            <div class="streams-section">
                <div class="column-title">Transmisje GoE (Kielecki Bunkier)</div>
                <div class="streams-grid" id="goe-streams-grid"></div>
            </div>

            <!-- DEDICATED CHART 1: GoE ONLY -->
            <div class="chart-box">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">📈 Przebieg widowni GoE w czasie (YouTube vs Twitch)</div>
                        <div id="goe-chart-sub-label" style="font-size: 12px; color: #a1a1aa; margin-top: 4px;">Ładowanie historii GoE...</div>
                    </div>
                    <div class="time-range-group">
                        <span style="font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; margin-right: 4px;">Zakres:</span>
                        <button class="time-btn time-goe-15m" onclick="setTimeRange('15m')">15 min</button>
                        <button class="time-btn time-goe-30m" onclick="setTimeRange('30m')">30 min</button>
                        <button class="time-btn time-goe-1h" onclick="setTimeRange('1h')">1 godz.</button>
                        <button class="time-btn time-goe-2h" onclick="setTimeRange('2h')">2 godz.</button>
                        <button class="time-btn time-goe-all active" onclick="setTimeRange('all')">Cały stream</button>
                    </div>
                </div>
                <div class="chart-wrapper">
                    <canvas id="goeChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Mode 2: Battle / Comparison View (Head-to-head vs Nervarien) -->
        <div id="view-battle" class="battle-view">
            <div class="scoreboard">
                <div class="team-card goe">
                    <div class="team-name">GOE</div>
                    <div class="team-score" id="battle-goe-score">--</div>
                    <div class="team-share" id="battle-goe-share">--% widowni</div>
                    <div class="momentum-badge" id="battle-goe-momentum">Trend: --</div>
                </div>
                <div class="vs-badge">VS</div>
                <div class="team-card nerva">
                    <div class="team-name">NERVARIEN</div>
                    <div class="team-score" id="battle-nerva-score">--</div>
                    <div class="team-share" id="battle-nerva-share">--% widowni</div>
                    <div class="momentum-badge" id="battle-nerva-momentum">Trend: --</div>
                </div>
            </div>

            <div class="battle-bar-container">
                <div id="battle-bar-goe" class="bar-segment-goe" style="width: 50%;"></div>
                <div id="battle-bar-nerva" class="bar-segment-nerva" style="width: 50%;"></div>
            </div>

            <!-- Comparison Streams Grid -->
            <div class="streams-section">
                <div class="column-title">Transmisje obu obozów (GoE & Nervarien)</div>
                <div class="streams-grid" id="battle-streams-grid"></div>
            </div>

            <!-- DEDICATED CHART 2: COMPARISON (GoE vs Nervarien) -->
            <div class="chart-box">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">⚖️ Przebieg Porównania w czasie: GoE vs Nervarien</div>
                        <div id="comp-chart-sub-label" style="font-size: 12px; color: #a1a1aa; margin-top: 4px;">Ładowanie historii porównania...</div>
                    </div>
                    <div class="time-range-group">
                        <span style="font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; margin-right: 4px;">Zakres:</span>
                        <button class="time-btn time-comp-15m" onclick="setTimeRange('15m')">15 min</button>
                        <button class="time-btn time-comp-30m" onclick="setTimeRange('30m')">30 min</button>
                        <button class="time-btn time-comp-1h" onclick="setTimeRange('1h')">1 godz.</button>
                        <button class="time-btn time-comp-2h" onclick="setTimeRange('2h')">2 godz.</button>
                        <button class="time-btn time-comp-all active" onclick="setTimeRange('all')">Cały stream</button>
                    </div>
                </div>
                <div class="chart-wrapper">
                    <canvas id="comparisonChart"></canvas>
                </div>
            </div>
        </div>

        <footer>
            <div class="roster-pipes">DEJF | CZARNYPIOTRUS | BIALITO | MAJUTEK | PEDRO | MAGVAYER | JASKIER</div>
            <div style="font-size: 16px; font-weight: 900; color: var(--goe-red); letter-spacing: 2px; margin: 8px 0 4px 0;">#bunkier</div>
            <div>Oficjalny system statystyk widowni Co-stream GoE</div>
        </footer>
    </div>

    <div id="toast"></div>

    <script>
        let currentMode = 'goe'; // 'goe' (default) or 'battle'
        let currentTimeRange = 'all'; // '15m', '30m', '1h', '2h', 'all'
        let rawData = null;
        let detailedHistory = [];
        let autoInterval = null;
        let goeChartInstance = null;
        let comparisonChartInstance = null;

        // Set of currently selected stream IDs
        const ALL_STREAM_IDS = ['goe_stream', 'I2E60nEUXWo', 'nervarien', 'woX6jXefVdw', 'SGAaZFSc3Zk'];
        let selectedStreamIds = new Set(['goe_stream', 'I2E60nEUXWo']);

        const STREAM_METADATA = {
            'goe_stream': { name: 'GoE Twitch', platform: 'Twitch', group: 'GOE', color: '#9146ff' },
            'I2E60nEUXWo': { name: 'GoE YouTube', platform: 'YouTube', group: 'GOE', color: '#ff1824' },
            'nervarien': { name: 'Nervarien Twitch', platform: 'Twitch', group: 'NERVA', color: '#a855f7' },
            'woX6jXefVdw': { name: 'Nervarien YT #1', platform: 'YouTube', group: 'NERVA', color: '#f97316' },
            'SGAaZFSc3Zk': { name: 'Nervarien YT #2', platform: 'YouTube', group: 'NERVA', color: '#ef4444' }
        };

        function initCharts() {
            const commonScales = {
                x: { ticks: { color: '#71717a' }, grid: { color: '#18181b' } },
                y: { ticks: { color: '#71717a' }, grid: { color: '#18181b' }, beginAtZero: true }
            };
            const commonTooltip = {
                backgroundColor: '#141418',
                borderColor: '#ff1824',
                borderWidth: 1,
                titleColor: '#ffffff',
                bodyColor: '#e4e4e7',
                padding: 10
            };

            // 1. GoE Dedicated Chart
            const ctxGoe = document.getElementById('goeChart').getContext('2d');
            goeChartInstance = new Chart(ctxGoe, {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#d4d4d8', font: { weight: 'bold' } } },
                        tooltip: commonTooltip
                    },
                    scales: commonScales
                }
            });

            // 2. Comparison Dedicated Chart
            const ctxComp = document.getElementById('comparisonChart').getContext('2d');
            comparisonChartInstance = new Chart(ctxComp, {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#d4d4d8', font: { weight: 'bold' } } },
                        tooltip: commonTooltip
                    },
                    scales: commonScales
                }
            });
        }

        function switchMode(mode) {
            currentMode = mode;
            if (mode === 'goe') {
                document.getElementById('tab-goe').classList.add('active');
                document.getElementById('tab-battle').classList.remove('active');
                document.getElementById('view-goe').style.display = 'block';
                document.getElementById('view-battle').style.display = 'none';
                selectedStreamIds = new Set(['goe_stream', 'I2E60nEUXWo']);
                setTimeout(() => { if (goeChartInstance) goeChartInstance.resize(); }, 50);
            } else {
                document.getElementById('tab-goe').classList.remove('active');
                document.getElementById('tab-battle').classList.add('active');
                document.getElementById('view-goe').style.display = 'none';
                document.getElementById('view-battle').style.display = 'block';
                selectedStreamIds = new Set(ALL_STREAM_IDS);
                setTimeout(() => { if (comparisonChartInstance) comparisonChartInstance.resize(); }, 50);
            }
            renderFilterChips();
            updateUI();
        }

        function applyPreset(preset) {
            if (preset === 'goe_only') {
                selectedStreamIds = new Set(['goe_stream', 'I2E60nEUXWo']);
                if (currentMode !== 'goe') switchMode('goe');
            } else if (preset === 'all') {
                selectedStreamIds = new Set(ALL_STREAM_IDS);
                if (currentMode !== 'battle') switchMode('battle');
            } else if (preset === 'twitch') {
                selectedStreamIds = new Set(['goe_stream', 'nervarien']);
            } else if (preset === 'youtube') {
                selectedStreamIds = new Set(['I2E60nEUXWo', 'woX6jXefVdw', 'SGAaZFSc3Zk']);
            }
            renderFilterChips();
            updateUI();
        }

        function toggleStream(streamId) {
            if (selectedStreamIds.has(streamId)) {
                if (selectedStreamIds.size > 1) {
                    selectedStreamIds.delete(streamId);
                } else {
                    showToast('Przynajmniej jeden stream musi być zaznaczony!');
                    return;
                }
            } else {
                selectedStreamIds.add(streamId);
            }
            renderFilterChips();
            updateUI();
        }

        function renderFilterChips() {
            const container = document.getElementById('stream-chips-container');
            container.innerHTML = '';

            ALL_STREAM_IDS.forEach(id => {
                const meta = STREAM_METADATA[id];
                const isSelected = selectedStreamIds.has(id);
                const isNerva = meta.group === 'NERVA';

                let viewers = 0;
                if (rawData) {
                    const allS = [...rawData.groups.GOE.streams, ...rawData.groups.NERVA.streams];
                    const found = allS.find(s => s.id === id);
                    if (found) viewers = found.viewers;
                }

                const chip = document.createElement('div');
                chip.className = `stream-chip ${isSelected ? 'selected' : ''} ${isNerva ? 'nerva-chip' : ''}`;
                chip.onclick = () => toggleStream(id);
                chip.innerHTML = `
                    <span class="chip-dot"></span>
                    <span>${meta.name}</span>
                    <span style="font-weight: 800; opacity: 0.85;">(${viewers.toLocaleString('pl-PL')})</span>
                `;
                container.appendChild(chip);
            });
        }

        function updateUI() {
            if (!rawData) return;

            const goeStreams = (rawData.groups.GOE.streams || []).map(s => ({ ...s, group: 'GOE' }));
            const nervaStreams = (rawData.groups.NERVA.streams || []).map(s => ({ ...s, group: 'NERVA' }));

            // 1. Update GoE Hub
            const goeYt = goeStreams.find(s => s.id === 'I2E60nEUXWo');
            const goeTw = goeStreams.find(s => s.id === 'goe_stream');
            const ytV = (goeYt && selectedStreamIds.has('I2E60nEUXWo')) ? goeYt.viewers : (goeYt ? goeYt.viewers : 0);
            const twV = (goeTw && selectedStreamIds.has('goe_stream')) ? goeTw.viewers : (goeTw ? goeTw.viewers : 0);
            const goeTotal = ytV + twV;
            const goeSumForPct = (ytV + twV) || 1;

            document.getElementById('goe-hero-total').innerText = goeTotal.toLocaleString('pl-PL');
            document.getElementById('goe-yt-viewers').innerText = ytV.toLocaleString('pl-PL');
            document.getElementById('goe-tw-viewers').innerText = twV.toLocaleString('pl-PL');
            document.getElementById('goe-yt-pct').innerText = `${((ytV / goeSumForPct) * 100).toFixed(1)}% widowni`;
            document.getElementById('goe-tw-pct').innerText = `${((twV / goeSumForPct) * 100).toFixed(1)}% widowni`;
            document.getElementById('goe-sub-bar-yt').style.width = `${((ytV / goeSumForPct) * 100).toFixed(1)}%`;
            document.getElementById('goe-sub-bar-tw').style.width = `${((twV / goeSumForPct) * 100).toFixed(1)}%`;

            // 2. Update Comparison Scoreboard
            const goeSelected = goeStreams.filter(s => selectedStreamIds.has(s.id));
            const nervaSelected = nervaStreams.filter(s => selectedStreamIds.has(s.id));
            const battleGoeTot = goeSelected.reduce((a, s) => a + (s.viewers || 0), 0);
            const battleNervaTot = nervaSelected.reduce((a, s) => a + (s.viewers || 0), 0);
            const battleTot = battleGoeTot + battleNervaTot;
            const bGoePct = battleTot > 0 ? (battleGoeTot / battleTot * 100).toFixed(1) : 50.0;
            const bNervaPct = battleTot > 0 ? (battleNervaTot / battleTot * 100).toFixed(1) : 50.0;

            document.getElementById('battle-goe-score').innerText = battleGoeTot.toLocaleString('pl-PL');
            document.getElementById('battle-goe-share').innerText = `${bGoePct}% widowni (${battleGoeTot.toLocaleString('pl-PL')})`;
            document.getElementById('battle-nerva-score').innerText = battleNervaTot.toLocaleString('pl-PL');
            document.getElementById('battle-nerva-share').innerText = `${bNervaPct}% widowni (${battleNervaTot.toLocaleString('pl-PL')})`;
            document.getElementById('battle-bar-goe').style.width = `${bGoePct}%`;
            document.getElementById('battle-bar-nerva').style.width = `${bNervaPct}%`;

            // 3. Render Stream Cards
            renderStreamsGrids(goeStreams, nervaStreams);

            // 4. Update Charts
            updateChartSeries();
        }

        function renderStreamsGrids(goeStreams, nervaStreams) {
            // Render to GoE grid
            const goeVisible = goeStreams.filter(s => selectedStreamIds.has(s.id));
            renderCardList(document.getElementById('goe-streams-grid'), goeVisible.length > 0 ? goeVisible : goeStreams);

            // Render to Battle grid
            const allStreams = [...goeStreams, ...nervaStreams];
            const battleVisible = allStreams.filter(s => selectedStreamIds.has(s.id));
            renderCardList(document.getElementById('battle-streams-grid'), battleVisible.length > 0 ? battleVisible : allStreams);
        }

        function renderCardList(grid, streams) {
            if (!grid) return;
            grid.innerHTML = '';
            streams.forEach(st => {
                const isTwitch = st.platform === 'Twitch';
                const badgeClass = isTwitch ? 'badge-twitch' : 'badge-yt';
                const dotClass = st.is_live ? 'live-dot' : 'offline-dot';
                const viewersText = st.is_live ? `${st.viewers.toLocaleString('pl-PL')} widzów` : 'OFFLINE';
                const avatarSrc = st.avatar_url || 'https://static-cdn.jtvnw.net/user-default-pictures-uv/cdd517eb-aca7-43f8-963e-aca743f8963e-profile_image-150x150.png';

                const a = document.createElement('a');
                a.className = 'stream-item';
                a.href = st.url;
                a.target = '_blank';
                a.innerHTML = `
                    <div class="avatar-box">
                        <img src="${avatarSrc}" alt="${st.channel}" loading="lazy" onerror="this.style.display='none'">
                    </div>
                    <div class="stream-info">
                        <div class="stream-item-header">
                            <div class="channel-name">
                                <span class="${dotClass}"></span>
                                <span class="platform-badge ${badgeClass}">${st.platform}</span>
                                <span>${st.channel}</span>
                            </div>
                        </div>
                        <div class="stream-title" title="${st.title}">${st.title || ''}</div>
                    </div>
                    <div class="stream-viewers">${viewersText}</div>
                `;
                grid.appendChild(a);
            });
        }

        function updateChartSeries() {
            if (!detailedHistory || detailedHistory.length === 0) return;

            const labels = detailedHistory.map(pt => pt.timestamp.split(' ')[1] || pt.timestamp);

            // --- 1. UPDATE GOE DEDICATED CHART (ONLY GOE) ---
            if (goeChartInstance) {
                const goeDatasets = [];

                // Total GoE Line
                const totalGoeData = detailedHistory.map(pt => {
                    let sum = 0;
                    if (pt.streams['I2E60nEUXWo'] && selectedStreamIds.has('I2E60nEUXWo')) sum += pt.streams['I2E60nEUXWo'].viewers;
                    else if (!selectedStreamIds.has('I2E60nEUXWo') && !selectedStreamIds.has('goe_stream')) {
                        if (pt.streams['I2E60nEUXWo']) sum += pt.streams['I2E60nEUXWo'].viewers;
                    }
                    if (pt.streams['goe_stream'] && selectedStreamIds.has('goe_stream')) sum += pt.streams['goe_stream'].viewers;
                    else if (!selectedStreamIds.has('I2E60nEUXWo') && !selectedStreamIds.has('goe_stream')) {
                        if (pt.streams['goe_stream']) sum += pt.streams['goe_stream'].viewers;
                    }
                    return sum;
                });

                goeDatasets.push({
                    label: 'GoE Łącznie (Bunkier)',
                    data: totalGoeData,
                    borderColor: '#ff1824',
                    backgroundColor: 'rgba(255, 24, 36, 0.15)',
                    tension: 0.25,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: labels.length > 60 ? 0 : 3
                });

                if (selectedStreamIds.has('I2E60nEUXWo') || (!selectedStreamIds.has('I2E60nEUXWo') && !selectedStreamIds.has('goe_stream'))) {
                    goeDatasets.push({
                        label: 'YouTube (Gadają o Esporcie)',
                        data: detailedHistory.map(pt => pt.streams['I2E60nEUXWo'] ? pt.streams['I2E60nEUXWo'].viewers : 0),
                        borderColor: '#ef4444',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        fill: false,
                        pointRadius: labels.length > 60 ? 0 : 2
                    });
                }

                if (selectedStreamIds.has('goe_stream') || (!selectedStreamIds.has('I2E60nEUXWo') && !selectedStreamIds.has('goe_stream'))) {
                    goeDatasets.push({
                        label: 'Twitch (GoE_stream)',
                        data: detailedHistory.map(pt => pt.streams['goe_stream'] ? pt.streams['goe_stream'].viewers : 0),
                        borderColor: '#9146ff',
                        borderDash: [3, 3],
                        borderWidth: 2,
                        fill: false,
                        pointRadius: labels.length > 60 ? 0 : 2
                    });
                }

                goeChartInstance.data.labels = labels;
                goeChartInstance.data.datasets = goeDatasets;
                goeChartInstance.update();
            }

            // --- 2. UPDATE COMPARISON DEDICATED CHART (GOE VS NERVA) ---
            if (comparisonChartInstance) {
                const compDatasets = [];

                const goeLine = detailedHistory.map(pt => {
                    let s = 0;
                    ['I2E60nEUXWo', 'goe_stream'].forEach(id => {
                        if (selectedStreamIds.has(id) && pt.streams[id]) s += pt.streams[id].viewers;
                    });
                    if (s === 0) {
                        ['I2E60nEUXWo', 'goe_stream'].forEach(id => {
                            if (pt.streams[id]) s += pt.streams[id].viewers;
                        });
                    }
                    return s;
                });

                const nervaLine = detailedHistory.map(pt => {
                    let s = 0;
                    ['nervarien', 'woX6jXefVdw', 'SGAaZFSc3Zk'].forEach(id => {
                        if (selectedStreamIds.has(id) && pt.streams[id]) s += pt.streams[id].viewers;
                    });
                    if (s === 0) {
                        ['nervarien', 'woX6jXefVdw', 'SGAaZFSc3Zk'].forEach(id => {
                            if (pt.streams[id]) s += pt.streams[id].viewers;
                        });
                    }
                    return s;
                });

                compDatasets.push({
                    label: 'GOE (Kielecki Bunkier)',
                    data: goeLine,
                    borderColor: '#ff1824',
                    backgroundColor: 'rgba(255, 24, 36, 0.15)',
                    tension: 0.25,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: labels.length > 60 ? 0 : 3
                });

                compDatasets.push({
                    label: 'NERVARIEN (Łącznie)',
                    data: nervaLine,
                    borderColor: '#ffffff',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    tension: 0.25,
                    fill: true,
                    borderWidth: 2.5,
                    pointRadius: labels.length > 60 ? 0 : 3
                });

                comparisonChartInstance.data.labels = labels;
                comparisonChartInstance.data.datasets = compDatasets;
                comparisonChartInstance.update();
            }
        }

        function setTimeRange(range) {
            currentTimeRange = range;
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll(`.time-goe-${range}, .time-comp-${range}`).forEach(b => b.classList.add('active'));
            loadDetailedHistory();
        }

        async function loadDetailedHistory() {
            try {
                let limit = 5000;
                if (currentTimeRange === '15m') limit = 60;
                else if (currentTimeRange === '30m') limit = 120;
                else if (currentTimeRange === '1h') limit = 240;
                else if (currentTimeRange === '2h') limit = 480;

                const resp = await fetch(`/api/detailed-history?limit=${limit}`);
                detailedHistory = await resp.json();

                const count = detailedHistory.length;
                let rangeLabel = 'Brak historii';
                if (count > 0) {
                    const firstTime = detailedHistory[0].timestamp.split(' ')[1] || detailedHistory[0].timestamp;
                    const lastTime = detailedHistory[count - 1].timestamp.split(' ')[1] || detailedHistory[count - 1].timestamp;
                    rangeLabel = `${count} pomiarów (${firstTime} — ${lastTime})`;
                }

                const goeSub = document.getElementById('goe-chart-sub-label');
                if (goeSub) goeSub.innerText = `YouTube & Twitch • ${rangeLabel}`;
                const compSub = document.getElementById('comp-chart-sub-label');
                if (compSub) compSub.innerText = `GoE vs Nervarien • ${rangeLabel}`;

                updateChartSeries();
            } catch (e) {
                console.error("Detailed history error:", e);
            }
        }

        async function loadMomentum() {
            try {
                const resp = await fetch('/api/momentum');
                const m = await resp.json();
                const renderDelta = (elId, delta) => {
                    const el = document.getElementById(elId);
                    if (!el) return;
                    if (delta > 0) {
                        el.innerText = `▲ +${delta.toLocaleString('pl-PL')} w ${m.minutes} min`;
                        el.className = 'momentum-badge momentum-up';
                    } else if (delta < 0) {
                        el.innerText = `▼ ${delta.toLocaleString('pl-PL')} w ${m.minutes} min`;
                        el.className = 'momentum-badge momentum-down';
                    } else {
                        el.innerText = `— 0 w ${m.minutes} min`;
                        el.className = 'momentum-badge';
                    }
                };
                renderDelta('goe-hero-momentum', m.goe_delta);
                renderDelta('battle-goe-momentum', m.goe_delta);
                renderDelta('battle-nerva-momentum', m.nerva_delta);
            } catch (e) {
                console.error("Momentum error:", e);
            }
        }

        async function loadData(manual = false) {
            try {
                const resp = await fetch('/api/data');
                rawData = await resp.json();

                document.getElementById('last-updated').innerText = `Ostatni pomiar: ${rawData.timestamp} • Stan bazy: ${detailedHistory.length} próbek`;

                renderFilterChips();
                updateUI();
                await loadMomentum();
                await loadDetailedHistory();

                if (manual) showToast('Zaktualizowano dane!');
            } catch (err) {
                console.error(err);
            }
        }

        function setupAutoRefresh() {
            if (autoInterval) clearInterval(autoInterval);
            const seconds = parseInt(document.getElementById('auto-refresh-select').value);
            if (seconds > 0) {
                autoInterval = setInterval(() => loadData(false), seconds * 1000);
            }
        }

        function downloadLiveCard() {
            window.open('/api/card', '_blank');
        }

        function downloadSummaryCard(mode = 'goe') {
            window.open(`/api/summary-card?mode=${mode}`, '_blank');
        }

        function downloadCSV() {
            window.open('/api/export-csv', '_blank');
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2000);
        }

        window.onload = async () => {
            initCharts();
            await loadData();
            setupAutoRefresh();
        };
    </script>
</body>
</html>
"""


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
                content = HTML_TEMPLATE.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)

        elif path == "/api/data":
            data = fetch_all_data()
            save_snapshot(data)
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
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        return


def background_collector_loop():
    """Background thread collecting data every 15 seconds while streams are live,
    stopping only after 30 consecutive minutes of all streams being offline."""
    print(f"[Collector] Uruchomiono inteligentne zbieranie danych co {POLL_INTERVAL}s.")
    print(
        "[Collector] Monitorowanie aktywne dopóki trwają transmisje (zakończenie po 30 min ciągłego braku sygnału)."
    )

    card_path = os.path.join(os.path.dirname(__file__), "battle_card.png")
    goe_summary_path = os.path.join(os.path.dirname(__file__), "goe_summary.png")
    comparison_summary_path = os.path.join(
        os.path.dirname(__file__), "stream_summary.png"
    )

    consecutive_offline_seconds = 0
    had_live_stream = False

    while True:
        try:
            data = fetch_all_data()
            any_live = any(
                s.get("is_live", False)
                for s in data["groups"]["GOE"]["streams"]
                + data["groups"]["NERVA"]["streams"]
            )

            if any_live:
                had_live_stream = True
                consecutive_offline_seconds = 0
                save_snapshot(data)
                create_battle_card(data, card_path)
                create_summary_card(goe_summary_path, mode="GOE", filter_bots=True)
                create_summary_card(
                    comparison_summary_path, mode="COMPARISON", filter_bots=True
                )
                ts = datetime.now().strftime("%H:%M:%S")
                goe_v = data["groups"]["GOE"]["total_viewers"]
                nerva_v = data["groups"]["NERVA"]["total_viewers"]
                print(
                    f"[{ts}] Zapisano: GOE={goe_v:,} | NERVA={nerva_v:,}".replace(
                        ",", " "
                    )
                )
            else:
                consecutive_offline_seconds += POLL_INTERVAL
                offline_mins = consecutive_offline_seconds // 60
                ts = datetime.now().strftime("%H:%M:%S")
                if consecutive_offline_seconds % 60 == 0:
                    print(
                        f"[{ts}] Wszystkie streamy offline ({offline_mins}/30 min)..."
                    )

                if (
                    had_live_stream
                    and consecutive_offline_seconds >= OFFLINE_TIMEOUT_SECONDS
                ):
                    print(
                        f"[{ts}] Wszystkie transmisje zakończone (30 min offline). Generowanie ostatecznych podsumowań..."
                    )
                    create_summary_card(goe_summary_path, mode="GOE", filter_bots=True)
                    create_summary_card(
                        comparison_summary_path,
                        mode="COMPARISON",
                        filter_bots=True,
                    )
                    print(
                        "[Collector] Podsumowania zapisane. Przejście w tryb czuwania."
                    )
                    break
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
