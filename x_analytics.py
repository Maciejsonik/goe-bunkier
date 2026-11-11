"""Analytics processor for #bunkier Twitter/X exports (Worlds 2026)."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os
import re
from zoneinfo import ZoneInfo

from config import DAYS_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WARSAW_TZ = ZoneInfo("Europe/Warsaw")

DEFAULT_START_DATE = "2026-10-31"
DEFAULT_END_DATE = "2026-11-11"

GOE_CREW_HANDLES = {
    "gadaja_",
    "czarnypiotrus10",
    "dejfdawid",
    "bialito_",
    "majutek_lol",
    "pedro_paprzycki",
    "magvayerlol",
    "jaskierbb",
}

RELATED_CREATOR_HANDLES = {
    "silv4nn",
    "rybson__",
    "cwillegendspl",
    "avahiresport",
    "mmalenstwoo",
    "maciejsonik_",
}

CONTEXT_KEYWORDS = (
    "bunkier",
    "bunkrze",
    "bunkra",
    "bunkrow",
    "hotbunkier",
    "bukier",
    "worlds",
    "gadają o esporcie",
    "gadaja o esporcie",
    "costream",
    "co-stream",
    "co stream",
    "preshow",
    "transmisj",
    "oglądalno",
    "ogladalno",
    "ćwierćfinał",
    "półfinał",
    "pickem",
    "tierlist",
    "texas tom",
    "philly pete",
    "puerto rico pedro",
    "michigan mike",
    "białej willi",
    "biała willa",
    "wiejskim stole",
    "caster",
    "predykcj",
    "dylan falco",
    "nervarien",
    "tobiasz",
    "flyquest",
    "gen.g",
    "invictus",
    "karmine",
    "dplus",
    "top esports",
    "faker",
    "chovy",
)

TOKEN_KEYWORDS_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:goe|lol|bo5|t1|blg|geng|hle|kt|tes|ig|kc|dk|lyon|fly|g2|al|lck|lpl|lec|mkoi|swiss|stream|strem|stumyk|finał|final|widzów|widzow)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

RELATED_OFFTOPIC_RE = re.compile(
    r"(?:riftbound|rcstuttgart|cyberpunk_tcg|timeoutpl|\bmouz\b)",
    re.IGNORECASE,
)

NOISE_TERMS = (
    "#urbanex",
    "urbex",
    "#schron",
    "#militaria",
    "#techno",
    "klub bunkier",
    "bunkier sztuki",
    "bunkier gdańsk",
    "bunkier gdansk",
    "bunkier rzeszów",
    "bunkier olsztyn",
    "bunkier pub",
    "wiatrówk",
    "nieruchomości",
)


def parse_x_count(raw: object) -> int:
    """Parses raw int or Polish/English X compact strings (e.g. '1,2 tys.', '14.5K')."""
    if isinstance(raw, (int, float)):
        return max(0, int(round(raw)))
    if not raw:
        return 0

    txt = str(raw).strip()
    m = re.search(
        r"(\d+(?:[., \u00a0\u202f]\d+)*)\s*(tys\.?|mln|mld|[kmbKMB])?",
        txt,
        re.IGNORECASE,
    )
    if not m:
        return 0

    num_part = m.group(1).strip()
    suffix = (m.group(2) or "").lower()
    if suffix:
        cleaned = re.sub(r"[\s\u00a0\u202f]+", "", num_part).replace(",", ".")
        try:
            val = float(cleaned)
        except ValueError:
            return 0
        if suffix.startswith("tys") or suffix == "k":
            return int(round(val * 1000))
        if suffix in ("mln", "m"):
            return int(round(val * 1_000_000))
        if suffix in ("mld", "b"):
            return int(round(val * 1_000_000_000))
        return int(round(val))

    digits = re.sub(r"[\s\u00a0\u202f.,]+", "", num_part)
    try:
        return int(digits)
    except ValueError:
        return 0


def parse_warsaw_timestamp(iso_str: str) -> datetime | None:
    """Converts an ISO UTC timestamp string into an Europe/Warsaw aware datetime."""
    if not iso_str:
        return None
    norm = iso_str.strip()
    if norm.endswith("Z"):
        norm = norm[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(norm)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=WARSAW_TZ)
    return dt.astimezone(WARSAW_TZ)


def normalize_raw_tweet(item: dict) -> dict | None:
    """Normalizes a raw scraped tweet dict into consistent typed metrics."""
    tid = str(item.get("tweet_id") or item.get("id") or "").strip()
    if not tid:
        return None
    return {
        "tweet_id": tid,
        "url": str(item.get("url", "")).strip(),
        "author_handle": str(item.get("author_handle", "")).lstrip("@").strip(),
        "author_name": str(item.get("author_name", "")).strip(),
        "timestamp": str(item.get("timestamp", "")).strip(),
        "text": str(item.get("text", "")).strip(),
        "hashtags": [str(h).lower().strip() for h in (item.get("hashtags") or [])],
        "views": parse_x_count(item.get("views", 0)),
        "replies": parse_x_count(item.get("replies", 0)),
        "reposts": parse_x_count(item.get("reposts", 0)),
        "likes": parse_x_count(item.get("likes", 0)),
        "bookmarks": parse_x_count(item.get("bookmarks", 0)),
        "is_reply": bool(item.get("is_reply", False)),
        "has_media": bool(item.get("has_media", False)),
        "queries": list(item.get("queries") or []),
    }


def load_raw_exports(paths: list[str]) -> list[dict]:
    """Loads one or more raw X export JSON files and deduplicates tweets by tweet_id."""
    merged: dict[str, dict] = {}
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        items = payload.get("tweets", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            continue
        for item in items:
            norm_rec = normalize_raw_tweet(item)
            if not norm_rec:
                continue
            tid = norm_rec["tweet_id"]
            prev = merged.get(tid)
            if not prev:
                merged[tid] = norm_rec
            else:
                for metric in ("views", "replies", "reposts", "likes", "bookmarks"):
                    norm_rec[metric] = max(prev[metric], norm_rec[metric])
                norm_rec["queries"] = list(
                    dict.fromkeys([*prev["queries"], *norm_rec["queries"]])
                )
                if not norm_rec["text"] and prev["text"]:
                    norm_rec["text"] = prev["text"]
                merged[tid] = norm_rec
    return list(merged.values())


NON_LATIN_SPAM_RE = re.compile(
    r"[\u0600-\u06FF\u0900-\u097F\u3040-\u30FF\u4E00-\u9FFF]"
)
REPLY_PREFIX_RE = re.compile(
    r"^(?:\d+\s*(?:g\.?|godz\.?|min|m|h|s|d)\s+)?(?:Odpowiedź do(?:\s+użytkownika|\s+użytkowników)?|W odpowiedzi do|Odpowiadanie(?:\s+użytkownikowi)?|Replying to)(?:\s+(?:@[A-Za-z0-9_]+|i|and|oraz|\d+\s+innych))*\s*",
    re.IGNORECASE,
)


def clean_display_text(text: str) -> str:
    """Strips X UI boilerplate like 'Konto parodystyczne' or 'Odpowiedź do @...' for snippets."""
    cleaned = text.strip()
    cleaned = re.sub(
        r"^(?:Konto parodystyczne|Parody account)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = REPLY_PREFIX_RE.sub("", cleaned).strip()
    return cleaned


def classify_tweet(
    tweet: dict,
    crew_handles: set[str],
    related_handles: set[str],
) -> tuple[bool, str, str, bool]:
    """Determines whether a post belongs in #bunkier Worlds 2026 analytics.

    Returns (keep, role, reason, has_bunkier_hashtag).
    """
    handle_l = tweet["author_handle"].lower()
    text_l = tweet["text"].lower()
    tags_l = {h.lower() for h in tweet.get("hashtags", [])}

    # Check context on reply-stripped, mention-stripped body so "@lewuslol" doesn't match "lol"
    body_no_reply = clean_display_text(tweet["text"])
    body_no_mentions = re.sub(r"@[A-Za-z0-9_]+", " ", body_no_reply).lower()

    if handle_l in crew_handles:
        role = "bunkier"
    else:
        role = "community"
    is_tracked_scene_handle = (handle_l in crew_handles) or (
        handle_l in related_handles
    )

    has_bunkier_tag = ("#bunkier" in tags_l) or bool(
        re.search(r"(?:^|\W)#bunkier(?:\W|$)", text_l)
    )
    has_bunkier_variant = (
        ("#bukier" in text_l)
        or ("kielecki bunkier" in text_l)
        or ("kieleckim bunkrze" in text_l)
        or ("inicjatywa bunkier" in text_l)
    )
    has_esports_ctx = any(kw in body_no_mentions for kw in CONTEXT_KEYWORDS) or bool(
        TOKEN_KEYWORDS_RE.search(body_no_mentions)
    )
    has_noise_term = any(nt in text_l for nt in NOISE_TERMS)

    if is_tracked_scene_handle:
        if has_bunkier_tag:
            return True, role, "ok", has_bunkier_tag
        if RELATED_OFFTOPIC_RE.search(text_l):
            return False, role, "offtopic_event", has_bunkier_tag
        if has_bunkier_variant or has_esports_ctx:
            return True, role, "ok", has_bunkier_tag
        return False, role, "non_worlds_post", has_bunkier_tag

    if NON_LATIN_SPAM_RE.search(tweet["text"]) and not any(
        strong in text_l
        for strong in ("worlds", "gadają", "gadaja", "goe", "t1", "blg", "gen.g", "lol")
    ):
        return False, role, "offtopic_non_latin_spam", has_bunkier_tag

    if has_noise_term and not (has_esports_ctx and not has_noise_term):
        # Explicit off-topic club/urbex/shelter noise unless GoE/Worlds context dominates
        if not any(
            strong in text_l
            for strong in ("worlds", "gadają", "gadaja", "goe", "t1", "blg", "gen.g")
        ):
            return False, role, "offtopic_noise_term", has_bunkier_tag

    if has_bunkier_tag or has_bunkier_variant:
        return True, role, "ok", has_bunkier_tag

    return False, role, "no_bunkier_tag", has_bunkier_tag


def build_x_analytics(
    raw_tweets: list[dict],
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    extra_related_handles: set[str] | None = None,
) -> tuple[dict, list[dict]]:
    """Computes aggregated analytics and rejected-item audit list from normalized tweets."""
    crew_handles = set(GOE_CREW_HANDLES)
    related_handles = set(RELATED_CREATOR_HANDLES)
    if extra_related_handles:
        related_handles.update(h.lower().lstrip("@") for h in extra_related_handles)

    match_dates = {cfg.get("date", "") for cfg in DAYS_CONFIG.values()}
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date()

    kept_tweets: list[dict] = []
    rejected_tweets: list[dict] = []

    for raw_tw in raw_tweets:
        tw = normalize_raw_tweet(raw_tw)
        if not tw:
            rejected_tweets.append({**raw_tw, "reject_reason": "missing_tweet_id"})
            continue
        dt_pl = parse_warsaw_timestamp(tw.get("timestamp", ""))
        if not dt_pl:
            rejected_tweets.append({**tw, "reject_reason": "invalid_timestamp"})
            continue
        day_date = dt_pl.date()
        if day_date < d_start or day_date > d_end:
            rejected_tweets.append(
                {**tw, "reject_reason": f"outside_window:{day_date.isoformat()}"}
            )
            continue

        keep, role, reason, has_tag = classify_tweet(tw, crew_handles, related_handles)
        is_reply_detected = tw["is_reply"] or bool(REPLY_PREFIX_RE.match(tw["text"]))
        enriched = {
            **tw,
            "is_reply": is_reply_detected,
            "display_text": clean_display_text(tw["text"]),
            "role": role,
            "has_bunkier_hashtag": has_tag,
            "date_pl": day_date.isoformat(),
            "date_label": dt_pl.strftime("%d.%m"),
            "time_pl": dt_pl.strftime("%H:%M"),
            "interactions": tw["likes"] + tw["reposts"] + tw["replies"],
        }
        if keep:
            kept_tweets.append(enriched)
        else:
            rejected_tweets.append({**enriched, "reject_reason": reason})

    # Totals
    total_posts = len(kept_tweets)
    hashtag_posts = sum(1 for t in kept_tweets if t["has_bunkier_hashtag"])
    original_posts = sum(1 for t in kept_tweets if not t["is_reply"])
    reply_posts = total_posts - original_posts
    total_views = sum(t["views"] for t in kept_tweets)
    total_likes = sum(t["likes"] for t in kept_tweets)
    total_reposts = sum(t["reposts"] for t in kept_tweets)
    total_replies = sum(t["replies"] for t in kept_tweets)
    total_bookmarks = sum(t["bookmarks"] for t in kept_tweets)
    total_interactions = total_likes + total_reposts + total_replies
    er_pct = (
        round((total_interactions / total_views) * 100, 2) if total_views > 0 else 0.0
    )

    # Group split: Bunkier vs Społeczność
    group_acc: dict[str, dict] = {
        "bunkier": {
            "posts": 0,
            "hashtag_posts": 0,
            "views": 0,
            "interactions": 0,
            "authors": set(),
        },
        "community": {
            "posts": 0,
            "hashtag_posts": 0,
            "views": 0,
            "interactions": 0,
            "authors": set(),
        },
    }
    author_acc: dict[str, dict] = {}
    daily_acc: dict[str, dict] = defaultdict(
        lambda: {
            "posts": 0,
            "hashtag_posts": 0,
            "views": 0,
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "interactions": 0,
            "authors": set(),
        }
    )

    for tw in kept_tweets:
        role = tw["role"]
        h_key = tw["author_handle"].lower()

        g = group_acc[role]
        g["posts"] += 1
        g["hashtag_posts"] += 1 if tw["has_bunkier_hashtag"] else 0
        g["views"] += tw["views"]
        g["interactions"] += tw["interactions"]
        g["authors"].add(h_key)

        if h_key not in author_acc:
            author_acc[h_key] = {
                "handle": tw["author_handle"],
                "author_name": tw["author_name"],
                "role": role,
                "posts": 0,
                "hashtag_posts": 0,
                "views": 0,
                "likes": 0,
                "reposts": 0,
                "replies": 0,
                "interactions": 0,
            }
        a = author_acc[h_key]
        a["posts"] += 1
        a["hashtag_posts"] += 1 if tw["has_bunkier_hashtag"] else 0
        a["views"] += tw["views"]
        a["likes"] += tw["likes"]
        a["reposts"] += tw["reposts"]
        a["replies"] += tw["replies"]
        a["interactions"] += tw["interactions"]

        d = daily_acc[tw["date_pl"]]
        d["posts"] += 1
        d["hashtag_posts"] += 1 if tw["has_bunkier_hashtag"] else 0
        d["views"] += tw["views"]
        d["likes"] += tw["likes"]
        d["reposts"] += tw["reposts"]
        d["replies"] += tw["replies"]
        d["interactions"] += tw["interactions"]
        d["authors"].add(h_key)

    # Full continuous daily timeline
    daily_series = []
    cur = d_start
    while cur <= d_end:
        d_iso = cur.isoformat()
        d_raw = daily_acc[d_iso]
        daily_series.append(
            {
                "date": d_iso,
                "label": cur.strftime("%d.%m"),
                "is_match_day": d_iso in match_dates,
                "posts": d_raw["posts"],
                "hashtag_posts": d_raw["hashtag_posts"],
                "views": d_raw["views"],
                "likes": d_raw["likes"],
                "reposts": d_raw["reposts"],
                "replies": d_raw["replies"],
                "interactions": d_raw["interactions"],
                "unique_authors": len(d_raw["authors"]),
            }
        )
        cur += timedelta(days=1)

    def _serialize_group(key: str) -> dict:
        g = group_acc[key]
        return {
            "posts": g["posts"],
            "posts_pct": round((g["posts"] / total_posts) * 100, 1)
            if total_posts > 0
            else 0.0,
            "hashtag_posts": g["hashtag_posts"],
            "views": g["views"],
            "views_pct": round((g["views"] / total_views) * 100, 1)
            if total_views > 0
            else 0.0,
            "interactions": g["interactions"],
            "unique_authors": len(g["authors"]),
        }

    top_authors = sorted(
        author_acc.values(),
        key=lambda x: (x["views"], x["interactions"], x["posts"]),
        reverse=True,
    )[:10]

    top_posts = sorted(
        kept_tweets,
        key=lambda x: (x["views"], x["interactions"], x["likes"]),
        reverse=True,
    )[:10]

    summary = {
        "generated_at": datetime.now(WARSAW_TZ).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "date_range": {
            "start": start_date,
            "end": end_date,
            "start_label": d_start.strftime("%d.%m"),
            "end_label": d_end.strftime("%d.%m"),
            "days_count": len(daily_series),
        },
        "totals": {
            "posts": total_posts,
            "hashtag_posts": hashtag_posts,
            "non_hashtag_posts": total_posts - hashtag_posts,
            "original_posts": original_posts,
            "reply_posts": reply_posts,
            "unique_authors": len(author_acc),
            "views": total_views,
            "likes": total_likes,
            "reposts": total_reposts,
            "replies": total_replies,
            "bookmarks": total_bookmarks,
            "interactions": total_interactions,
            "engagement_rate_pct": er_pct,
            "rejected_count": len(rejected_tweets),
        },
        "groups": {
            "bunkier": _serialize_group("bunkier"),
            "community": _serialize_group("community"),
        },
        "daily": daily_series,
        "top_authors": top_authors,
        "top_posts": [
            {
                "tweet_id": p["tweet_id"],
                "url": p["url"],
                "author_handle": p["author_handle"],
                "author_name": p["author_name"],
                "role": p["role"],
                "date_pl": p["date_pl"],
                "date_label": p["date_label"],
                "time_pl": p["time_pl"],
                "has_bunkier_hashtag": p["has_bunkier_hashtag"],
                "text": p["text"],
                "display_text": p["display_text"],
                "views": p["views"],
                "likes": p["likes"],
                "reposts": p["reposts"],
                "replies": p["replies"],
                "interactions": p["interactions"],
            }
            for p in top_posts
        ],
    }
    return summary, rejected_tweets


def run_self_test():
    """Runs unit checks covering count parsing, timezone mapping, deduplication, and filtering."""
    assert parse_x_count("26") == 26
    assert parse_x_count("1 234 wyświetleń") == 1234
    assert parse_x_count("1\u00a0234") == 1234
    assert parse_x_count("1,5 tys. wyświetleń") == 1500
    assert parse_x_count("14.2K views") == 14200
    assert parse_x_count("1,2 mln") == 1_200_000
    assert parse_x_count("") == 0

    sample_tweets = [
        {
            "tweet_id": "1",
            "url": "https://x.com/gadaja_/status/1",
            "author_handle": "gadaja_",
            "author_name": "Gadają o Esporcie",
            "timestamp": "2026-10-31T21:00:00.000Z",
            "text": "Odpalamy #bunkier na Worlds 2026!",
            "hashtags": ["#bunkier"],
            "views": "24,5 tys.",
            "likes": "810",
            "reposts": "65",
            "replies": "34",
            "bookmarks": "19",
            "is_reply": False,
        },
        {
            "tweet_id": "2",
            "url": "https://x.com/Silv4nn/status/2",
            "author_handle": "Silv4nn",
            "author_name": "Silv4n",
            "timestamp": "2026-11-06T22:45:00.000Z",
            "text": "Ten finał BO5 KC vs T1 na Worldsach to totalny odlot",
            "hashtags": [],
            "views": 18400,
            "likes": 620,
            "reposts": 22,
            "replies": 41,
            "bookmarks": 11,
            "is_reply": False,
        },
        {
            "tweet_id": "3",
            "url": "https://x.com/vidz1/status/3",
            "author_handle": "widz1",
            "author_name": "Widz",
            "timestamp": "2026-11-06T22:55:00.000Z",
            "text": "Siedzę w #bunkier i oglądam T1",
            "hashtags": ["#bunkier"],
            "views": 1200,
            "likes": 35,
            "reposts": 2,
            "replies": 4,
            "bookmarks": 0,
            "is_reply": False,
        },
        {
            "tweet_id": "4",
            "url": "https://x.com/spam/status/4",
            "author_handle": "spammer",
            "author_name": "Klub",
            "timestamp": "2026-11-05T18:00:00.000Z",
            "text": "Dziś #techno impreza w Klub Bunkier Kraków #bunkier",
            "hashtags": ["#techno", "#bunkier"],
            "views": 900,
            "likes": 5,
            "reposts": 0,
            "replies": 0,
            "bookmarks": 0,
            "is_reply": False,
        },
        {
            "tweet_id": "5",
            "url": "https://x.com/Silv4nn/status/5",
            "author_handle": "Silv4nn",
            "author_name": "Silv4n",
            "timestamp": "2026-11-02T12:00:00.000Z",
            "text": "Kawa wypita, lecimy na spacer",
            "hashtags": [],
            "views": 500,
            "likes": 12,
            "reposts": 0,
            "replies": 1,
            "bookmarks": 0,
            "is_reply": False,
        },
    ]

    summary, rejected = build_x_analytics(
        sample_tweets, start_date="2026-10-31", end_date="2026-11-11"
    )
    assert summary["totals"]["posts"] == 3, (
        f"Expected 3 kept posts, got {summary['totals']}"
    )
    assert summary["totals"]["hashtag_posts"] == 2
    assert summary["totals"]["views"] == 24500 + 18400 + 1200
    assert summary["totals"]["rejected_count"] == 2
    assert len(summary["daily"]) == 12
    assert summary["daily"][0]["date"] == "2026-10-31"
    assert summary["daily"][-1]["date"] == "2026-11-11"
    assert summary["groups"]["bunkier"]["posts"] == 1
    assert summary["groups"]["community"]["posts"] == 2
    print("✅ [x_analytics] Self-test PASSED (parsing, filtering, timezone, grouping).")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze exported #bunkier X/Twitter JSON."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[os.path.join(BASE_DIR, "x_bunkier_raw.json")],
        help="Path(s) to raw X export JSON files",
    )
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument(
        "--extra-related",
        nargs="*",
        default=[],
        help="Additional X handles to classify as related creators",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BASE_DIR, "x_bunkier_analytics.json"),
    )
    parser.add_argument(
        "--rejected-output",
        default=os.path.join(BASE_DIR, "x_bunkier_rejected.json"),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    existing_inputs = [
        os.path.expanduser(p)
        for p in args.inputs
        if os.path.exists(os.path.expanduser(p))
    ]
    if not existing_inputs:
        raise SystemExit(
            f"Nie znaleziono pliku wejściowego: {args.inputs}. Najpierw wyeksportuj dane z X przy użyciu x_collector.js."
        )

    raw_tweets = load_raw_exports(existing_inputs)
    summary, rejected = build_x_analytics(
        raw_tweets,
        start_date=args.start_date,
        end_date=args.end_date,
        extra_related_handles=set(args.extra_related),
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(args.rejected_output, "w", encoding="utf-8") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)

    tot = summary["totals"]
    print(f"✅ Zapisano analitykę X: {args.output}")
    print(
        f"📊 Posty: {tot['posts']} ({tot['hashtag_posts']} z #bunkier) | "
        f"Wyświetlenia: {tot['views']:,} | Autorzy: {tot['unique_authors']} | "
        f"Interakcje: {tot['interactions']:,} (ER {tot['engagement_rate_pct']}%) | "
        f"Odrzucono: {tot['rejected_count']}"
    )


if __name__ == "__main__":
    main()
