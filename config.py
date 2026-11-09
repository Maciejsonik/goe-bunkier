"""Configuration for the Stream Battle Scraper with Multi-Day Support."""

import os
from datetime import UTC, datetime

# Multi-day configuration for Worlds 2026 Quarter-Finals
# Day 1: Nov 3 12:00 UTC to Nov 4 12:00 UTC (Completed)
# Day 2: Nov 4 12:00 UTC to Nov 5 12:00 UTC (Completed)
# Day 3: Nov 5 12:00 UTC to Nov 6 12:00 UTC (Completed)
# Day 4: Nov 6 12:00 UTC to Nov 7 12:00 UTC (Completed)
# Day 5: Nov 7 12:00 UTC to Nov 8 12:00 UTC (Today - Start GoE: 20:30 CET)
# Day 6: Nov 8 12:00 UTC to Nov 9 12:00 UTC (Tomorrow - Start GoE: 21:30 CET, Match: 23:00 CET)
DAYS_CONFIG = {
    "day-1": {
        "id": "day-1",
        "name": "Dzień 1 (03.11)",
        "label": "Dzień 1 • 03.11 (Zakończony)",
        "date": "2026-11-03",
        "is_finished": True,
        "start_utc": "2026-11-03 12:00:00",
        "end_utc": "2026-11-04 12:00:00",
        "schedule": {
            "goe_start": "21:30",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-03T21:30:00+01:00",
        },
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
        "label": "Dzień 2 • 04.11 (Zakończony)",
        "date": "2026-11-04",
        "is_finished": True,
        "start_utc": "2026-11-04 12:00:00",
        "end_utc": "2026-11-05 12:00:00",
        "schedule": {
            "goe_start": "21:30",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-04T21:30:00+01:00",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": ["dKZGkF2mIDU"],  # Ćwierćfinał Lyon vs Gen.G (04.11)
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#ef4444",  # Crimson Red
                "twitch": ["nervarien"],
                "youtube": ["00uONX5EBiA", "N3i_DQlKL_U"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",  # Vibrant Orange
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": ["N3i_DQlKL_U"],
        "curiosity_streams": ["N3i_DQlKL_U"],
    },
    "day-3": {
        "id": "day-3",
        "name": "Dzień 3 (05.11)",
        "label": "Dzień 3 • 05.11 (Zakończony)",
        "date": "2026-11-05",
        "is_finished": True,
        "start_utc": "2026-11-05 12:00:00",
        "end_utc": "2026-11-06 12:00:00",
        "schedule": {
            "goe_start": "21:15",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-05T21:15:00+01:00",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",
                "twitch": ["goe_stream"],
                "youtube": ["jcO4IHpR7XE"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#ef4444",
                "twitch": ["nervarien"],
                "youtube": ["x3HI_AwFKEU"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": [],
        "curiosity_streams": [],
    },
    "day-4": {
        "id": "day-4",
        "name": "Dzień 4 (06.11)",
        "label": "Dzień 4 • 06.11 (Zakończony)",
        "date": "2026-11-06",
        "is_finished": True,
        "start_utc": "2026-11-06 12:00:00",
        "end_utc": "2026-11-07 12:00:00",
        "schedule": {
            "goe_start": "21:15",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-06T21:15:00+01:00",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",
                "twitch": ["goe_stream"],
                "youtube": ["Zv_21UIAKAc"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#ef4444",
                "twitch": ["nervarien"],
                "youtube": ["vxdgguSxRyE", "d97hINx-EHU"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": ["d97hINx-EHU"],
        "curiosity_streams": ["d97hINx-EHU"],
    },
    "day-5": {
        "id": "day-5",
        "name": "Dzień 5 (07.11)",
        "label": "Dzień 5 • 07.11 (Zakończony)",
        "date": "2026-11-07",
        "is_finished": True,
        "start_utc": "2026-11-07 12:00:00",
        "end_utc": "2026-11-08 12:00:00",
        "schedule": {
            "goe_start": "20:30",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-07T20:30:00+01:00",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",
                "twitch": ["goe_stream"],
                "youtube": ["_PfE0hBYM-o"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#ef4444",
                "twitch": ["nervarien"],
                "youtube": ["MqZfKdM3ZXI", "f4jsbC6bgNc", "aD1nB7lMtoY"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": ["f4jsbC6bgNc", "aD1nB7lMtoY"],
        "curiosity_streams": ["f4jsbC6bgNc", "aD1nB7lMtoY"],
    },
    "day-6": {
        "id": "day-6",
        "name": "Dzień 6 (08.11)",
        "label": "Dzień 6 • 08.11 (Zakończony)",
        "date": "2026-11-08",
        "is_finished": True,
        "start_utc": "2026-11-08 12:00:00",
        "end_utc": "2026-11-09 12:00:00",
        "schedule": {
            "goe_start": "21:30",
            "nerva_start": "22:30",
            "match_start": "23:00",
            "goe_start_iso": "2026-11-08T21:30:00+01:00",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#3b82f6",
                "twitch": ["goe_stream"],
                "youtube": ["p7f_l6Volf8"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#ef4444",
                "twitch": ["nervarien"],
                "youtube": ["JiL6EGqs-74"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": [],
        "curiosity_streams": [],
    },
}

# Co-stream channels mapped across all days
# Tracked on the dashboard but excluded from official duel sums
COSTREAM_STREAMS = {
    "woX6jXefVdw": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "N3i_DQlKL_U": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "d97hINx-EHU": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "f4jsbC6bgNc": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "aD1nB7lMtoY": {"name": "Nerva Co-stream", "group": "NERVA", "platform": "YouTube"},
    "ttobias_lol": {
        "name": "Tobiasz",
        "group": "TOBIASZ",
        "platform": "Twitch",
    },
}
CURIOSITY_STREAMS = COSTREAM_STREAMS


def get_active_day_id(now_utc: datetime | None = None) -> str:
    """Returns active day id based on the 12:00 UTC rollover rule:
    - Before 2026-11-04 12:00:00 UTC -> 'day-1'
    - 2026-11-04 12:00 to 2026-11-05 12:00 UTC -> 'day-2'
    - 2026-11-05 12:00 to 2026-11-06 12:00 UTC -> 'day-3'
    - 2026-11-06 12:00 to 2026-11-07 12:00 UTC -> 'day-4'
    - 2026-11-07 12:00 to 2026-11-08 12:00 UTC -> 'day-5'
    - From 2026-11-08 12:00 UTC onwards -> 'day-6'
    Can be manually overridden with STREAM_DAY environment variable.
    """
    override = os.environ.get("STREAM_DAY")
    if override and override in DAYS_CONFIG:
        return override

    if now_utc is None:
        now_utc = datetime.now(UTC)

    d2 = datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC)
    d3 = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)
    d4 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)
    d5 = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)
    d6 = datetime(2026, 11, 8, 12, 0, 0, tzinfo=UTC)

    if now_utc < d2:
        return "day-1"
    elif now_utc < d3:
        return "day-2"
    elif now_utc < d4:
        return "day-3"
    elif now_utc < d5:
        return "day-4"
    elif now_utc < d6:
        return "day-5"
    else:
        return "day-6"


def get_groups_config(day_id: str | None = None) -> dict:
    """Returns groups configuration dictionary for a given day id."""
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
