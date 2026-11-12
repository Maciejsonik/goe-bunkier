"""Generates a 1080x1350 GoE #bunkier X (Twitter) activity infographic."""

import argparse
import json
import os

from PIL import Image, ImageDraw

from generate_card import (
    _get_font,
    clean_text_for_font,
    draw_goe_background,
    draw_slanted_text,
    draw_top_emblem,
)
from generate_summary import _draw_segmented_bar

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

X_ROLE_COLORS = {
    "bunkier": (255, 95, 110),
    "community": (96, 165, 250),
}
X_BAR_COLORS = {
    "bunkier": (255, 24, 36),
    "community": (59, 130, 246),
}


def _fmt_space(val: int) -> str:
    return f"{int(val):,}".replace(",", " ")


def _fmt_compact_views(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M".replace(".0M", "M")
    if val >= 1000:
        return f"{val / 1000:.1f}k".replace(".0k", "k")
    return str(val)


def _pl_form(n: int, form1: str, form2_4: str, form5: str) -> str:
    n_abs = abs(int(n))
    if n_abs == 1:
        return form1
    if 12 <= (n_abs % 100) <= 14:
        return form5
    if 2 <= (n_abs % 10) <= 4:
        return form2_4
    return form5


def _truncate_text_to_width(
    draw: ImageDraw.ImageDraw, text: str, font, max_width: int
) -> str:
    """Normalizes whitespace and truncates text cleanly inside max_width pixels."""
    cleaned = " ".join(clean_text_for_font(text).split())
    if not cleaned:
        return ""
    if draw.textlength(cleaned, font=font) <= max_width:
        return cleaned

    ellipsis = "..."
    lo, hi = 0, len(cleaned)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = cleaned[:mid].rstrip() + ellipsis
        if draw.textlength(candidate, font=font) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    trimmed = cleaned[:lo].rstrip()
    # Prefer cutting at word boundary when it preserves most of the preview
    last_space = trimmed.rfind(" ")
    if last_space >= int(len(trimmed) * 0.7):
        trimmed = trimmed[:last_space].rstrip()
    trimmed = trimmed.rstrip(" ,;:-")
    return f"{trimmed}{ellipsis}"


def _draw_x_header(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    width: int,
    title: str,
    subtitle: str,
    title_size: int = 74,
) -> None:
    font_top_emblem = _get_font(26, bold=True, font_type="rajdhani")
    font_main_title = _get_font(title_size, font_type="anton")
    font_sub_title = _get_font(20, font_type="rajdhani")

    draw_top_emblem(draw, width, 48, "WORLDS 2026 • AKCJA NA X", font_top_emblem)
    draw_slanted_text(
        img,
        title,
        font_main_title,
        (255, 0, 51),
        (width // 2, 112),
        slant_k=0.20,
    )
    draw.text(
        (width // 2, 178),
        subtitle,
        fill=(220, 220, 230),
        font=font_sub_title,
        anchor="mm",
    )


def _draw_x_footer(
    draw: ImageDraw.ImageDraw,
    width: int,
    note_text: str = "Statystyki akcji #bunkier na X (Twitter) • Worlds 2026",
) -> None:
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(13, font_type="rajdhani")

    roster_pipes = (
        "DEJF | CZARNYPIOTRUS | BIALITO | MAJUTEK | PEDRO | MAGVAYER | JASKIER"
    )
    draw.text(
        (width // 2, 1222),
        roster_pipes,
        fill=(255, 255, 255),
        font=font_footer_pipes,
        anchor="mm",
    )

    bunkier_w, bunkier_h = 140, 32
    bx, by = (width - bunkier_w) // 2, 1248
    draw.rounded_rectangle(
        [bx, by, bx + bunkier_w, by + bunkier_h], radius=6, fill=(255, 0, 51)
    )
    draw.text(
        (width // 2, by + bunkier_h // 2),
        "#BUNKIER",
        fill=(255, 255, 255),
        font=font_bunkier_badge,
        anchor="mm",
    )

    draw.text(
        (width // 2, 1300),
        note_text,
        fill=(140, 140, 150),
        font=font_system_note,
        anchor="mm",
    )


def _draw_rank_badge(
    draw: ImageDraw.ImageDraw, x: int, y: int, rank: int, w: int = 30, h: int = 21
) -> None:
    styles = {
        1: ((62, 48, 14), (180, 140, 35), (255, 212, 60)),
        2: ((42, 46, 58), (115, 125, 148), (220, 228, 242)),
        3: ((56, 36, 22), (145, 90, 52), (235, 155, 95)),
    }
    fill_col, out_col, txt_col = styles.get(
        rank, ((28, 28, 36), (52, 52, 66), (185, 185, 200))
    )
    draw.rounded_rectangle(
        [x, y, x + w, y + h], radius=5, fill=fill_col, outline=out_col, width=1
    )
    draw.text(
        (x + w // 2, y + h // 2),
        f"#{rank}",
        fill=txt_col,
        font=_get_font(12, bold=True, font_type="rajdhani"),
        anchor="mm",
    )


def create_x_summary_card(
    analytics: dict,
    output_path: str = os.path.join(BASE_DIR, "x_bunkier_summary.png"),
) -> str:
    """Renders a 1080x1350 infographic summarizing #bunkier activity on X."""
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    font_stat_val = _get_font(38, font_type="anton")
    font_stat_lbl = _get_font(15, bold=True, font_type="rajdhani")
    font_stat_sub = _get_font(13, bold=True, font_type="rajdhani")
    font_panel_hdr = _get_font(15, bold=True, font_type="rajdhani")
    font_lbl = _get_font(14, bold=False, font_type="rajdhani")
    font_val = _get_font(14, bold=True, font_type="rajdhani")
    font_small = _get_font(13, bold=True, font_type="rajdhani")

    # 1. Header
    dr = analytics.get("date_range", {})
    sub_text = f"{dr.get('start_label', '31.10')} – {dr.get('end_label', '11.11')} • Zasięgi, posty i zaangażowanie społeczności"
    _draw_x_header(img, draw, width, "#BUNKIER NA X", sub_text, title_size=74)

    # 2. Top 4 KPI Cards
    totals = analytics.get("totals", {})
    groups = analytics.get("groups", {})
    bunkier_grp = groups.get("bunkier", {})
    community = groups.get("community", {})

    box_w = 226
    box_h = 108
    y_boxes = 205
    x_positions = [50, 301, 553, 804]

    views_str = (
        f"{totals.get('views', 0) / 1_000_000:.2f} M"
        if totals.get("views", 0) >= 1_000_000
        else _fmt_space(totals.get("views", 0))
    )

    non_hash = totals.get("non_hashtag_posts", totals.get("crew_non_hashtag_posts", 0))
    posts_sub = (
        f"{_fmt_space(totals.get('hashtag_posts', 0))} Z #BUNKIER • +{non_hash} WORLDS"
        if non_hash > 0
        else f"{_fmt_space(totals.get('hashtag_posts', 0))} Z HASHTAGIEM #BUNKIER"
    )

    stat_items = [
        (
            "POSTY ŁĄCZNIE",
            _fmt_space(totals.get("posts", 0)),
            (255, 24, 36),
            posts_sub,
        ),
        (
            "WYŚWIETLENIA",
            views_str,
            (0, 229, 255),
            "ŁĄCZNY ZASIĘG POSTÓW",
        ),
        (
            "UNIKALNI AUTORZY",
            _fmt_space(totals.get("unique_authors", 0)),
            (255, 255, 255),
            f"{bunkier_grp.get('unique_authors', 0)} BUNKIER • {community.get('unique_authors', 0)} SPOŁECZNOŚĆ",
        ),
        (
            "INTERAKCJE",
            _fmt_space(totals.get("interactions", 0)),
            (96, 165, 250),
            f"ER {totals.get('engagement_rate_pct', 0.0)}% • {_fmt_space(totals.get('likes', 0))} {_pl_form(totals.get('likes', 0), 'POLUBIENIE', 'POLUBIENIA', 'POLUBIEŃ')}",
        ),
    ]

    for i, (lbl, val, col, sub) in enumerate(stat_items):
        bx = x_positions[i]
        draw.rounded_rectangle(
            [bx, y_boxes, bx + box_w, y_boxes + box_h],
            radius=12,
            fill=(10, 10, 12),
            outline=(255, 0, 51),
            width=1,
        )
        draw.text(
            (bx + 14, y_boxes + 12), lbl, fill=(180, 180, 190), font=font_stat_lbl
        )
        draw.text((bx + 14, y_boxes + 34), val, fill=col, font=font_stat_val)
        draw.text(
            (bx + 14, y_boxes + 84), sub, fill=(135, 135, 145), font=font_stat_sub
        )

    # 3. Daily Posts + Views Activity Chart
    chart_x1, chart_y1, chart_x2, chart_y2 = 50, 328, 1030, 735
    draw.rounded_rectangle(
        [chart_x1, chart_y1, chart_x2, chart_y2],
        radius=12,
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )

    draw.text(
        (chart_x1 + 18, chart_y1 + 22),
        "AKTYWNOŚĆ DZIENNA (POSTY ORAZ ZASIĘG):",
        fill=(220, 220, 230),
        font=font_panel_hdr,
        anchor="lm",
    )

    # Chart Legend (right-aligned)
    leg_items = [
        ("Dni BO5 (03-08.11)", (255, 24, 36)),
        ("Poza BO5", (59, 130, 246)),
        ("Zasięg (góra)", (0, 229, 255)),
    ]
    cur_lx = chart_x2 - 18
    leg_cy = chart_y1 + 22
    for lbl, col in reversed(leg_items):
        bbox = font_small.getbbox(lbl)
        cur_lx -= bbox[2] - bbox[0]
        draw.text(
            (cur_lx, leg_cy), lbl, fill=(215, 215, 225), font=font_small, anchor="lm"
        )
        sx2 = cur_lx - 6
        draw.rectangle([sx2 - 12, leg_cy - 6, sx2, leg_cy + 6], fill=col)
        cur_lx = sx2 - 20

    plot_x1, plot_y1, plot_x2, plot_y2 = 96, 376, 1006, 694
    draw.rectangle(
        [plot_x1, plot_y1, plot_x2, plot_y2],
        fill=(8, 8, 12),
        outline=(40, 40, 50),
        width=1,
    )

    daily = analytics.get("daily", [])
    max_posts = max((d.get("posts", 0) for d in daily), default=10)
    axis_top = max(8, int(max_posts * 1.25))
    # Round axis top cleanly
    if axis_top > 20:
        axis_top = ((axis_top + 9) // 10) * 10

    bar_top_limit = plot_y1 + 42  # Reserve clean top band for Cyan Views labels
    bar_max_h = plot_y2 - bar_top_limit

    for g_idx in range(5):
        gy = plot_y2 - int((g_idx / 4) * bar_max_h)
        gval = int(round((g_idx / 4) * axis_top))
        draw.line([(plot_x1, gy), (plot_x2, gy)], fill=(28, 28, 38), width=1)
        draw.text(
            (plot_x1 - 8, gy),
            _fmt_space(gval),
            fill=(140, 140, 150),
            font=font_small,
            anchor="rm",
        )

    draw.text(
        (plot_x1 + 10, plot_y1 + 16),
        "ZASIĘG:",
        fill=(0, 229, 255),
        font=_get_font(12, bold=True, font_type="rajdhani"),
        anchor="lm",
    )

    n_days = max(1, len(daily))
    usable_x1 = plot_x1 + 72
    col_step = (plot_x2 - usable_x1 - 10) / n_days
    bar_w = max(18, min(44, int(col_step * 0.56)))

    for idx, d in enumerate(daily):
        cx = int(usable_x1 + (idx + 0.5) * col_step)
        p_cnt = d.get("posts", 0)
        v_cnt = d.get("views", 0)
        bar_col = (255, 24, 36) if d.get("is_match_day") else (59, 130, 246)

        # Daily compact views badge at top of plot (only suppress if 0 posts)
        v_lbl = _fmt_compact_views(v_cnt) if (v_cnt > 0 or p_cnt > 0) else "-"
        draw.text(
            (cx, plot_y1 + 16),
            v_lbl,
            fill=(0, 229, 255) if v_cnt > 0 else (90, 90, 105),
            font=_get_font(13, bold=True, font_type="rajdhani"),
            anchor="mm",
        )

        if p_cnt > 0:
            bh = max(4, int((p_cnt / axis_top) * bar_max_h))
            bx1 = cx - bar_w // 2
            by1 = plot_y2 - bh
            draw.rounded_rectangle(
                [bx1, by1, bx1 + bar_w, plot_y2],
                radius=4,
                fill=bar_col,
            )
            draw.text(
                (cx, by1 - 6),
                str(p_cnt),
                fill=(255, 255, 255),
                font=_get_font(14, bold=True, font_type="rajdhani"),
                anchor="mb",
            )

        draw.text(
            (cx, plot_y2 + 18),
            d.get("label", ""),
            fill=(225, 225, 235) if d.get("is_match_day") else (150, 150, 165),
            font=_get_font(13, bold=bool(d.get("is_match_day")), font_type="rajdhani"),
            anchor="mm",
        )

    # 4. Bottom Breakdown Cards (750..1094)
    card_y1, card_y2 = 750, 1094
    card_w = 480
    left_x, right_x = 50, 550

    draw.rounded_rectangle(
        [left_x, card_y1, left_x + card_w, card_y2],
        radius=10,
        fill=(14, 14, 18),
        outline=(85, 30, 42),
        width=1,
    )
    draw.rounded_rectangle(
        [right_x, card_y1, right_x + card_w, card_y2],
        radius=10,
        fill=(14, 14, 18),
        outline=(40, 65, 85),
        width=1,
    )

    # Left Card: Bunkier vs Community + Top Authors
    draw.text(
        (left_x + 16, card_y1 + 22),
        "KTO NAPĘDZAŁ AKCJĘ? (BUNKIER vs SPOŁECZNOŚĆ)",
        fill=(255, 75, 90),
        font=font_panel_hdr,
        anchor="lm",
    )

    b_p = bunkier_grp.get("posts_pct", 0.0)
    s_p = community.get("posts_pct", 0.0)
    b_v = bunkier_grp.get("views_pct", 0.0)
    s_v = community.get("views_pct", 0.0)

    draw.text(
        (left_x + 16, card_y1 + 52),
        "Posty:",
        fill=(200, 200, 210),
        font=font_lbl,
        anchor="lm",
    )
    draw.text(
        (left_x + card_w - 16, card_y1 + 52),
        f"Bunkier {b_p}%  •  Społeczność {s_p}%",
        fill=(240, 240, 245),
        font=font_val,
        anchor="rm",
    )
    _draw_segmented_bar(
        img,
        draw,
        left_x + 16,
        card_y1 + 66,
        left_x + card_w - 16,
        card_y1 + 80,
        [(b_p, (255, 24, 36)), (s_p, (59, 130, 246))],
        radius=5,
    )

    draw.text(
        (left_x + 16, card_y1 + 106),
        "Zasięg:",
        fill=(200, 200, 210),
        font=font_lbl,
        anchor="lm",
    )
    draw.text(
        (left_x + card_w - 16, card_y1 + 106),
        f"Bunkier {b_v}%  •  Społeczność {s_v}%",
        fill=(240, 240, 245),
        font=font_val,
        anchor="rm",
    )
    _draw_segmented_bar(
        img,
        draw,
        left_x + 16,
        card_y1 + 120,
        left_x + card_w - 16,
        card_y1 + 134,
        [(b_v, (255, 24, 36)), (s_v, (59, 130, 246))],
        radius=5,
    )

    draw.line(
        [(left_x + 16, card_y1 + 152), (left_x + card_w - 16, card_y1 + 152)],
        fill=(38, 38, 48),
        width=1,
    )
    draw.text(
        (left_x + 16, card_y1 + 174),
        "TOP AUTORZY WG ZASIĘGU (WYŚWIETLEŃ):",
        fill=(255, 204, 0),
        font=font_small,
        anchor="lm",
    )

    top_authors = analytics.get("top_authors", [])[:4]
    for a_idx, auth in enumerate(top_authors):
        ay = card_y1 + 206 + a_idx * 32
        rcol = X_ROLE_COLORS.get(auth.get("role", "community"), (230, 230, 240))
        draw.text(
            (left_x + 16, ay),
            f"{a_idx + 1}. @{auth.get('handle', '')}",
            fill=rcol,
            font=font_val,
            anchor="lm",
        )
        draw.text(
            (left_x + card_w - 16, ay),
            f"{_fmt_space(auth.get('views', 0))} wyśw.  •  {auth.get('posts', 0)} p.",
            fill=(220, 220, 230),
            font=font_lbl,
            anchor="rm",
        )

    # Right Card: Top 3 Posts
    draw.text(
        (right_x + 16, card_y1 + 22),
        "TOP 3 NAJBARDZIEJ ZASIĘGOWE POSTY",
        fill=(0, 229, 255),
        font=font_panel_hdr,
        anchor="lm",
    )

    top_posts = analytics.get("top_posts", [])[:3]
    for p_idx, post in enumerate(top_posts):
        py1 = card_y1 + 44 + p_idx * 98
        py2 = py1 + 88
        draw.rounded_rectangle(
            [right_x + 14, py1, right_x + card_w - 14, py2],
            radius=6,
            fill=(20, 20, 26),
            outline=(45, 45, 58),
            width=1,
        )
        tag_lbl = " • #bunkier" if post.get("has_bunkier_hashtag") else ""
        rcol = X_ROLE_COLORS.get(post.get("role", "community"), (255, 255, 255))
        draw.text(
            (right_x + 26, py1 + 17),
            f"@{post.get('author_handle', '')} • {post.get('date_label', '')}{tag_lbl}",
            fill=rcol,
            font=font_val,
            anchor="lm",
        )
        draw.text(
            (right_x + card_w - 26, py1 + 17),
            f"{_fmt_space(post.get('views', 0))} wyśw.",
            fill=(0, 229, 255),
            font=font_val,
            anchor="rm",
        )

        raw_snippet = post.get("display_text") or post.get("text", "")
        font_snippet = _get_font(14, bold=False, font_type="rajdhani")
        snippet = _truncate_text_to_width(draw, raw_snippet, font_snippet, card_w - 54)
        draw.text(
            (right_x + 26, py1 + 43),
            snippet,
            fill=(225, 225, 235),
            font=font_snippet,
            anchor="lm",
        )
        draw.text(
            (right_x + 26, py1 + 69),
            f"{_fmt_space(post.get('likes', 0))} polubień  •  {_fmt_space(post.get('reposts', 0))} RT  •  {_fmt_space(post.get('replies', 0))} odp.",
            fill=(150, 150, 165),
            font=font_small,
            anchor="lm",
        )

    # 5. Disclaimers Box
    disc_y = 1106
    draw.rounded_rectangle(
        [50, disc_y, width - 50, disc_y + 82],
        radius=6,
        fill=(14, 14, 18),
        outline=(50, 50, 60),
        width=1,
    )
    draw.text(
        (65, disc_y + 17),
        "METODOLOGIA & ZAKRES DANYCH:",
        fill=(255, 204, 0),
        font=font_small,
        anchor="lm",
    )
    rej_cnt = totals.get("rejected_count", 0)
    disc_lines = [
        f"• Okres: {dr.get('start_label', '31.10')}–{dr.get('end_label', '11.11')} (czas polski CET) • Posty z #bunkier oraz wpisy kont Bunkra (@gadaja_ i prowadzących) o Worldsach.",
        f"• Odfiltrowano {rej_cnt} {_pl_form(rej_cnt, 'wpis', 'wpisy', 'wpisów')} spoza kontekstu (szum / poza oknem) • Wyświetlenia (Views) i interakcje wg publicznych liczników X.",
    ]
    for d_idx, dline in enumerate(disc_lines):
        draw.text(
            (65, disc_y + 40 + d_idx * 20),
            dline,
            fill=(165, 165, 180),
            font=_get_font(12, font_type="rajdhani"),
            anchor="lm",
        )

    # 6. Footer
    _draw_x_footer(draw, width)

    img.save(output_path, "PNG")
    return output_path


def _draw_top10_authors_panel(
    draw: ImageDraw.ImageDraw,
    top_authors: list[dict],
    total_views: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> None:
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=8,
        fill=(14, 14, 18),
        outline=(50, 50, 62),
        width=1,
    )
    bunkier_cnt = sum(1 for a in top_authors if a.get("role") == "bunkier")
    comm_cnt = len(top_authors) - bunkier_cnt

    draw.text(
        (x1 + 16, y1 + 22),
        "TOP 10 AUTORÓW WG ZASIĘGU",
        fill=(255, 75, 90),
        font=_get_font(15, bold=True, font_type="rajdhani"),
        anchor="lm",
    )
    draw.text(
        (x2 - 16, y1 + 22),
        f"{bunkier_cnt} BUNKIER • {comm_cnt} SPOŁ.",
        fill=(170, 170, 185),
        font=_get_font(12, bold=True, font_type="rajdhani"),
        anchor="rm",
    )

    max_views = max((a.get("views", 0) for a in top_authors), default=1) or 1
    font_handle = _get_font(16, bold=True, font_type="rajdhani")
    font_views = _get_font(15, bold=True, font_type="rajdhani")
    font_meta = _get_font(13, bold=True, font_type="rajdhani")
    font_share = _get_font(12, bold=True, font_type="rajdhani")

    cx1, cx2 = x1 + 14, x2 - 14
    bar_w = (cx2 - 12) - (cx1 + 12)

    for idx, auth in enumerate(top_authors):
        ry = y1 + 46 + idx * 84
        draw.rounded_rectangle(
            [cx1, ry, cx2, ry + 76],
            radius=6,
            fill=(20, 20, 26),
            outline=(45, 45, 58),
            width=1,
        )
        role = auth.get("role", "community")
        rcol = X_ROLE_COLORS.get(role, (230, 230, 240))
        bcol = X_BAR_COLORS.get(role, (59, 130, 246))

        _draw_rank_badge(draw, cx1 + 10, ry + 9, idx + 1)
        draw.text(
            (cx1 + 48, ry + 20),
            f"@{auth.get('handle', '')}",
            fill=rcol,
            font=font_handle,
            anchor="lm",
        )
        views = auth.get("views", 0)
        draw.text(
            (cx2 - 12, ry + 20),
            f"{_fmt_space(views)} wyśw.",
            fill=(0, 229, 255),
            font=font_views,
            anchor="rm",
        )

        # Proportional reach bar
        bx1, by1, bx2, by2 = cx1 + 12, ry + 39, cx2 - 12, ry + 45
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=3, fill=(30, 30, 40))
        fill_w = max(8, int(bar_w * (views / max_views))) if views > 0 else 0
        if fill_w > 0:
            draw.rounded_rectangle(
                [bx1, by1, min(bx2, bx1 + fill_w), by2], radius=3, fill=bcol
            )

        posts = auth.get("posts", 0)
        hash_posts = auth.get("hashtag_posts", 0)
        inter = auth.get("interactions", 0)
        share_pct = (views / total_views) * 100 if total_views > 0 else 0.0
        draw.text(
            (cx1 + 12, ry + 61),
            f"{posts} {_pl_form(posts, 'post', 'posty', 'postów')} ({hash_posts} #)  •  {_fmt_space(inter)} int.",
            fill=(168, 168, 184),
            font=font_meta,
            anchor="lm",
        )
        draw.text(
            (cx2 - 12, ry + 61),
            f"{share_pct:.1f}% akcji",
            fill=(135, 135, 152),
            font=font_share,
            anchor="rm",
        )


def _draw_top10_posts_panel(
    draw: ImageDraw.ImageDraw,
    top_posts: list[dict],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> None:
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=8,
        fill=(14, 14, 18),
        outline=(50, 50, 62),
        width=1,
    )
    bunkier_cnt = sum(1 for p in top_posts if p.get("role") == "bunkier")
    comm_cnt = len(top_posts) - bunkier_cnt

    draw.text(
        (x1 + 16, y1 + 22),
        "TOP 10 POSTÓW WG ZASIĘGU",
        fill=(0, 229, 255),
        font=_get_font(15, bold=True, font_type="rajdhani"),
        anchor="lm",
    )
    draw.text(
        (x2 - 16, y1 + 22),
        f"{bunkier_cnt} BUNKIER • {comm_cnt} SPOŁ.",
        fill=(170, 170, 185),
        font=_get_font(12, bold=True, font_type="rajdhani"),
        anchor="rm",
    )

    font_hdr = _get_font(15, bold=True, font_type="rajdhani")
    font_views = _get_font(15, bold=True, font_type="rajdhani")
    font_snip = _get_font(14, bold=False, font_type="rajdhani")
    font_meta = _get_font(12, bold=True, font_type="rajdhani")

    cx1, cx2 = x1 + 14, x2 - 14
    max_snip_w = (cx2 - 12) - (cx1 + 12)

    for idx, post in enumerate(top_posts):
        ry = y1 + 46 + idx * 84
        draw.rounded_rectangle(
            [cx1, ry, cx2, ry + 76],
            radius=6,
            fill=(20, 20, 26),
            outline=(45, 45, 58),
            width=1,
        )
        role = post.get("role", "community")
        rcol = X_ROLE_COLORS.get(role, (230, 230, 240))
        tag_lbl = " • #bunkier" if post.get("has_bunkier_hashtag") else ""

        _draw_rank_badge(draw, cx1 + 10, ry + 8, idx + 1)
        draw.text(
            (cx1 + 48, ry + 19),
            f"@{post.get('author_handle', '')} • {post.get('date_label', '')}{tag_lbl}",
            fill=rcol,
            font=font_hdr,
            anchor="lm",
        )
        p_views = post.get("views", 0)
        draw.text(
            (cx2 - 12, ry + 19),
            f"{_fmt_space(p_views)} wyśw.",
            fill=(0, 229, 255),
            font=font_views,
            anchor="rm",
        )

        raw_snippet = post.get("display_text") or post.get("text", "")
        snippet = _truncate_text_to_width(draw, raw_snippet, font_snip, max_snip_w)
        draw.text(
            (cx1 + 12, ry + 43),
            snippet,
            fill=(225, 225, 235),
            font=font_snip,
            anchor="lm",
        )

        likes = post.get("likes", 0)
        reposts = post.get("reposts", 0)
        replies = post.get("replies", 0)
        inter = post.get("interactions", likes + reposts + replies)
        er_pct = (inter / p_views) * 100 if p_views > 0 else 0.0
        draw.text(
            (cx1 + 12, ry + 63),
            f"{_fmt_space(likes)} polubień  •  {_fmt_space(reposts)} RT  •  {_fmt_space(replies)} odp.",
            fill=(152, 152, 170),
            font=font_meta,
            anchor="lm",
        )
        draw.text(
            (cx2 - 12, ry + 63),
            f"ER {er_pct:.2f}%",
            fill=(135, 135, 152),
            font=font_meta,
            anchor="rm",
        )


def create_x_top10_card(
    analytics: dict,
    output_path: str = os.path.join(BASE_DIR, "x_bunkier_top10.png"),
) -> str:
    """Renders a 1080x1350 leaderboard infographic for Top 10 authors and Top 10 posts."""
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)
    draw_goe_background(draw, width, height)

    dr = analytics.get("date_range", {})
    sub_text = (
        f"{dr.get('start_label', '31.10')} – {dr.get('end_label', '11.11')} • "
        "Liderzy zasięgu i najpopularniejsze posty akcji"
    )
    _draw_x_header(img, draw, width, "#BUNKIER • TOP 10", sub_text, title_size=70)

    totals = analytics.get("totals", {})
    total_views = max(1, totals.get("views", 1))
    total_posts = totals.get("posts", 0)
    top_authors = analytics.get("top_authors", [])[:10]
    top_posts = analytics.get("top_posts", [])[:10]

    ta_views = sum(a.get("views", 0) for a in top_authors)
    ta_posts = sum(a.get("posts", 0) for a in top_authors)
    ta_pct = (
        round((ta_views / total_views) * 100, 1) if totals.get("views", 0) > 0 else 0.0
    )

    tp_views = sum(p.get("views", 0) for p in top_posts)
    tp_pct = (
        round((tp_views / total_views) * 100, 1) if totals.get("views", 0) > 0 else 0.0
    )
    tp_bunkier = sum(1 for p in top_posts if p.get("role") == "bunkier")
    tp_comm = len(top_posts) - tp_bunkier

    # 3 Compact KPI Strip Cards
    box_w, box_h, y_box = 314, 76, 202
    x_boxes = [50, 383, 716]
    font_kpi_lbl = _get_font(13, bold=True, font_type="rajdhani")
    font_kpi_val = _get_font(26, font_type="anton")
    font_kpi_sub = _get_font(13, bold=True, font_type="rajdhani")

    for bx in x_boxes:
        draw.rounded_rectangle(
            [bx, y_box, bx + box_w, y_box + box_h],
            radius=8,
            fill=(14, 14, 18),
            outline=(60, 60, 75),
            width=1,
        )

    # Box 1: Top 10 Authors share
    draw.text(
        (x_boxes[0] + box_w // 2, y_box + 15),
        "TOP 10 AUTORÓW",
        fill=(180, 180, 190),
        font=font_kpi_lbl,
        anchor="mm",
    )
    draw.text(
        (x_boxes[0] + box_w // 2, y_box + 39),
        f"{ta_pct}% ZASIĘGU",
        fill=(255, 24, 36),
        font=font_kpi_val,
        anchor="mm",
    )
    draw.text(
        (x_boxes[0] + box_w // 2, y_box + 62),
        f"{_fmt_space(ta_views)} wyśw. • {ta_posts}/{total_posts} postów",
        fill=(155, 155, 170),
        font=font_kpi_sub,
        anchor="mm",
    )

    # Box 2: Top 10 Posts share
    draw.text(
        (x_boxes[1] + box_w // 2, y_box + 15),
        "TOP 10 POSTÓW",
        fill=(180, 180, 190),
        font=font_kpi_lbl,
        anchor="mm",
    )
    draw.text(
        (x_boxes[1] + box_w // 2, y_box + 39),
        f"{tp_pct}% ZASIĘGU",
        fill=(0, 229, 255),
        font=font_kpi_val,
        anchor="mm",
    )
    draw.text(
        (x_boxes[1] + box_w // 2, y_box + 62),
        f"{_fmt_space(tp_views)} wyśw. • {tp_bunkier} Bunkier / {tp_comm} Społ.",
        fill=(155, 155, 170),
        font=font_kpi_sub,
        anchor="mm",
    )

    # Box 3: Legend (centered dynamically)
    b3_mid = x_boxes[2] + box_w // 2
    draw.text(
        (b3_mid, y_box + 15),
        "OZNACZENIA GRUP",
        fill=(180, 180, 190),
        font=font_kpi_lbl,
        anchor="mm",
    )
    font_leg = _get_font(16, bold=True, font_type="rajdhani")
    dot_d, dot_gap, grp_gap = 10, 7, 24
    w_b = draw.textlength("Bunkier", font=font_leg)
    w_c = draw.textlength("Społeczność", font=font_leg)
    total_leg_w = (dot_d + dot_gap + w_b) + grp_gap + (dot_d + dot_gap + w_c)
    lx = int(b3_mid - total_leg_w / 2)
    draw.ellipse([lx, y_box + 34, lx + dot_d, y_box + 44], fill=(255, 24, 36))
    draw.text(
        (lx + dot_d + dot_gap, y_box + 39),
        "Bunkier",
        fill=X_ROLE_COLORS["bunkier"],
        font=font_leg,
        anchor="lm",
    )
    lx2 = int(lx + dot_d + dot_gap + w_b + grp_gap)
    draw.ellipse([lx2, y_box + 34, lx2 + dot_d, y_box + 44], fill=(59, 130, 246))
    draw.text(
        (lx2 + dot_d + dot_gap, y_box + 39),
        "Społeczność",
        fill=X_ROLE_COLORS["community"],
        font=font_leg,
        anchor="lm",
    )
    draw.text(
        (b3_mid, y_box + 62),
        "Ranking wg wyświetleń (Views) na X",
        fill=(155, 155, 170),
        font=font_kpi_sub,
        anchor="mm",
    )

    # Main 2-column Leaderboard
    _draw_top10_authors_panel(draw, top_authors, total_views, 50, 294, 508, 1192)
    _draw_top10_posts_panel(draw, top_posts, 524, 294, 1030, 1192)

    _draw_x_footer(
        draw,
        width,
        f"Ranking TOP 10 akcji #bunkier na X ({dr.get('start_label', '31.10')}–{dr.get('end_label', '11.11')} CET) • Worlds 2026",
    )

    img.save(output_path, "PNG")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Render 1080x1350 X #bunkier summary and top10 PNGs."
    )
    parser.add_argument(
        "--input",
        default=os.path.join(BASE_DIR, "x_bunkier_analytics.json"),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BASE_DIR, "x_bunkier_summary.png"),
    )
    parser.add_argument(
        "--top10-output",
        default=os.path.join(BASE_DIR, "x_bunkier_top10.png"),
    )
    parser.add_argument(
        "--mode",
        choices=["all", "summary", "top10"],
        default="all",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        analytics = json.load(f)
    if args.mode in ("all", "summary"):
        out = create_x_summary_card(analytics, args.output)
        print(f"📊 Wygenerowano infografikę X: {out}")
    if args.mode in ("all", "top10"):
        out_top = create_x_top10_card(analytics, args.top10_output)
        print(f"🏆 Wygenerowano infografikę TOP 10 X: {out_top}")


if __name__ == "__main__":
    main()
