"""Configuration for the Stream Battle Scraper."""

# Channels and video streams divided into two competing groups
GROUPS = {
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
}

# HTTP User agent for YouTube requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Twitch public web client ID (no private secret needed)
TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
