"""Stream Scraper for Twitch and YouTube (zero API keys required)."""

import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from config import (
    COSTREAM_STREAMS,
    TWITCH_PUBLIC_CLIENT_ID,
    USER_AGENT,
    get_groups_config,
)


def fetch_twitch_batch(channel_logins: list[str]) -> dict[str, dict]:
    """Fetches live stream stats and avatars for multiple Twitch channels in a single GQL request."""
    if not channel_logins:
        return {}

    gql_query = [
        {
            "query": (
                f'query {{ user(login: "{ch}") {{ displayName login profileImageURL(width: 150) '
                "stream { viewersCount title game { name } } } }"
            )
        }
        for ch in channel_logins
    ]

    req = urllib.request.Request(
        "https://gql.twitch.tv/gql",
        data=json.dumps(gql_query).encode("utf-8"),
        headers={
            "Client-ID": TWITCH_PUBLIC_CLIENT_ID,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )

    results = {}
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                u = item.get("data", {}).get("user")
                if not u:
                    continue
                login = u.get("login", "").lower()
                stream = u.get("stream")
                results[login] = {
                    "id": login,
                    "platform": "Twitch",
                    "channel": u.get("displayName") or login,
                    "title": stream.get("title", "") if stream else "Stream offline",
                    "category": stream.get("game", {}).get("name", "")
                    if stream and stream.get("game")
                    else "",
                    "is_live": stream is not None,
                    "viewers": stream.get("viewersCount", 0) if stream else 0,
                    "url": f"https://www.twitch.tv/{login}",
                    "avatar_url": u.get("profileImageURL", ""),
                }
    except Exception as e:
        for ch in channel_logins:
            results[ch.lower()] = {
                "id": ch,
                "platform": "Twitch",
                "channel": ch,
                "title": f"Błąd pobierania: {e}",
                "category": "",
                "is_live": False,
                "viewers": 0,
                "url": f"https://www.twitch.tv/{ch}",
                "avatar_url": "",
            }
    return results


def fetch_youtube_stream(video_id: str) -> dict:
    """Fetches viewer count, avatar, and metadata for a YouTube stream by video ID."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

            # Extract title
            title_m = re.search(r"<title>(.*?)</title>", html)
            raw_title = title_m.group(1) if title_m else "YouTube Stream"
            title = raw_title.replace(" - YouTube", "").strip()

            # Channel / Author name
            channel_m = re.search(r'"ownerChannelName":"([^"]+)"', html)
            channel = channel_m.group(1) if channel_m else "YouTube"

            # Avatar URL
            avatar_m = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', html)
            if not avatar_m:
                avatar_m = re.search(
                    r'"channelThumbnail":\{"thumbnails":\[\{"url":"([^"]+)"',
                    html,
                )
            avatar_url = avatar_m.group(1) if avatar_m else ""

            # Check if live
            is_live_now = '"isLiveNow":true' in html or '"isLive":true' in html
            is_ended = '"isLiveNow":false' in html or '"endTimestamp"' in html
            is_live = is_live_now and not is_ended

            # Extract concurrent viewers ONLY if the stream is currently live
            # (Ended streams display cumulative VOD views which must NEVER be counted as live viewers)
            viewers = 0
            if is_live:
                vc_m = re.search(
                    r'"videoViewCountRenderer":\{.*?"originalViewCount":"(\d+)"',
                    html,
                )
                if not vc_m:
                    vc_m = re.search(r'"originalViewCount":"(\d+)"', html)

                if vc_m:
                    viewers = int(vc_m.group(1))
                else:
                    simple_m = re.search(
                        r'"runs":\[\{"text":"([\d\s,\.]+)"\},\{"text":"\s*(?:osób ogląda|watching now|viewers)"',
                        html,
                        re.IGNORECASE,
                    )
                    if simple_m:
                        cleaned = re.sub(r"[^\d]", "", simple_m.group(1))
                        if cleaned:
                            viewers = int(cleaned)

            return {
                "id": video_id,
                "platform": "YouTube",
                "channel": channel,
                "title": title,
                "category": "YouTube Live",
                "is_live": is_live,
                "viewers": viewers,
                "url": url,
                "avatar_url": avatar_url,
            }
    except Exception as e:
        return {
            "id": video_id,
            "platform": "YouTube",
            "channel": f"YT ({video_id})",
            "title": f"Błąd pobierania: {e}",
            "category": "YouTube Live",
            "is_live": False,
            "viewers": 0,
            "url": url,
            "avatar_url": "",
        }


def fetch_youtube_channel_live(handle: str) -> dict:
    """Observes a YouTube channel (@handle) and automatically detects its live or upcoming stream.

    If live: extracts videoId and fetches live viewers, title, and metadata.
    If not live: returns channel information with offline status, waiting for stream to begin.
    """
    clean_handle = handle.strip()
    if "youtube.com/" in clean_handle:
        m = re.search(r"youtube\.com/(@[a-zA-Z0-9_.-]+)", clean_handle)
        if m:
            clean_handle = m.group(1)

    if not clean_handle.startswith("@"):
        clean_handle = "@" + clean_handle.lstrip("/")

    url_live = f"https://www.youtube.com/{clean_handle}/live"
    req = urllib.request.Request(
        url_live,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )

    avatar_url = (
        "https://yt3.googleusercontent.com/sqtxooaGNUgRKzuOdpCvXL-sm9E-ahsMtdLwml6bgxBRMm7HwlEnDf8oYv90RX1IYiQLrFRz=s900-c-k-c0x00ffffff-no-rj"
        if "gadaja" in clean_handle.lower()
        else ""
    )
    channel_name = "Gadają o Esporcie" if "gadaja" in clean_handle.lower() else clean_handle

    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            final_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="ignore")

            # Extract avatar if present in HTML
            av_m = re.search(r'"avatar":\{"thumbnails":\[\{"url":"(https://[^"]+)"', html)
            if not av_m:
                av_m = re.search(r'<meta property="og:image" content="(https://[^"]+)">', html)
            if av_m:
                avatar_url = av_m.group(1)

            ch_m = re.search(r'"ownerChannelName":"([^"]+)"', html)
            if not ch_m:
                ch_m = re.search(r'"channelMetadataRenderer":\{.*?"title":"([^"]+)"', html)
            if ch_m:
                channel_name = ch_m.group(1)

            # Check if redirected to a watch?v= URL or canonical/og:url exists
            vid_m = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", final_url)
            if not vid_m:
                vid_m = re.search(
                    r'<meta property="og:url" content="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">',
                    html,
                )
            if not vid_m:
                vid_m = re.search(
                    r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">',
                    html,
                )

            is_live_now = '"isLiveNow":true' in html or '"isLive":true' in html
            is_ended = '"isLiveNow":false' in html or '"endTimestamp"' in html

            if vid_m:
                vid = vid_m.group(1)
                stream_data = fetch_youtube_stream(vid)
                stream_data["id"] = clean_handle
                stream_data["video_id"] = vid
                if avatar_url and not stream_data.get("avatar_url"):
                    stream_data["avatar_url"] = avatar_url
                return stream_data

    except Exception as e:
        print(f"[YouTube Observer] Sprawdzanie {clean_handle}/live: {e}")

    return {
        "id": clean_handle,
        "platform": "YouTube",
        "channel": channel_name,
        "title": "Stream offline (oczekiwanie na start transmisji...)",
        "category": "YouTube Live",
        "is_live": False,
        "viewers": 0,
        "url": url_live,
        "avatar_url": avatar_url,
    }


def fetch_all_data(
    groups_config: dict | None = None, day_id: str | None = None
) -> dict:
    """Fetches all streams concurrently and returns grouped comparison data."""
    if groups_config is None:
        groups_config = get_groups_config(day_id)

    all_twitch_channels = []
    all_yt_ids = []

    for group_data in groups_config.values():
        all_twitch_channels.extend(group_data.get("twitch", []))
        all_yt_ids.extend(group_data.get("youtube", []))

    twitch_results = {}
    yt_results = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        twitch_future = executor.submit(fetch_twitch_batch, all_twitch_channels)
        yt_futures = {}
        for item in all_yt_ids:
            if item.startswith("@") or "youtube.com/" in item:
                yt_futures[executor.submit(fetch_youtube_channel_live, item)] = item
            else:
                yt_futures[executor.submit(fetch_youtube_stream, item)] = item

        twitch_results = twitch_future.result()
        for fut, vid in yt_futures.items():
            yt_results[vid] = fut.result()

    grouped = {}
    total_all_viewers = 0

    for grp_key, grp_info in groups_config.items():
        streams = []
        group_total = 0

        # Twitch streams
        for ch in grp_info.get("twitch", []):
            st = twitch_results.get(ch.lower(), {})
            if st:
                st_item = dict(st)
                st_item["group"] = grp_key
                is_costream = (
                    ch.lower() in COSTREAM_STREAMS
                    or st_item.get("id") in COSTREAM_STREAMS
                )
                if is_costream:
                    costream_info = COSTREAM_STREAMS.get(
                        ch.lower(), COSTREAM_STREAMS.get(st_item.get("id"), {})
                    )
                    st_item["channel"] = costream_info.get(
                        "name", st_item.get("channel", "Tobiasz")
                    )
                    if grp_key != "TOBIASZ":
                        st_item["is_costream"] = True
                        st_item["is_curiosity"] = True  # Backward-compatible
                streams.append(st_item)
                # Co-streams under NERVA are excluded from the official head-to-head duel sum
                # For TOBIASZ, ttobias_lol is the main stream of the camp
                if st.get("is_live", False):
                    if grp_key == "TOBIASZ" or not is_costream:
                        group_total += st.get("viewers", 0)

        # YouTube streams
        for vid in grp_info.get("youtube", []):
            st = yt_results.get(vid, {})
            if st:
                st_item = dict(st)
                st_item["group"] = grp_key
                is_costream = vid in COSTREAM_STREAMS
                if is_costream:
                    st_item["channel"] = COSTREAM_STREAMS[vid].get(
                        "name", "Nerva Co-stream"
                    )
                    st_item["is_costream"] = True
                    st_item["is_curiosity"] = True  # Backward-compatible
                streams.append(st_item)
                # Co-streams are excluded from the official head-to-head duel sum
                if st.get("is_live", False) and not is_costream:
                    group_total += st.get("viewers", 0)

        grouped[grp_key] = {
            "id": grp_key,
            "name": grp_info["name"],
            "color": grp_info["color"],
            "total_viewers": group_total,
            "streams": streams,
        }
        total_all_viewers += group_total

    goe_viewers = grouped.get("GOE", {}).get("total_viewers", 0)
    nerva_viewers = grouped.get("NERVA", {}).get("total_viewers", 0)

    if total_all_viewers > 0:
        ratio_goe = round((goe_viewers / total_all_viewers) * 100, 1)
        ratio_nerva = round((nerva_viewers / total_all_viewers) * 100, 1)
    else:
        ratio_goe = 50.0
        ratio_nerva = 50.0

    if goe_viewers > nerva_viewers:
        leader = "GOE"
        diff = goe_viewers - nerva_viewers
    elif nerva_viewers > goe_viewers:
        leader = "NERVA"
        diff = nerva_viewers - goe_viewers
    else:
        leader = "REMIS"
        diff = 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "timestamp": now_str,
        "total_viewers": total_all_viewers,
        "leader": leader,
        "diff": diff,
        "ratio_goe": ratio_goe,
        "ratio_nerva": ratio_nerva,
        "groups": grouped,
    }
