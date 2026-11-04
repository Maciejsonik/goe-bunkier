"""Generates post-stream line chart infographics in GoE aesthetic: GoE-only or Comparison (1080x1350)."""

import os
from PIL import Image, ImageDraw, ImageFont

from db import (
    filter_bot_attacks,
    get_detailed_history,
    get_history,
    get_summary_stats,
)
from generate_card import (
    _get_font,
    draw_goe_background,
    draw_slanted_text,
    draw_vector_microphone,
)


def create_summary_card(
    output_path: str = "stream_summary.png",
    mode: str = "COMPARISON",
    platform: str = "ALL",
    custom_history: list[dict] = None,
    filter_bots: bool = True,
) -> str:
    """Renders a clean post-stream timeline chart in GoE aesthetic.

    Modes:
    - 'GOE': Dedicated GoE-only chart (Total GoE, YouTube, Twitch)
    - 'COMPARISON': Head-to-head chart (GoE vs Nervarien)
    """
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    # Fetch and filter history
    if custom_history is not None:
        raw_pts = [dict(p) for p in custom_history]
    else:
        raw_pts = get_detailed_history(limit=5000)

    history_points = filter_bot_attacks(raw_pts, enabled=filter_bots)
    if len(history_points) < 2:
        history_points = []

    stats = get_summary_stats(
        platform=platform,
        custom_history=history_points,
        filter_bots=filter_bots,
    )

    font_top_emblem = _get_font(26, bold=True, font_type="rajdhani")
    font_main_title = _get_font(78, font_type="anton")
    font_sub_title = _get_font(22, font_type="rajdhani")
    font_stat_val = _get_font(46, font_type="anton")
    font_stat_lbl = _get_font(16, font_type="rajdhani")
    font_axis = _get_font(14, bold=False)
    font_legend = _get_font(18, font_type="rajdhani")
    font_callout = _get_font(14, font_type="rajdhani")
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(14, font_type="rajdhani")
    font_badge = _get_font(14, font_type="rajdhani")

    # Top Emblem (Crisp vector microphone icon + WORLDS 2026 text)
    mic_cx, mic_cy = width // 2 - 85, 54
    draw_vector_microphone(draw, mic_cx, mic_cy)
    draw.line([(mic_cx + 20, 42), (mic_cx + 20, 66)], fill=(255, 255, 255), width=2)
    draw.text(
        (mic_cx + 36, 54),
        "WORLDS 2026",
        fill=(255, 255, 255),
        font=font_top_emblem,
        anchor="lm",
    )

    # Slanted Main Title
    title_text = "CO-STREAM GOE" if mode == "GOE" else "GOE vs NERVARIEN"
    draw_slanted_text(
        img,
        title_text,
        font_main_title,
        (255, 0, 51),
        (width // 2, 125),
        slant_k=0.20,
    )

    time_range = (
        f"{stats.get('start_time', '')} — {stats.get('end_time', '')}"
        if stats.get("start_time")
        else ""
    )
    sub_title_text = (
        f"w Kieleckim bunkrze • Widownia Co-stream GoE • {time_range}"
        if mode == "GOE"
        else f"w Kieleckim bunkrze vs Nervarien • Porównanie • {time_range}"
    )
    draw.text(
        (width // 2, 172),
        sub_title_text,
        fill=(255, 255, 255),
        font=font_sub_title,
        anchor="mm",
    )

    # Bot Filter Status Badge (clean text without emoji to avoid tofu glyphs)
    badge_y = 200
    if filter_bots:
        badge_text = "DANE OCZYSZCZONE (ODFILTROWANO ATAKI BOTÓW NA YOUTUBE)"
        badge_bg = (14, 35, 20)
        badge_border = (74, 222, 128)
        badge_fg = (74, 222, 128)
    else:
        badge_text = "SUROWE DANE (UWZGLĘDNIAJĄ SZTUCZNE PIKI BOTÓW NA YOUTUBE)"
        badge_bg = (40, 16, 16)
        badge_border = (248, 113, 113)
        badge_fg = (248, 113, 113)

    badge_w = 540
    badge_h = 24
    bx1 = (width - badge_w) // 2
    draw.rounded_rectangle(
        [bx1, badge_y, bx1 + badge_w, badge_y + badge_h],
        radius=12,
        fill=badge_bg,
        outline=badge_border,
        width=1,
    )
    draw.text(
        (width // 2, badge_y + badge_h // 2),
        badge_text,
        fill=badge_fg,
        font=font_badge,
        anchor="mm",
    )

    box_w = 225
    box_h = 122
    y_boxes = 236
    x_positions = [50, 305, 560, 805]

    # Stats setup
    if mode == "GOE":
        # Calculate GoE peak YT and peak Twitch
        def _get_goe_yt_v(p):
            for sid, s in p.get("streams", {}).items():
                if sid != "goe_stream" and (
                    s.get("platform") == "YouTube"
                    or s.get("group") == "GOE"
                    or sid == "I2E60nEUXWo"
                ):
                    return s.get(
                        "viewers" if filter_bots else "viewers_raw", s.get("viewers", 0)
                    )
            return 0

        peak_yt = max((_get_goe_yt_v(p) for p in history_points), default=0)
        peak_tw = max(
            (
                p.get("streams", {}).get("goe_stream", {}).get("viewers", 0)
                for p in history_points
            ),
            default=0,
        )

        stat_items = [
            (
                "PIK GOE",
                f"{stats['goe_peak']:,}".replace(",", " "),
                (255, 24, 36),
                f"ŁĄCZNIE O {stats.get('goe_peak_time', '')}",
            ),
            (
                "ŚREDNIA GOE",
                f"{stats['goe_avg']:,}".replace(",", " "),
                (255, 255, 255),
                "ORGANICZNA" if filter_bots else "W TRAKCIE STREAMU",
            ),
            (
                "PIK YOUTUBE",
                f"{peak_yt:,}".replace(",", " "),
                (255, 24, 36),
                "GADAJĄ O ESPORCIE",
            ),
            (
                "PIK TWITCH",
                f"{peak_tw:,}".replace(",", " "),
                (145, 70, 255),
                "GOE_STREAM",
            ),
        ]
    else:
        goe_peak_sub = (
            f"PIK O {stats['goe_peak_time']}"
            if stats.get("goe_peak_time")
            else "NAJWYŻSZA WIDOWNIA"
        )
        nerva_peak_sub = (
            f"PIK O {stats['nerva_peak_time']}"
            if stats.get("nerva_peak_time")
            else "NAJWYŻSZA WIDOWNIA"
        )

        stat_items = [
            (
                "PIK GOE",
                f"{stats['goe_peak']:,}".replace(",", " "),
                (255, 24, 36),
                goe_peak_sub,
            ),
            (
                "PIK NERVA",
                f"{stats['nerva_peak']:,}".replace(",", " "),
                (255, 255, 255),
                nerva_peak_sub,
            ),
            (
                "ŚREDNIA GOE",
                f"{stats['goe_avg']:,}".replace(",", " "),
                (255, 24, 36),
                "ORGANICZNA" if filter_bots else "W TRAKCIE STREAMU",
            ),
            (
                "ŚREDNIA NERVA",
                f"{stats['nerva_avg']:,}".replace(",", " "),
                (255, 255, 255),
                "W TRAKCIE STREAMU",
            ),
        ]

    font_stat_val = _get_font(42, font_type="anton")
    font_stat_lbl = _get_font(15, font_type="rajdhani")
    font_stat_sub = _get_font(13, font_type="rajdhani")

    for i, (label, val, color, sub) in enumerate(stat_items):
        bx = x_positions[i]
        draw.rounded_rectangle(
            [bx, y_boxes, bx + box_w, y_boxes + box_h],
            radius=12,
            fill=(10, 10, 12),
            outline=(255, 0, 51),
            width=1,
        )
        draw.text(
            (bx + 16, y_boxes + 13),
            label,
            fill=(180, 180, 190),
            font=font_stat_lbl,
        )
        draw.text((bx + 16, y_boxes + 30), val, fill=color, font=font_stat_val)
        draw.text(
            (bx + 16, y_boxes + 95),
            sub,
            fill=(135, 135, 145),
            font=font_stat_sub,
        )

    # Chart Area
    chart_x1, chart_y1 = 60, 380
    chart_x2, chart_y2 = 1020, 1180
    chart_w = chart_x2 - chart_x1
    chart_h = chart_y2 - chart_y1

    draw.rounded_rectangle(
        [chart_x1 - 10, chart_y1 - 10, chart_x2 + 10, chart_y2 + 10],
        radius=12,
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )

    # Legend depending on mode
    if mode == "GOE":
        # 3 legend items: GoE Łącznie, YouTube, Twitch
        draw.rectangle(
            [chart_x2 - 420, chart_y1 + 14, chart_x2 - 404, chart_y1 + 30],
            fill=(255, 24, 36),
        )
        draw.text(
            (chart_x2 - 395, chart_y1 + 14),
            "GoE Łącznie",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 270, chart_y1 + 14, chart_x2 - 254, chart_y1 + 30],
            fill=(239, 68, 68),
        )
        draw.text(
            (chart_x2 - 245, chart_y1 + 14),
            "YouTube",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 140, chart_y1 + 14, chart_x2 - 124, chart_y1 + 30],
            fill=(145, 70, 255),
        )
        draw.text(
            (chart_x2 - 115, chart_y1 + 14),
            "Twitch",
            fill=(255, 255, 255),
            font=font_legend,
        )
    else:
        # Comparison: GOE vs NERVARIEN
        draw.rectangle(
            [chart_x2 - 320, chart_y1 + 14, chart_x2 - 304, chart_y1 + 30],
            fill=(255, 24, 36),
        )
        draw.text(
            (chart_x2 - 295, chart_y1 + 14),
            "GOE",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 180, chart_y1 + 14, chart_x2 - 164, chart_y1 + 30],
            fill=(255, 255, 255),
        )
        draw.text(
            (chart_x2 - 155, chart_y1 + 14),
            "NERVARIEN",
            fill=(255, 255, 255),
            font=font_legend,
        )

    # Plot area
    plot_x1 = chart_x1 + 75
    plot_y1 = chart_y1 + 60
    plot_x2 = chart_x2 - 30
    plot_y2 = chart_y2 - 60
    plot_w = plot_x2 - plot_x1
    plot_h = plot_y2 - plot_y1

    draw.rectangle(
        [plot_x1, plot_y1, plot_x2, plot_y2],
        fill=(8, 8, 12),
        outline=(40, 40, 50),
        width=1,
    )

    if not history_points:
        history_points = [
            {"timestamp": "22:30:00", "goe_total": 2000, "nerva_total": 1000},
            {"timestamp": "23:00:00", "goe_total": 2500, "nerva_total": 3000},
        ]

    num_pts = len(history_points)

    if mode == "GOE":
        max_v = max(
            (
                (
                    p.get("goe_total", 0)
                    if filter_bots
                    else p.get("goe_total_raw", p.get("goe_total", 0))
                )
                for p in history_points
            ),
            default=100,
        )
    else:
        max_v = max(
            max(
                (
                    p.get("goe_total", 0)
                    if filter_bots
                    else p.get("goe_total_raw", p.get("goe_total", 0))
                )
                for p in history_points
            ),
            max(p.get("nerva_total", 0) for p in history_points),
            100,
        )
    max_y = int(max(max_v * 1.20, 100))

    # Grid lines
    grid_steps = 5
    for i in range(grid_steps + 1):
        gy = plot_y2 - int((i / grid_steps) * plot_h)
        val = int((i / grid_steps) * max_y)
        draw.line([(plot_x1, gy), (plot_x2, gy)], fill=(30, 30, 40), width=1)
        val_str = f"{val:,}".replace(",", " ")
        draw.text(
            (plot_x1 - 10, gy),
            val_str,
            fill=(140, 140, 150),
            font=font_axis,
            anchor="rm",
        )

    # Coordinates calculation
    if mode == "GOE":
        goe_coords = []
        yt_coords = []
        tw_coords = []
        curr_max = -1
        max_idx = 0

        for idx, pt in enumerate(history_points):
            x = (
                plot_x1
                if num_pts == 1
                else plot_x1 + int((idx / (num_pts - 1)) * plot_w)
            )
            streams_map = pt.get("streams", {})
            yt_s = {}
            for sid, s in streams_map.items():
                if sid != "goe_stream" and (
                    s.get("platform") == "YouTube"
                    or s.get("group") == "GOE"
                    or sid == "I2E60nEUXWo"
                ):
                    yt_s = s
                    break
            tw_s = streams_map.get("goe_stream", {})
            yt_v = (
                yt_s.get("viewers", 0)
                if filter_bots
                else yt_s.get("viewers_raw", yt_s.get("viewers", 0))
            )
            tw_v = tw_s.get("viewers", 0)
            tot_v = (
                pt.get("goe_total", yt_v + tw_v)
                if filter_bots
                else pt.get("goe_total_raw", pt.get("goe_total", yt_v + tw_v))
            )

            if tot_v > curr_max:
                curr_max = tot_v
                max_idx = idx

            y_tot = plot_y2 - int((tot_v / max_y) * plot_h)
            y_yt = plot_y2 - int((yt_v / max_y) * plot_h)
            y_tw = plot_y2 - int((tw_v / max_y) * plot_h)

            goe_coords.append((x, y_tot))
            yt_coords.append((x, y_yt))
            tw_coords.append((x, y_tw))

        # Fill under total line
        if len(goe_coords) >= 2:
            fill_poly = [(plot_x1, plot_y2)] + goe_coords + [(plot_x2, plot_y2)]
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon(fill_poly, fill=(255, 24, 36, 45))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        # Lines for YT and Twitch
        for i in range(len(tw_coords) - 1):
            draw.line([tw_coords[i], tw_coords[i + 1]], fill=(145, 70, 255), width=2)
        for i in range(len(yt_coords) - 1):
            draw.line([yt_coords[i], yt_coords[i + 1]], fill=(239, 68, 68), width=2)

        # Thick line for GoE Total
        for i in range(len(goe_coords) - 1):
            draw.line([goe_coords[i], goe_coords[i + 1]], fill=(255, 24, 36), width=4)
        for x, y in goe_coords[:: max(1, num_pts // 30)]:
            draw.ellipse(
                [x - 4, y - 4, x + 4, y + 4],
                fill=(255, 24, 36),
                outline=(255, 255, 255),
                width=2,
            )

        # Peak Callout
        if goe_coords and curr_max > 0:
            pk_x, pk_y = goe_coords[max_idx]
            callout_text = f"⚡ PIK GOE: {curr_max:,}".replace(",", " ")
            cb_w = 135
            cb_h = 24
            cb_x1 = max(plot_x1 + 10, min(plot_x2 - cb_w - 10, pk_x - cb_w // 2))
            cb_y1 = max(plot_y1 + 5, pk_y - 36)
            draw.rounded_rectangle(
                [cb_x1, cb_y1, cb_x1 + cb_w, cb_y1 + cb_h],
                radius=4,
                fill=(255, 24, 36),
            )
            draw.text(
                (cb_x1 + cb_w // 2, cb_y1 + cb_h // 2),
                callout_text,
                fill=(255, 255, 255),
                font=font_callout,
                anchor="mm",
            )
            draw.line(
                [(pk_x, pk_y), (pk_x, cb_y1 + cb_h)],
                fill=(255, 24, 36),
                width=2,
            )

    else:
        # Comparison mode: GoE vs Nervarien
        goe_coords = []
        nerva_coords = []
        max_goe_idx = 0
        curr_max_goe = -1

        for idx, pt in enumerate(history_points):
            x = (
                plot_x1
                if num_pts == 1
                else plot_x1 + int((idx / (num_pts - 1)) * plot_w)
            )
            gv = (
                pt.get("goe_total", 0)
                if filter_bots
                else pt.get("goe_total_raw", pt.get("goe_total", 0))
            )
            nv = pt.get("nerva_total", 0)

            if gv > curr_max_goe:
                curr_max_goe = gv
                max_goe_idx = idx

            y_goe = plot_y2 - int((gv / max_y) * plot_h)
            y_nerva = plot_y2 - int((nv / max_y) * plot_h)
            goe_coords.append((x, y_goe))
            nerva_coords.append((x, y_nerva))

        if len(goe_coords) >= 2:
            fill_poly = [(plot_x1, plot_y2)] + goe_coords + [(plot_x2, plot_y2)]
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon(fill_poly, fill=(255, 24, 36, 45))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        for i in range(len(nerva_coords) - 1):
            draw.line(
                [nerva_coords[i], nerva_coords[i + 1]],
                fill=(255, 255, 255),
                width=3,
            )
        for x, y in nerva_coords[:: max(1, num_pts // 30)]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255))

        for i in range(len(goe_coords) - 1):
            draw.line([goe_coords[i], goe_coords[i + 1]], fill=(255, 24, 36), width=4)
        for x, y in goe_coords[:: max(1, num_pts // 30)]:
            draw.ellipse(
                [x - 4, y - 4, x + 4, y + 4],
                fill=(255, 24, 36),
                outline=(255, 255, 255),
                width=2,
            )

        if goe_coords and curr_max_goe > 0:
            pk_x, pk_y = goe_coords[max_goe_idx]
            callout_text = f"⚡ PIK GOE: {curr_max_goe:,}".replace(",", " ")
            cb_w = 125
            cb_h = 24
            cb_x1 = max(plot_x1 + 10, min(plot_x2 - cb_w - 10, pk_x - cb_w // 2))
            cb_y1 = max(plot_y1 + 5, pk_y - 36)
            draw.rounded_rectangle(
                [cb_x1, cb_y1, cb_x1 + cb_w, cb_y1 + cb_h],
                radius=4,
                fill=(255, 24, 36),
            )
            draw.text(
                (cb_x1 + cb_w // 2, cb_y1 + cb_h // 2),
                callout_text,
                fill=(255, 255, 255),
                font=font_callout,
                anchor="mm",
            )
            draw.line(
                [(pk_x, pk_y), (pk_x, cb_y1 + cb_h)],
                fill=(255, 24, 36),
                width=2,
            )

    # Time labels
    step = max(1, num_pts // 5)
    time_indices = list(range(0, num_pts, step))
    if num_pts - 1 not in time_indices:
        time_indices.append(num_pts - 1)

    for t_idx in time_indices:
        pt = history_points[t_idx]
        ts = pt.get("timestamp", "").split()[-1]
        tx = (
            plot_x1 if num_pts == 1 else plot_x1 + int((t_idx / (num_pts - 1)) * plot_w)
        )
        draw.text(
            (tx, plot_y2 + 18),
            ts,
            fill=(160, 160, 170),
            font=font_axis,
            anchor="mm",
        )

    # Footer - GoE Roster Pipes & #bunkier (Strictly NO sponsors, NO 'oficjalny system')
    roster_pipes = (
        "DEJF | CZARNYPIOTRUS | BIALITO | MAJUTEK | PEDRO | MAGVAYER | JASKIER"
    )
    draw.text(
        (width // 2, 1220),
        roster_pipes,
        fill=(255, 255, 255),
        font=font_footer_pipes,
        anchor="mm",
    )

    bunkier_w = 140
    bunkier_h = 32
    bx = (width - bunkier_w) // 2
    by = 1248
    draw.rounded_rectangle(
        [bx, by, bx + bunkier_w, by + bunkier_h],
        radius=6,
        fill=(255, 0, 51),
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
        "Statystyki widowni Co-stream GoE • Worlds 2026",
        fill=(140, 140, 150),
        font=font_system_note,
        anchor="mm",
    )

    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    out_goe = create_summary_card(
        "infographsbot/goe_summary.png", mode="GOE", filter_bots=True
    )
    out_comp = create_summary_card(
        "infographsbot/stream_summary.png", mode="COMPARISON", filter_bots=True
    )
    out_goe_raw = create_summary_card(
        "infographsbot/goe_summary_raw.png", mode="GOE", filter_bots=False
    )
    out_comp_raw = create_summary_card(
        "infographsbot/stream_summary_raw.png", mode="COMPARISON", filter_bots=False
    )
    print(f"GoE summary card (clean): {out_goe}")
    print(f"Comparison summary card (clean): {out_comp}")
    print(f"GoE summary card (raw): {out_goe_raw}")
    print(f"Comparison summary card (raw): {out_comp_raw}")
