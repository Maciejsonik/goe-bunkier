"""Stream Scraper for Twitch and YouTube (zero API keys required)."""

import json
import os
import re
import threading
import time
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

# Disk + in-memory cache of last successful live stream data to prevent 0-viewer drops on temporary network glitches / HTTP 429
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "last_live.json")
_CACHE_LOCK = threading.Lock()
_STREAM_CACHE: dict[str, dict] = {}


def _load_disk_cache() -> None:
    """Loads persisted live stream cache from disk once."""
    if not os.path.exists(_CACHE_FILE):
        return
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            now_t = time.time()
            with _CACHE_LOCK:
                for k, v in data.items():
                    if isinstance(v, dict) and (now_t - v.get("timestamp", 0)) < 600:
                        _STREAM_CACHE[k] = v
    except Exception:
        pass


def _update_cache(key: str, st_obj: dict) -> None:
    """Updates in-memory and disk cache with a fresh live stream snapshot."""
    with _CACHE_LOCK:
        _STREAM_CACHE[key] = {
            "data": dict(st_obj),
            "timestamp": time.time(),
        }
        try:
            os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
            tmp_path = _CACHE_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(_STREAM_CACHE, f, ensure_ascii=False)
            os.replace(tmp_path, _CACHE_FILE)
        except Exception:
            pass


def _get_cached_fallback(key: str, max_age_sec: int = 360) -> dict | None:
    """Returns cached live stream data if recent enough."""
    with _CACHE_LOCK:
        entry = _STREAM_CACHE.get(key)
        if entry and (time.time() - entry.get("timestamp", 0)) < max_age_sec:
            return dict(entry["data"])
    return None


def _urlopen_with_retry(
    req: urllib.request.Request,
    timeout: float = 6.0,
    retries: int = 2,
    delay: float = 0.7,
) -> tuple[str, str]:
    """Executes an HTTP request with retry and backoff; returns (final_url, body_str)."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                final_url = resp.geturl()
                body = resp.read().decode("utf-8", errors="ignore")
                return final_url, body
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(delay * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
                continue
            raise
    raise last_err


_load_disk_cache()


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
        _, raw_body = _urlopen_with_retry(req, timeout=6.0, retries=2, delay=0.6)
        data = json.loads(raw_body)
        for item in data:
            u = item.get("data", {}).get("user")
            if not u:
                continue
            login = u.get("login", "").lower()
            stream = u.get("stream")
            st_obj = {
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
            results[login] = st_obj
            if stream is not None:
                _update_cache(login, st_obj)
    except Exception as e:
        for ch in channel_logins:
            k = ch.lower()
            cached = _get_cached_fallback(k, max_age_sec=360)
            if cached:
                results[k] = cached
                continue
            results[k] = {
                "id": ch,
                "platform": "Twitch",
                "channel": ch,
                "title": f"Błąd pobierania: {e}",
                "category": "",
                "is_live": False,
                "viewers": 0,
                "fetch_error": True,
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
        _, html = _urlopen_with_retry(req, timeout=6.0, retries=2, delay=0.7)

        # Extract title
        title_m = re.search(r"<title>(.*?)</title>", html)
        raw_title = title_m.group(1) if title_m else ""
        title = raw_title.replace(" - YouTube", "").strip()

        if not title or title in ("YouTube", "YouTube Stream"):
            m_vp = re.search(
                r'videoPrimaryInfoRenderer":\{"title":\{"runs":\[\{"text":"(.*?)"\}\]',
                html,
            )
            if m_vp:
                title = m_vp.group(1)

        # Channel / Author name
        channel_m = re.search(r'"ownerChannelName":"([^"]+)"', html)
        if not channel_m:
            channel_m = re.search(r'"videoOwnerRenderer":\{.*?"text":"([^"]+)"', html)
        if not channel_m:
            channel_m = re.search(
                r'"channelMetadataRenderer":\{.*?"title":"([^"]+)"', html
            )
        channel = (
            channel_m.group(1)
            if channel_m
            else ("Gadają o Esporcie" if "gadaja" in html.lower() else "YouTube")
        )

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

        st_obj = {
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
        if is_live:
            _update_cache(video_id, st_obj)
        return st_obj
    except Exception as e:
        cached = _get_cached_fallback(video_id, max_age_sec=360)
        if cached:
            print(
                f"[YouTube Fallback] {video_id} błąd ({e}), zachowuję ostatni stan: {cached.get('viewers', 0)} widzów"
            )
            return cached

        return {
            "id": video_id,
            "platform": "YouTube",
            "channel": f"YT ({video_id})",
            "title": f"Błąd pobierania: {e}",
            "category": "YouTube Live",
            "is_live": False,
            "viewers": 0,
            "fetch_error": True,
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
    channel_name = (
        "Gadają o Esporcie" if "gadaja" in clean_handle.lower() else clean_handle
    )

    had_error = False
    try:
        final_url, html = _urlopen_with_retry(req, timeout=7.0, retries=2, delay=0.7)

        # Extract avatar if present in HTML
        av_m = re.search(r'"avatar":\{"thumbnails":\[\{"url":"(https://[^"]+)"', html)
        if not av_m:
            av_m = re.search(
                r'<meta property="og:image" content="(https://[^"]+)">', html
            )
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

        # Fallback: inspect channel's /streams tab to find the latest broadcast
        if not vid_m:
            try:
                url_streams = f"https://www.youtube.com/{clean_handle}/streams"
                req_s = urllib.request.Request(
                    url_streams,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
                    },
                )
                _, html_s = _urlopen_with_retry(
                    req_s, timeout=6.0, retries=1, delay=0.5
                )
                m_init = re.search(r"var ytInitialData = ({.*?});</script>", html_s)
                if m_init:
                    try:
                        d_init = json.loads(m_init.group(1))

                        def find_first_content_id(obj):
                            if isinstance(obj, dict):
                                if (
                                    "lockupViewModel" in obj
                                    and "contentId" in obj["lockupViewModel"]
                                ):
                                    return obj["lockupViewModel"]["contentId"]
                                for v in obj.values():
                                    res = find_first_content_id(v)
                                    if res:
                                        return res
                            elif isinstance(obj, list):
                                for item in obj:
                                    res = find_first_content_id(item)
                                    if res:
                                        return res
                            return None

                        stream_vid = find_first_content_id(d_init)
                        if stream_vid:
                            vid_m = re.match(r"^([a-zA-Z0-9_-]{11})$", stream_vid)
                    except Exception:
                        pass
                if not vid_m:
                    vid_m = re.search(r'"contentId":"([a-zA-Z0-9_-]{11})"', html_s)
            except Exception as ex_s:
                print(
                    f"[YouTube Observer] Fallback /streams for {clean_handle}: {ex_s}"
                )

        if vid_m:
            vid = vid_m.group(1)
            stream_data = fetch_youtube_stream(vid)
            stream_data["id"] = clean_handle
            stream_data["video_id"] = vid
            stream_data["direct_watch_url"] = f"https://www.youtube.com/watch?v={vid}"
            if stream_data.get("is_live"):
                stream_data["url"] = f"https://www.youtube.com/watch?v={vid}"
                if avatar_url and not stream_data.get("avatar_url"):
                    stream_data["avatar_url"] = avatar_url
                _update_cache(clean_handle, stream_data)
                return stream_data
            elif stream_data.get("fetch_error"):
                had_error = True
            else:
                # Stream explicitly not live: always present clean offline waiting message
                stream_data["title"] = (
                    "Stream offline (oczekiwanie na start transmisji...)"
                )
                if avatar_url and not stream_data.get("avatar_url"):
                    stream_data["avatar_url"] = avatar_url
                return stream_data

    except Exception as e:
        had_error = True
        print(f"[YouTube Observer] Sprawdzanie {clean_handle}/live: {e}")

    if had_error:
        cached = _get_cached_fallback(clean_handle, max_age_sec=360)
        if cached:
            print(
                f"[YouTube Observer Fallback] {clean_handle} błąd, zachowuję ostatni stan: {cached.get('viewers', 0)} widzów"
            )
            return cached

    return {
        "id": clean_handle,
        "platform": "YouTube",
        "channel": channel_name,
        "title": "Stream offline (oczekiwanie na start transmisji...)",
        "category": "YouTube Live",
        "is_live": False,
        "viewers": 0,
        "fetch_error": had_error,
        "url": url_live,
        "avatar_url": avatar_url,
    }


_LAST_DISCOVERY = {}
_DISCOVERED_VIDS = {}


def check_channel_live_streams(handle: str, force: bool = False) -> list[str]:
    """Auto-discovers all currently live stream video IDs on a YouTube channel's /streams page."""
    now = time.time()
    if not force and handle in _LAST_DISCOVERY and (now - _LAST_DISCOVERY[handle]) < 45:
        return _DISCOVERED_VIDS.get(handle, [])

    try:
        clean = handle.replace("https://www.youtube.com/", "").replace("/", "").strip()
        if not clean.startswith("@"):
            clean = f"@{clean}"
        url = f"https://www.youtube.com/{clean}/streams"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        _, html = _urlopen_with_retry(req, timeout=5.0, retries=1, delay=0.5)
        blocks = re.split(r"\"(?:videoRenderer|lockupViewModel)\":", html)
        live_ids = []
        for b in blocks[1:]:
            is_live = (
                '"imageName":"LIVE"' in b
                or '"BADGE_STYLE_TYPE_LIVE_NOW"' in b
                or '"THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE' in b
            )
            if is_live:
                vid_m = re.search(r"\"videoId\":\"([a-zA-Z0-9_-]{11})\"", b)
                if vid_m:
                    vid = vid_m.group(1)
                    if vid not in live_ids:
                        live_ids.append(vid)
        _LAST_DISCOVERY[handle] = now
        _DISCOVERED_VIDS[handle] = live_ids
        return live_ids
    except Exception as e:
        print(f"[Auto-Discovery] Błąd skanowania {handle}/streams: {e}")
        return _DISCOVERED_VIDS.get(handle, [])


def fetch_all_data(
    groups_config: dict | None = None, day_id: str | None = None
) -> dict:
    """Fetches all streams concurrently and returns grouped comparison data."""
    if groups_config is None:
        groups_config = get_groups_config(day_id)

    # Work on a shallow-cloned groups config so auto-discovery does not mutate global DAYS_CONFIG
    working_groups = {
        k: {
            **v,
            "twitch": list(v.get("twitch", [])),
            "youtube": list(v.get("youtube", [])),
        }
        for k, v in groups_config.items()
    }

    # Dynamic auto-discovery of live streams for GoE and Nervarien
    channel_handles = {"GOE": "@gadaja_", "NERVA": "@nervarien"}
    for grp_key, handle in channel_handles.items():
        if grp_key in working_groups:
            grp_yt = working_groups[grp_key]["youtube"]
            live_discovered = check_channel_live_streams(handle)
            for vid in live_discovered:
                if vid not in grp_yt:
                    print(
                        f"[{grp_key} Auto-Discovery] Wykryto nową transmisję na żywo: {vid}"
                    )
                    grp_yt.append(vid)

    all_twitch_channels = []
    all_yt_ids = []

    for group_data in working_groups.values():
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

    for grp_key, grp_info in working_groups.items():
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
        seen_yt_vids = set()
        for vid in grp_info.get("youtube", []):
            st = yt_results.get(vid, {})
            if st:
                actual_vid = st.get("video_id") or st.get("id")
                if actual_vid in seen_yt_vids:
                    continue
                seen_yt_vids.add(actual_vid)

                st_item = dict(st)
                st_item["group"] = grp_key
                title_upper = (st.get("title") or "").upper()
                is_costream = (
                    vid in COSTREAM_STREAMS
                    or actual_vid in COSTREAM_STREAMS
                    or (
                        grp_key == "NERVA"
                        and (
                            "NERVARIEN CO-STREAM" in title_upper
                            or ("CO-STREAM" in title_upper and vid != "@nervarien")
                        )
                    )
                )
                if is_costream:
                    if actual_vid and actual_vid not in COSTREAM_STREAMS:
                        COSTREAM_STREAMS[actual_vid] = {
                            "name": "Nerva Co-stream",
                            "group": "NERVA",
                            "platform": "YouTube",
                        }
                    costream_info = COSTREAM_STREAMS.get(
                        vid, COSTREAM_STREAMS.get(actual_vid, {})
                    )
                    st_item["channel"] = costream_info.get("name", "Nerva Co-stream")
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
