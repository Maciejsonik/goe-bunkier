"""Generates post-stream line chart infographics in GoE aesthetic: GoE-only or Comparison (1080x1350)."""

import os
from PIL import Image, ImageDraw, ImageFont

from config import get_active_day_id, get_known_stream_ids
from db import (
    extract_goe_yt_viewers,
    filter_bot_attacks,
    get_detailed_history,
    get_history,
    get_summary_stats,
)
from generate_card import (
    _get_font,
    draw_goe_background,
    draw_slanted_text,
    draw_top_emblem,
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
        active_day = get_active_day_id()
        day_hist_path = os.path.join(
            os.path.dirname(__file__), f"history_{active_day}.json"
        )
        if os.path.exists(day_hist_path):
            try:
                import json

                with open(day_hist_path, "r", encoding="utf-8") as f:
                    raw_pts = json.load(f)
            except Exception:
                raw_pts = []
        else:
            raw_pts = get_detailed_history(limit=5000, day_id=active_day)
        if not raw_pts:
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
    font_sub_title = _get_font(20, font_type="rajdhani")
    font_stat_val = _get_font(42, font_type="anton")
    font_stat_lbl = _get_font(15, bold=True, font_type="rajdhani")
    font_stat_sub = _get_font(13, bold=True, font_type="rajdhani")
    font_axis = _get_font(14, bold=False)
    font_legend = _get_font(18, font_type="rajdhani")
    font_callout = _get_font(14, font_type="rajdhani")
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(14, font_type="rajdhani")

    # Top Emblem (Crisp vector microphone icon + WORLDS 2026 text)
    draw_top_emblem(draw, width, 48, "WORLDS 2026", font_top_emblem)

    # Slanted Main Title
    if mode == "GOE":
        title_text = "CO-STREAM GOE"
    elif mode == "CAMPS":
        title_text = "STARCIE 3 OBOZÓW"
    else:
        title_text = "GOE vs NERVARIEN"

    draw_slanted_text(
        img,
        title_text,
        font_main_title,
        (255, 0, 51),
        (width // 2, 112),
        slant_k=0.20,
    )

    time_range = (
        f"{stats.get('start_time', '')} — {stats.get('end_time', '')}"
        if stats.get("start_time")
        else ""
    )
    if mode == "GOE":
        sub_title_text = f"w Kieleckim bunkrze • Widownia Co-stream GoE • {time_range}"
    elif mode == "CAMPS":
        sub_title_text = (
            f"w Kieleckim bunkrze • GoE vs Nervarien vs Tobiasz • {time_range}"
        )
    else:
        sub_title_text = f"w Kieleckim bunkrze vs Nervarien • Porównanie • {time_range}"
    draw.text(
        (width // 2, 182),
        sub_title_text,
        fill=(255, 255, 255),
        font=font_sub_title,
        anchor="mm",
    )

    box_w = 226
    box_h = 130
    y_boxes = 220
    x_positions = [50, 301, 553, 804]

    # Stats setup
    if mode == "GOE":
        known_ids = get_known_stream_ids()

        # Calculate GoE peak YT and peak Twitch dynamically
        peak_yt = max(
            (
                extract_goe_yt_viewers(
                    p.get("streams", {}), filter_bots=filter_bots, known_ids=known_ids
                )[0]
                for p in history_points
            ),
            default=0,
        )
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
                "W TRAKCIE STREAMU",
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
    elif mode == "CAMPS":
        peak_tobias = max(
            (
                p.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
                for p in history_points
            ),
            default=0,
        )

        def _get_costream_v(p):
            cs_vals = [
                s.get("viewers", 0)
                for sid, s in p.get("streams", {}).items()
                if sid != "ttobias_lol"
                and (
                    s.get("is_costream")
                    or s.get("is_curiosity")
                    or sid
                    in (
                        "woX6jXefVdw",
                        "N3i_DQlKL_U",
                        "d97hINx-EHU",
                        "f4jsbC6bgNc",
                        "aD1nB7lMtoY",
                    )
                )
            ]
            return max(cs_vals, default=0)

        peak_costream = max((_get_costream_v(p) for p in history_points), default=0)

        stat_items = [
            (
                "PIK GOE",
                f"{stats['goe_peak']:,}".replace(",", " "),
                (255, 24, 36),
                f"ŁĄCZNIE O {stats.get('goe_peak_time', '')}",
            ),
            (
                "PIK NERVA",
                f"{stats['nerva_peak']:,}".replace(",", " "),
                (255, 255, 255),
                f"TWITCH + YT O {stats.get('nerva_peak_time', '')}",
            ),
            (
                "PIK TOBIASZ",
                f"{peak_tobias:,}".replace(",", " "),
                (249, 115, 22),
                "TWITCH • TTOBIAS_LOL",
            ),
            (
                "NERVA CO-STREAM",
                f"{peak_costream:,}".replace(",", " "),
                (245, 158, 11),
                "YOUTUBE • DAMIAN",
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
                "W TRAKCIE STREAMU",
            ),
            (
                "ŚREDNIA NERVA",
                f"{stats['nerva_avg']:,}".replace(",", " "),
                (255, 255, 255),
                "W TRAKCIE STREAMU",
            ),
        ]

    font_stat_val = _get_font(42, font_type="anton")
    font_stat_lbl = _get_font(15, bold=True, font_type="rajdhani")
    font_stat_sub = _get_font(13, bold=True, font_type="rajdhani")

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
            (bx + 16, y_boxes + 14),
            label,
            fill=(180, 180, 190),
            font=font_stat_lbl,
        )
        draw.text((bx + 16, y_boxes + 38), val, fill=color, font=font_stat_val)
        draw.text(
            (bx + 16, y_boxes + 98),
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
    elif mode == "CAMPS":
        # 4 legend items: GOE, NERVA, TOBIASZ, CO-STREAM
        draw.rectangle(
            [chart_x2 - 460, chart_y1 + 14, chart_x2 - 444, chart_y1 + 30],
            fill=(255, 24, 36),
        )
        draw.text(
            (chart_x2 - 435, chart_y1 + 14),
            "GOE",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 370, chart_y1 + 14, chart_x2 - 354, chart_y1 + 30],
            fill=(255, 255, 255),
        )
        draw.text(
            (chart_x2 - 345, chart_y1 + 14),
            "NERVARIEN",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 230, chart_y1 + 14, chart_x2 - 214, chart_y1 + 30],
            fill=(249, 115, 22),
        )
        draw.text(
            (chart_x2 - 205, chart_y1 + 14),
            "TOBIASZ",
            fill=(255, 255, 255),
            font=font_legend,
        )

        draw.rectangle(
            [chart_x2 - 110, chart_y1 + 14, chart_x2 - 94, chart_y1 + 30],
            fill=(245, 158, 11),
        )
        draw.text(
            (chart_x2 - 85, chart_y1 + 14),
            "CO-STREAM",
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
    elif mode == "CAMPS":

        def _get_costream_v_pt(p):
            cs_vals = [
                s.get("viewers", 0)
                for sid, s in p.get("streams", {}).items()
                if sid != "ttobias_lol"
                and (
                    s.get("is_costream")
                    or s.get("is_curiosity")
                    or sid
                    in (
                        "woX6jXefVdw",
                        "N3i_DQlKL_U",
                        "d97hINx-EHU",
                        "f4jsbC6bgNc",
                        "aD1nB7lMtoY",
                    )
                )
            ]
            return max(cs_vals, default=0)

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
            max(
                (
                    p.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
                    for p in history_points
                ),
                default=0,
            ),
            max((_get_costream_v_pt(p) for p in history_points), default=0),
            100,
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
        known_ids = get_known_stream_ids()

        for idx, pt in enumerate(history_points):
            x = (
                plot_x1
                if num_pts == 1
                else plot_x1 + int((idx / (num_pts - 1)) * plot_w)
            )
            streams_map = pt.get("streams", {})
            tw_s = streams_map.get("goe_stream", {})
            yt_v, _ = extract_goe_yt_viewers(
                streams_map, filter_bots=filter_bots, known_ids=known_ids
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

    elif mode == "CAMPS":
        # 3 Camps mode: GoE vs Nervarien vs Tobiasz + Nerva Co-stream
        goe_coords = []
        nerva_coords = []
        tobias_coords = []
        costream_coords = []
        max_goe_idx = 0
        curr_max_goe = -1

        def _get_cs_v(p):
            cs_vals = [
                s.get("viewers", 0)
                for sid, s in p.get("streams", {}).items()
                if sid != "ttobias_lol"
                and (
                    s.get("is_costream")
                    or s.get("is_curiosity")
                    or sid
                    in (
                        "woX6jXefVdw",
                        "N3i_DQlKL_U",
                        "d97hINx-EHU",
                        "f4jsbC6bgNc",
                        "aD1nB7lMtoY",
                    )
                )
            ]
            return max(cs_vals, default=0)

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
            tv = pt.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
            cv = _get_cs_v(pt)

            if gv > curr_max_goe:
                curr_max_goe = gv
                max_goe_idx = idx

            y_goe = plot_y2 - int((gv / max_y) * plot_h)
            y_nerva = plot_y2 - int((nv / max_y) * plot_h)
            y_tobias = plot_y2 - int((tv / max_y) * plot_h)
            y_costream = plot_y2 - int((cv / max_y) * plot_h)

            goe_coords.append((x, y_goe))
            nerva_coords.append((x, y_nerva))
            tobias_coords.append((x, y_tobias))
            costream_coords.append((x, y_costream))

        # Fill GoE
        if len(goe_coords) >= 2:
            fill_poly = [(plot_x1, plot_y2)] + goe_coords + [(plot_x2, plot_y2)]
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon(fill_poly, fill=(255, 24, 36, 40))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        # 1. Co-stream (yellow line)
        for i in range(len(costream_coords) - 1):
            draw.line(
                [costream_coords[i], costream_coords[i + 1]],
                fill=(245, 158, 11),
                width=2,
            )

        # 2. Tobiasz (orange line)
        for i in range(len(tobias_coords) - 1):
            draw.line(
                [tobias_coords[i], tobias_coords[i + 1]], fill=(249, 115, 22), width=3
            )
        for x, y in tobias_coords[:: max(1, num_pts // 30)]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(249, 115, 22))

        # 3. Nervarien (white line)
        for i in range(len(nerva_coords) - 1):
            draw.line(
                [nerva_coords[i], nerva_coords[i + 1]], fill=(255, 255, 255), width=3
            )
        for x, y in nerva_coords[:: max(1, num_pts // 30)]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255))

        # 4. GoE (red line)
        for i in range(len(goe_coords) - 1):
            draw.line([goe_coords[i], goe_coords[i + 1]], fill=(255, 24, 36), width=4)
        for x, y in goe_coords[:: max(1, num_pts // 30)]:
            draw.ellipse(
                [x - 4, y - 4, x + 4, y + 4],
                fill=(255, 24, 36),
                outline=(255, 255, 255),
                width=2,
            )

        # Peak GoE Callout
        if goe_coords and curr_max_goe > 0:
            pk_x, pk_y = goe_coords[max_goe_idx]
            callout_text = f"⚡ PIK GOE: {curr_max_goe:,}".replace(",", " ")
            cb_w = 125
            cb_h = 24
            cb_x1 = max(plot_x1 + 10, min(plot_x2 - cb_w - 10, pk_x - cb_w // 2))
            cb_y1 = max(plot_y1 + 5, pk_y - 36)
            draw.rounded_rectangle(
                [cb_x1, cb_y1, cb_x1 + cb_w, cb_y1 + cb_h], radius=4, fill=(255, 24, 36)
            )
            draw.text(
                (cb_x1 + cb_w // 2, cb_y1 + cb_h // 2),
                callout_text,
                fill=(255, 255, 255),
                font=font_callout,
                anchor="mm",
            )
            draw.line([(pk_x, pk_y), (pk_x, cb_y1 + cb_h)], fill=(255, 24, 36), width=2)

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
        if len(time_indices) > 1 and (num_pts - 1) - time_indices[-1] < step // 2:
            time_indices[-1] = num_pts - 1
        else:
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


def create_stage_summary_card(
    stage_id: str = "tournament",
    output_path: str = "tournament_summary.png",
) -> str:
    """Renders a high-impact 1080x1350 summary infographic for a tournament stage
    (Quarters, Semis, or All-Tournament) in GoE Bunkier aesthetics.
    """
    from analytics import generate_tournament_analytics

    data_all = generate_tournament_analytics()
    stage = data_all.get("stages", {}).get(stage_id)
    if not stage:
        stage = data_all.get("stages", {}).get("tournament", {})

    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    font_top_emblem = _get_font(26, bold=True, font_type="rajdhani")
    font_main_title = _get_font(68, font_type="anton")
    font_sub_title = _get_font(20, font_type="rajdhani")
    font_stat_val = _get_font(38, font_type="anton")
    font_stat_lbl = _get_font(15, bold=True, font_type="rajdhani")
    font_stat_sub = _get_font(13, bold=True, font_type="rajdhani")
    font_match_title = _get_font(18, bold=True, font_type="anton")
    font_match_sub = _get_font(14, font_type="rajdhani")
    font_bar_val = _get_font(14, bold=True, font_type="rajdhani")
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(13, font_type="rajdhani")

    # 1. Top Emblem
    draw_top_emblem(draw, width, 48, "WORLDS 2026", font_top_emblem)

    # 2. Slanted Main Title
    played_cnt = stage.get("matches_count", len(stage.get("matches", [])))
    sched_cnt = stage.get("scheduled_matches_count", len(stage.get("matches", [])))
    if stage_id == "quarters":
        title_text = "ĆWIERĆFINAŁY (DNI 1-4)"
        sub_text = "4 mecze BO5 • Bilans oglądalności polskiej sceny"
    elif stage_id == "semis":
        title_text = "PÓŁFINAŁY (DNI 5-6)"
        sub_text = "2 mecze BO5 • Walka o Wielki Finał"
    elif stage_id == "finals":
        title_text = "WIELKI FINAŁ (14.11)"
        sub_text = "Bilibili Gaming vs Gen.G Esports • Mecz o Puchar"
    else:
        title_text = "PODSUMOWANIE TURNIEJU"
        if played_cnt < sched_cnt:
            sub_text = (
                f"{played_cnt}/{sched_cnt} meczów BO5 • Faza pucharowa + Finał (14.11)"
            )
        else:
            sub_text = f"{played_cnt} meczów BO5 • Cała faza pucharowa Worlds 2026"

    draw_slanted_text(
        img,
        title_text,
        font_main_title,
        (255, 0, 51),
        (width // 2, 112),
        slant_k=0.20,
    )

    draw.text(
        (width // 2, 178),
        sub_text,
        fill=(220, 220, 230),
        font=font_sub_title,
        anchor="mm",
    )

    # 3. Top 4 KPI Boxes
    box_w = 226
    box_h = 115
    y_boxes = 205
    x_positions = [50, 301, 553, 804]

    tot_vh = f"{stage.get('total_watch_hours', 0):,}".replace(",", " ") + " h"
    tot_peak = f"{stage.get('total_scene_peak', 0):,}".replace(",", " ")
    goe_share = f"{stage.get('goe', {}).get('share', 0.0)}%"
    goe_avg = f"{stage.get('goe', {}).get('live_avg', 0):,}".replace(",", " ")

    stat_items = [
        (
            "WATCH-TIME SCENY",
            tot_vh,
            (0, 229, 255),
            "ŁĄCZNIE 3 OBOZY",
        ),
        (
            "REKORD SCENY",
            tot_peak,
            (255, 24, 36),
            f"PIK ({stage.get('total_scene_peak_match', '')})",
        ),
        (
            "UDZIAŁ GOE",
            goe_share,
            (255, 24, 36),
            "WIDZOGODZINY BUNKRA",
        ),
        (
            "ŚREDNIA GOE LIVE",
            goe_avg,
            (255, 255, 255),
            "NA ŻYWO W TRAKCIE MECZÓW",
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
            (bx + 14, y_boxes + 12),
            lbl,
            fill=(180, 180, 190),
            font=font_stat_lbl,
        )
        draw.text((bx + 14, y_boxes + 36), val, fill=col, font=font_stat_val)
        draw.text(
            (bx + 14, y_boxes + 86),
            sub,
            fill=(135, 135, 145),
            font=font_stat_sub,
        )

    # 4. Three Camp Cards (GoE, Nervarien, Tobiasz)
    c_y = 335
    c_w = 310
    c_h = 100
    c_xs = [50, 385, 720]

    camps_data = [
        (
            "BUNKIER GOE",
            stage.get("goe", {}),
            (59, 130, 246),
            (20, 30, 50),
        ),
        (
            "NERVARIEN & CO-STREAMY",
            stage.get("nerva", {}),
            (239, 68, 68),
            (50, 20, 25),
        ),
        (
            "TOBIASZ",
            stage.get("tobias", {}),
            (249, 115, 22),
            (50, 30, 15),
        ),
    ]

    for (cname, cstats, ccolor, cbg), cx in zip(camps_data, c_xs):
        draw.rounded_rectangle(
            [cx, c_y, cx + c_w, c_y + c_h],
            radius=8,
            fill=(18, 18, 22),
            outline=ccolor,
            width=2,
        )
        draw.ellipse([cx + 12, c_y + 15, cx + 22, c_y + 25], fill=ccolor)
        draw.text(
            (cx + 28, c_y + 12),
            cname,
            fill=ccolor,
            font=_get_font(16, bold=True, font_type="rajdhani"),
        )
        # Stats inside card
        peak_str = f"Pik: {cstats.get('peak', 0):,}".replace(",", " ")
        avg_str = f"Śr. live: {cstats.get('live_avg', 0):,}".replace(",", " ")
        vh_str = f"Watch: {cstats.get('watch_hours', 0):,}".replace(",", " ") + "h"
        share_str = f"Udział: {cstats.get('share', 0.0)}%"

        draw.text(
            (cx + 12, c_y + 40),
            peak_str,
            fill=(255, 255, 255),
            font=_get_font(15, bold=True, font_type="rajdhani"),
        )
        draw.text(
            (cx + 160, c_y + 40),
            avg_str,
            fill=(200, 200, 210),
            font=_get_font(15, bold=False, font_type="rajdhani"),
        )
        draw.text(
            (cx + 12, c_y + 68),
            vh_str,
            fill=(0, 229, 255),
            font=_get_font(15, bold=True, font_type="rajdhani"),
        )
        draw.text(
            (cx + 160, c_y + 68),
            share_str,
            fill=ccolor,
            font=_get_font(15, bold=True, font_type="rajdhani"),
        )

    # 5. Match-by-Match Visual Rows
    matches = stage.get("matches", [])
    row_y_start = 455
    available_h = 635
    row_h = min(98, available_h // max(1, len(matches)))

    draw.text(
        (50, row_y_start - 18),
        "ZESTAWIENIE MECZÓW (SZCZYTY I CZAS TRWANIA):",
        fill=(180, 180, 190),
        font=_get_font(14, bold=True, font_type="rajdhani"),
    )

    max_p = max(
        (
            max(
                m["goe"]["peak"],
                m["nerva"]["peak"],
                m["tobias"]["peak"],
                1,
            )
            for m in matches
        ),
        default=10000,
    )

    for i, m in enumerate(matches):
        my = row_y_start + i * row_h
        m_w = width - 100
        is_upcoming_row = m.get("points_count", 0) == 0
        row_outline = (180, 140, 20) if is_upcoming_row else (40, 40, 50)
        draw.rounded_rectangle(
            [50, my, 50 + m_w, my + row_h - 8],
            radius=6,
            fill=(16, 16, 20),
            outline=row_outline,
            width=1,
        )

        # Match label and score (omit empty parens for unplayed matches)
        score_str = m.get("score", "")
        title_line = (
            f"{m['name']} • {m['match']} ({score_str})"
            if score_str
            else f"{m['name']} • {m['match']}"
        )
        draw.text(
            (65, my + 8),
            title_line,
            fill=(255, 204, 0) if is_upcoming_row else (255, 255, 255),
            font=font_match_title,
        )

        if is_upcoming_row:
            sched_match = m.get("schedule", {}).get("match_start", "20:00")
            sched_goe = m.get("schedule", {}).get("goe_start", "19:00")
            draw.text(
                (width - 65, my + 8),
                f"NADCHODZĄCY ({sched_match} CET)",
                fill=(255, 204, 0),
                font=_get_font(15, bold=True, font_type="rajdhani"),
                anchor="ra",
            )
            draw.text(
                (65, my + 40),
                f"Start studia GoE: ~{sched_goe} CET  •  Ceremonia Otwarcia i Mecz: {sched_match} CET  •  Barclays Center",
                fill=(180, 180, 195),
                font=_get_font(15, font_type="rajdhani"),
            )
            continue

        tot_p_str = f"Pik meczu: {m['total_peak']:,}".replace(",", " ")
        draw.text(
            (width - 65, my + 8),
            tot_p_str,
            fill=(0, 229, 255),
            font=_get_font(15, bold=True, font_type="rajdhani"),
            anchor="ra",
        )

        # 3 Comparative Progress Bars inside the row
        bar_x = 65
        bar_max_w = 400
        compact = row_h < 95
        bar_y_base = my + (31 if compact else 34)
        bar_h = 10 if compact else 11
        spacing = 14 if compact else 15

        # GoE bar
        gp = m["goe"]["peak"]
        gw = int((gp / max_p) * bar_max_w)
        draw.rectangle(
            [bar_x, bar_y_base, bar_x + gw, bar_y_base + bar_h],
            fill=(59, 130, 246),
        )
        draw.text(
            (bar_x + gw + 8, bar_y_base - 1),
            f"GoE: {gp:,}".replace(",", " "),
            fill=(59, 130, 246),
            font=font_bar_val,
        )

        # Nerva bar
        np_val = m["nerva"]["peak"]
        nw = int((np_val / max_p) * bar_max_w)
        draw.rectangle(
            [bar_x, bar_y_base + spacing, bar_x + nw, bar_y_base + spacing + bar_h],
            fill=(239, 68, 68),
        )
        draw.text(
            (bar_x + nw + 8, bar_y_base + spacing - 1),
            f"Nerva: {np_val:,}".replace(",", " "),
            fill=(239, 68, 68),
            font=font_bar_val,
        )

        # Tobias bar
        tp = m["tobias"]["peak"]
        tw = int((tp / max_p) * bar_max_w)
        if tp > 0:
            draw.rectangle(
                [
                    bar_x,
                    bar_y_base + spacing * 2,
                    bar_x + tw,
                    bar_y_base + spacing * 2 + bar_h,
                ],
                fill=(249, 115, 22),
            )
            draw.text(
                (bar_x + tw + 8, bar_y_base + spacing * 2 - 1),
                f"Tobiasz: {tp:,}".replace(",", " "),
                fill=(249, 115, 22),
                font=font_bar_val,
            )
        else:
            draw.text(
                (bar_x, bar_y_base + spacing * 2 - 1),
                "Tobiasz: Offline (Brak transmisji)",
                fill=(120, 120, 130),
                font=font_bar_val,
            )

        # Right side stats: hours & live average
        right_x = 730
        draw.text(
            (right_x, bar_y_base),
            f"GoE śr: {m['goe']['live_avg']:,} | {m['goe']['watch_hours']:,}h".replace(
                ",", " "
            ),
            fill=(200, 200, 210),
            font=_get_font(13, font_type="rajdhani"),
        )
        draw.text(
            (right_x, bar_y_base + spacing),
            f"Nerva śr: {m['nerva']['live_avg']:,} | {m['nerva']['watch_hours']:,}h".replace(
                ",", " "
            ),
            fill=(200, 200, 210),
            font=_get_font(13, font_type="rajdhani"),
        )
        if tp > 0:
            draw.text(
                (right_x, bar_y_base + spacing * 2),
                f"Tobiasz śr: {m['tobias']['live_avg']:,} | {m['tobias']['watch_hours']:,}h".replace(
                    ",", " "
                ),
                fill=(200, 200, 210),
                font=_get_font(13, font_type="rajdhani"),
            )

    # 6. Disclaimers Box
    disc_y = 1110
    draw.rounded_rectangle(
        [50, disc_y, width - 50, disc_y + 85],
        radius=6,
        fill=(14, 14, 18),
        outline=(50, 50, 60),
        width=1,
    )
    draw.text(
        (65, disc_y + 10),
        "ADNOTACJE METODOLOGICZNE & RAPORT DANYCH:",
        fill=(255, 204, 0),
        font=_get_font(13, bold=True, font_type="rajdhani"),
    )
    disc_lines = [
        "• Dzień 1: Oczyszczono 2 fale viewbotów YT (GoE); brak streamu Tobiasza; opóźnione wykrycie co-streamu Damiana.",
        "• Dni 2-6: Wygładzono chwilowe błędy API YouTube; Dzień 3 przycięty o 02:11 (koniec meczu).",
        "• 'True Live Window' + całkowanie czasem (metoda trapezów): dokładne widzogodziny bez dublowania próbek.",
    ]
    for d_idx, dline in enumerate(disc_lines):
        draw.text(
            (65, disc_y + 28 + d_idx * 17),
            dline,
            fill=(160, 160, 175),
            font=_get_font(12, font_type="rajdhani"),
        )

    # 7. Footer - Roster & Bunkier Badge
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
        "Statystyki widowni Co-stream GoE • Faza Pucharowa Worlds 2026",
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
