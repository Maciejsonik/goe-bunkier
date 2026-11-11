"""Generates a 1080x1350 GoE #bunkier X (Twitter) activity infographic."""

import argparse
import json
import os
import textwrap

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


def create_x_summary_card(
    analytics: dict,
    output_path: str = os.path.join(BASE_DIR, "x_bunkier_summary.png"),
) -> str:
    """Renders a 1080x1350 infographic summarizing #bunkier activity on X."""
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    font_top_emblem = _get_font(26, bold=True, font_type="rajdhani")
    font_main_title = _get_font(74, font_type="anton")
    font_sub_title = _get_font(20, font_type="rajdhani")
    font_stat_val = _get_font(38, font_type="anton")
    font_stat_lbl = _get_font(15, bold=True, font_type="rajdhani")
    font_stat_sub = _get_font(13, bold=True, font_type="rajdhani")
    font_panel_hdr = _get_font(15, bold=True, font_type="rajdhani")
    font_lbl = _get_font(14, bold=False, font_type="rajdhani")
    font_val = _get_font(14, bold=True, font_type="rajdhani")
    font_small = _get_font(13, bold=True, font_type="rajdhani")
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(13, font_type="rajdhani")

    # 1. Header
    draw_top_emblem(draw, width, 48, "WORLDS 2026 • AKCJA NA X", font_top_emblem)
    draw_slanted_text(
        img,
        "#BUNKIER NA X",
        font_main_title,
        (255, 0, 51),
        (width // 2, 112),
        slant_k=0.20,
    )

    dr = analytics.get("date_range", {})
    sub_text = f"{dr.get('start_label', '31.10')} – {dr.get('end_label', '11.11')} • Zasięgi, posty i zaangażowanie społeczności"
    draw.text(
        (width // 2, 178),
        sub_text,
        fill=(220, 220, 230),
        font=font_sub_title,
        anchor="mm",
    )

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
    role_colors = {
        "bunkier": (255, 95, 110),
        "community": (96, 165, 250),
    }
    for a_idx, auth in enumerate(top_authors):
        ay = card_y1 + 206 + a_idx * 32
        rcol = role_colors.get(auth.get("role", "community"), (230, 230, 240))
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
        rcol = role_colors.get(post.get("role", "community"), (255, 255, 255))
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
        cleaned = clean_text_for_font(raw_snippet.replace("\n", " "))
        snippet = textwrap.shorten(cleaned, width=56, placeholder="...")
        draw.text(
            (right_x + 26, py1 + 43),
            snippet,
            fill=(225, 225, 235),
            font=_get_font(14, bold=False, font_type="rajdhani"),
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
        "Statystyki akcji #bunkier na X (Twitter) • Worlds 2026",
        fill=(140, 140, 150),
        font=font_system_note,
        anchor="mm",
    )

    img.save(output_path, "PNG")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Render 1080x1350 X #bunkier summary PNG."
    )
    parser.add_argument(
        "--input",
        default=os.path.join(BASE_DIR, "x_bunkier_analytics.json"),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BASE_DIR, "x_bunkier_summary.png"),
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        analytics = json.load(f)
    out = create_x_summary_card(analytics, args.output)
    print(f"📊 Wygenerowano infografikę X: {out}")


if __name__ == "__main__":
    main()
