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
        "match": "TOP Esports vs Invictus Gaming",
        "match_short": "TES vs IG",
        "score": "1 : 3",
        "winner": "Invictus Gaming",
        "stage": "quarters",
        "date": "2026-11-03",
        "is_finished": True,
        "disclaimers": [
            "Atak viewbotów na YouTube (GoE) – dane oczyszczone filtrem adaptywnym (prawdziwy organiczny szczyt: 2 815).",
            "Brak transmisji Tobiasza (offline przez cały mecz).",
            "Błąd pomiarowy w co-streamie Nervariena (opóźnione wykrycie transmisji Damiana).",
            "Błędy w pobieraniu danych / timeouty YouTube API (dane wygładzone).",
        ],
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
                "color": "#ff0033",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": ["I2E60nEUXWo"],
            },
            "NERVA": {
                "name": "Nervarien & Co-streams",
                "color": "#3b82f6",  # Crimson Red
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
        "match": "Movistar Lyon vs Gen.G Esports",
        "match_short": "Lyon vs Gen.G",
        "score": "0 : 3",
        "winner": "Gen.G Esports",
        "stage": "quarters",
        "date": "2026-11-04",
        "is_finished": True,
        "disclaimers": [],
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
                "color": "#ff0033",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": ["dKZGkF2mIDU"],  # Ćwierćfinał Lyon vs Gen.G (04.11)
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",  # Crimson Red
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
        "match": "Bilibili Gaming vs Dplus KIA",
        "match_short": "BLG vs DK",
        "score": "3 : 0",
        "winner": "Bilibili Gaming",
        "stage": "quarters",
        "date": "2026-11-05",
        "is_finished": True,
        "disclaimers": [
            "Dane przycięte do zakończenia rywalizacji turniejowej (02:11 CET, zakończenie streamów GoE i Tobiasza).",
            "Wygładzono chwilowe błędy i timeouty pobierania YouTube.",
        ],
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
                "color": "#ff0033",
                "twitch": ["goe_stream"],
                "youtube": ["jcO4IHpR7XE"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",
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
        "match": "Karmine Corp vs T1",
        "match_short": "KC vs T1",
        "score": "1 : 3",
        "winner": "T1",
        "stage": "quarters",
        "date": "2026-11-06",
        "is_finished": True,
        "disclaimers": [
            "Błędy w pobieraniu danych / timeouty YouTube API (dane wygładzone).",
        ],
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
                "color": "#ff0033",
                "twitch": ["goe_stream"],
                "youtube": ["Zv_21UIAKAc"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",
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
        "match": "Gen.G Esports vs Invictus Gaming",
        "match_short": "Gen.G vs IG",
        "score": "3 : 0",
        "winner": "Gen.G Esports",
        "stage": "semis",
        "date": "2026-11-07",
        "is_finished": True,
        "disclaimers": [
            "Wygładzono dip z 23:40 (restart co-streamu Nervariena) oraz zacięcie o 01:00.",
        ],
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
                "color": "#ff0033",
                "twitch": ["goe_stream"],
                "youtube": ["_PfE0hBYM-o"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",
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
        "match": "Bilibili Gaming vs T1",
        "match_short": "BLG vs T1",
        "score": "3 : 1",
        "winner": "Bilibili Gaming",
        "stage": "semis",
        "date": "2026-11-08",
        "is_finished": True,
        "disclaimers": [
            "Rekordowy szczyt jednoczesnej widowni 3 obozów: 17 596 widzów.",
        ],
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
                "color": "#ff0033",
                "twitch": ["goe_stream"],
                "youtube": ["p7f_l6Volf8"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",
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
    "day-7": {
        "id": "day-7",
        "name": "Finał (14.11)",
        "label": "Finał • 14.11 (Na Żywo)",
        "match": "Bilibili Gaming vs Gen.G Esports",
        "match_short": "BLG vs Gen.G",
        "score": "",
        "winner": "",
        "stage": "finals",
        "date": "2026-11-14",
        "is_finished": False,
        "disclaimers": [
            "Ceremonia Otwarcia i start Wielkiego Finału w Barclays Center (Nowy Jork): 20:00 CET (19:00 UTC).",
            "Start studia GoE: 17:30 CET (transmisja live od 17:50), Nervarien: ~19:30 CET.",
        ],
        "start_utc": "2026-11-14 12:00:00",
        "end_utc": "2026-11-15 12:00:00",
        "schedule": {
            "goe_start": "17:30",
            "nerva_start": "19:30",
            "match_start": "20:00",
            "goe_start_iso": "2026-11-14T17:30:00+01:00",
            "match_start_iso": "2026-11-14T20:00:00+01:00",
            "venue": "Barclays Center, Nowy Jork",
        },
        "groups": {
            "GOE": {
                "name": "Gadają o Esporcie (GOE)",
                "color": "#ff0033",  # Neon Blue
                "twitch": ["goe_stream"],
                "youtube": ["@gadaja_"],
            },
            "NERVA": {
                "name": "Nervarien",
                "color": "#3b82f6",  # Crimson Red
                "twitch": ["nervarien"],
                "youtube": ["@nervarien"],
            },
            "TOBIASZ": {
                "name": "Tobiasz",
                "color": "#f97316",  # Vibrant Orange
                "twitch": ["ttobias_lol"],
                "youtube": [],
            },
        },
        "costream_streams": [],
        "curiosity_streams": [],
        "events": [
            {"time": "17:50", "label": "Start Bunkra"},
            {"time": "20:00", "label": "Ceremonia Otwarcia"},
        ],
    },
}

# Tournament Stages Configuration (Quarters, Semis, Finals, Overall)
STAGES_CONFIG = {
    "quarters": {
        "id": "quarters",
        "name": "Ćwierćfinały (Dni 1–4)",
        "short_name": "Ćwierćfinały",
        "days": ["day-1", "day-2", "day-3", "day-4"],
        "icon": "🥊",
        "subtitle": "4 mecze BO5 • 8 czołowych drużyn świata",
    },
    "semis": {
        "id": "semis",
        "name": "Półfinały (Dni 5–6)",
        "short_name": "Półfinały",
        "days": ["day-5", "day-6"],
        "icon": "🔥",
        "subtitle": "2 mecze BO5 • Walka o Wielki Finał",
    },
    "finals": {
        "id": "finals",
        "name": "Wielki Finał (Dzień 7)",
        "short_name": "Wielki Finał",
        "days": ["day-7"],
        "icon": "👑",
        "subtitle": "Bilibili Gaming vs Gen.G Esports • Mecz o Puchar Przywoływacza",
    },
    "tournament": {
        "id": "tournament",
        "name": "Cały Turniej (Dni 1–7)",
        "short_name": "Cały Turniej",
        "days": ["day-1", "day-2", "day-3", "day-4", "day-5", "day-6", "day-7"],
        "icon": "🏆",
        "subtitle": "Pełne podsumowanie fazy pucharowej Worlds 2026",
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
    - 2026-11-08 12:00 to 2026-11-09 12:00 UTC -> 'day-6'
    - From 2026-11-09 12:00 UTC onwards -> 'day-7' (Grand Final)
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
    d7 = datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)

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
    elif now_utc < d7:
        return "day-6"
    else:
        return "day-7"


def get_known_stream_ids() -> dict[str, set[str]]:
    """Collects known stream IDs grouped by camp and platform across all days."""
    ids: dict[str, set[str]] = {
        "goe_yt": {"@gadaja_"},
        "goe_tw": {"goe_stream"},
        "nerva_yt": {"@nervarien"},
        "nerva_tw": {"nervarien"},
        "nerva_costream": {
            cid
            for cid, info in COSTREAM_STREAMS.items()
            if info.get("group") == "NERVA"
        },
        "tobias_tw": {"ttobias_lol"},
    }
    for dcfg in DAYS_CONFIG.values():
        costreams = set(dcfg.get("costream_streams", [])) | set(
            dcfg.get("curiosity_streams", [])
        )
        ids["nerva_costream"].update(costreams)
        groups = dcfg.get("groups", {})
        for yt_id in groups.get("GOE", {}).get("youtube", []):
            ids["goe_yt"].add(yt_id)
        for tw_id in groups.get("GOE", {}).get("twitch", []):
            ids["goe_tw"].add(tw_id)
        for yt_id in groups.get("NERVA", {}).get("youtube", []):
            if yt_id not in ids["nerva_costream"]:
                ids["nerva_yt"].add(yt_id)
        for tw_id in groups.get("NERVA", {}).get("twitch", []):
            ids["nerva_tw"].add(tw_id)
        for tw_id in groups.get("TOBIASZ", {}).get("twitch", []):
            ids["tobias_tw"].add(tw_id)
    return ids


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
