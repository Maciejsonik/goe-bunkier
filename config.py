"""Configuration for the Stream Battle Scraper with Multi-Day Support."""

import os
from datetime import UTC, datetime

# Multi-day configuration for Worlds 2026
# Day 1: Nov 3 12:00 UTC to Nov 4 12:00 UTC
# Day 2: Nov 4 12:00 UTC to Nov 5 12:00 UTC
DAYS_CONFIG = {
    "day-1": {
        "id": "day-1",
        "name": "Dzień 1 (03.11)",
        "label": "Dzień 1 • 03.11 (Zakończony)",
        "date": "2026-11-03",
        "is_finished": True,
        "start_utc": "2026-11-03 12:00:00",
        "end_utc": "2026-11-04 12:00:00",
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": ["I2E60nEUXWo"],
            },
            "NERVA": {
                "name": "Nervarien & Co-streams",
                "color": "#ef4444",  # Crimson Red
                "twitch": ["nervarien"],
                "youtube": ["SGAaZFSc3Zk", "woX6jXefVdw"],
            },
        },
        "costream_streams": ["woX6jXefVdw"],
        "curiosity_streams": ["woX6jXefVdw"],
    },
    "day-2": {
        "id": "day-2",
        "name": "Dzień 2 (04.11)",
        "label": "Dzień 2 • 04.11 (Dzisiejszy)",
        "date": "2026-11-04",
        "is_finished": False,
        "start_utc": "2026-11-04 12:00:00",
        "end_utc": "2026-11-05 12:00:00",
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": [],  # GoE YouTube link will be added here once announced
            },
            "NERVA": {
                "name": "Nervarien & Co-streams",
                "color": "#ef4444",  # Crimson Red
                "twitch": ["nervarien", "ttobias_lol"],
                "youtube": ["00uONX5EBiA", "N3i_DQlKL_U"],
            },
        },
        "costream_streams": ["N3i_DQlKL_U", "ttobias_lol"],
        "curiosity_streams": ["N3i_DQlKL_U", "ttobias_lol"],
    },
}

# Co-stream channels mapped across all days
# Tracked on the dashboard but excluded from official duel sums
COSTREAM_STREAMS = {
    "woX6jXefVdw": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "N3i_DQlKL_U": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "ttobias_lol": {
        "name": "Tobiasz Co-stream",
        "group": "NERVA",
        "platform": "Twitch",
    },
}
CURIOSITY_STREAMS = COSTREAM_STREAMS


def get_active_day_id(now_utc: datetime | None = None) -> str:
    """Returns active day id based on the 12:00 UTC rollover rule:
    - Before 2026-11-04 12:00:00 UTC -> 'day-1'
    - From 2026-11-04 12:00:00 UTC onwards -> 'day-2'
    Can be manually overridden with STREAM_DAY environment variable.
    """
    override = os.environ.get("STREAM_DAY")
    if override and override in DAYS_CONFIG:
        return override

    if now_utc is None:
        now_utc = datetime.now(UTC)

    day2_cutoff = datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC)
    if now_utc < day2_cutoff:
        return "day-1"
    return "day-2"


def get_groups_config(day_id: str | None = None) -> dict:
    """Returns groups configuration dictionary for a given day id."""
    if day_id is None:
        day_id = get_active_day_id()
    day_entry = DAYS_CONFIG.get(day_id, DAYS_CONFIG["day-1"])
    return day_entry["groups"]
    if day_id is None:
        day_id = get_active_day_id()
    day_entry = DAYS_CONFIG.get(day_id, DAYS_CONFIG["day-1"])
    return day_entry["groups"]


# Backward-compatible global GROUPS
GROUPS = get_groups_config()

# HTTP User agent for YouTube requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Twitch public web client ID (no private secret needed)
TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
