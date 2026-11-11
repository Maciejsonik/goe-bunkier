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
        f" • {stats.get('start_time', '')} — {stats.get('end_time', '')}"
        if stats.get("start_time")
        else " • Oczekiwanie na start transmisji"
    )
    if mode == "GOE":
        sub_title_text = f"w Kieleckim bunkrze • Widownia Co-stream GoE{time_range}"
    elif mode == "CAMPS":
        sub_title_text = (
            f"w Kieleckim bunkrze • GoE vs Nervarien vs Tobiasz{time_range}"
        )
    else:
        sub_title_text = f"w Kieleckim bunkrze vs Nervarien • Porównanie{time_range}"
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

        goe_peak_sub = (
            f"ŁĄCZNIE O {stats['goe_peak_time']}"
            if stats.get("goe_peak_time")
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
        goe_peak_sub = (
            f"ŁĄCZNIE O {stats['goe_peak_time']}"
            if stats.get("goe_peak_time")
            else "NAJWYŻSZA WIDOWNIA"
        )
        nerva_peak_sub = (
            f"TWITCH + YT O {stats['nerva_peak_time']}"
            if stats.get("nerva_peak_time")
            else "TWITCH + YOUTUBE"
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
                (59, 130, 246),
                nerva_peak_sub,
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
                (59, 130, 246),
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
                (59, 130, 246),
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

    # Legend depending on mode (right-aligned, vertically centered on swatches)
    if mode == "GOE":
        legend_items = [
            ("GoE Łącznie", (255, 24, 36)),
            ("YouTube", (239, 68, 68)),
            ("Twitch", (145, 70, 255)),
        ]
    elif mode == "CAMPS":
        legend_items = [
            ("GOE", (255, 24, 36)),
            ("NERVARIEN", (59, 130, 246)),
            ("TOBIASZ", (249, 115, 22)),
            ("CO-STREAM", (245, 158, 11)),
        ]
    else:
        legend_items = [
            ("GOE", (255, 24, 36)),
            ("NERVARIEN", (59, 130, 246)),
        ]

    legend_cy = chart_y1 + 25
    cur_lx = chart_x2 - 30
    for lbl, col in reversed(legend_items):
        bbox = font_legend.getbbox(lbl)
        lbl_w = bbox[2] - bbox[0]
        cur_lx -= lbl_w
        draw.text(
            (cur_lx, legend_cy),
            lbl,
            fill=(255, 255, 255),
            font=font_legend,
            anchor="lm",
        )
        swatch_x2 = cur_lx - 8
        swatch_x1 = swatch_x2 - 16
        draw.rectangle(
            [swatch_x1, legend_cy - 8, swatch_x2, legend_cy + 8],
            fill=col,
        )
        cur_lx = swatch_x1 - 24

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

    has_history = bool(history_points)
    num_pts = len(history_points)

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

    def _draw_peak_callout(pk_x: int, pk_y: int, peak_val: int):
        callout_text = f"PIK GOE: {peak_val:,}".replace(",", " ")
        cb_bbox = font_callout.getbbox(callout_text)
        cb_w = (cb_bbox[2] - cb_bbox[0]) + 24
        cb_h = 26
        cb_x1 = max(plot_x1 + 10, min(plot_x2 - cb_w - 10, pk_x - cb_w // 2))
        cb_y1 = max(plot_y1 + 5, pk_y - 38)
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

    if not has_history:
        max_v = 5000
    elif mode == "GOE":
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

    if not has_history:
        cx = (plot_x1 + plot_x2) // 2
        cy = (plot_y1 + plot_y2) // 2
        draw.text(
            (cx, cy - 16),
            "OCZEKIWANIE NA START TRANSMISJI",
            fill=(255, 204, 0),
            font=_get_font(26, bold=True, font_type="rajdhani"),
            anchor="mm",
        )
        draw.text(
            (cx, cy + 18),
            "Wykres pojawi się po zebraniu pierwszych próbek live",
            fill=(170, 170, 185),
            font=_get_font(17, font_type="rajdhani"),
            anchor="mm",
        )
    elif mode == "GOE":
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
            _draw_peak_callout(pk_x, pk_y, curr_max)

    elif mode == "CAMPS":
        # 3 Camps mode: GoE vs Nervarien vs Tobiasz + Nerva Co-stream
        goe_coords = []
        nerva_coords = []
        tobias_coords = []
        costream_coords = []
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
            tv = pt.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0)
            cv = _get_costream_v_pt(pt)

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

        # 1. Co-stream (amber line)
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

        # 3. Nervarien (blue line)
        for i in range(len(nerva_coords) - 1):
            draw.line(
                [nerva_coords[i], nerva_coords[i + 1]], fill=(59, 130, 246), width=3
            )
        for x, y in nerva_coords[:: max(1, num_pts // 30)]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(59, 130, 246))

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
            _draw_peak_callout(pk_x, pk_y, curr_max_goe)

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
                fill=(59, 130, 246),
                width=3,
            )
        for x, y in nerva_coords[:: max(1, num_pts // 30)]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(59, 130, 246))

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
            _draw_peak_callout(pk_x, pk_y, curr_max_goe)

    # Time labels
    if has_history:
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
                plot_x1
                if num_pts == 1
                else plot_x1 + int((t_idx / (num_pts - 1)) * plot_w)
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


def _draw_segmented_bar(
    base_img: Image.Image,
    draw: ImageDraw.Draw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    segments: list[tuple[float, tuple[int, int, int]]],
    radius: int = 6,
):
    """Draws a crisp multi-segment horizontal percentage bar masked to rounded capsule ends."""
    bar_w = x2 - x1
    bar_h = y2 - y1
    if bar_w <= 0 or bar_h <= 0:
        return

    mask = Image.new("L", (bar_w, bar_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, bar_w - 1, bar_h - 1], radius=radius, fill=255
    )

    inner = Image.new("RGB", (bar_w, bar_h), (18, 18, 24))
    d_inner = ImageDraw.Draw(inner)

    tot = sum(max(0.0, float(v)) for v, _ in segments)
    if tot > 0:
        cur_x = 0
        non_zero = [(v, c) for v, c in segments if v > 0]
        for idx, (val, col) in enumerate(non_zero):
            seg_w = (
                (bar_w - cur_x)
                if idx == len(non_zero) - 1
                else max(2, int(round((val / tot) * bar_w)))
            )
            seg_end = min(bar_w, cur_x + seg_w)
            if seg_end > cur_x:
                d_inner.rectangle([cur_x, 0, seg_end, bar_h], fill=col)
            if idx < len(non_zero) - 1 and 0 < seg_end < bar_w:
                d_inner.rectangle(
                    [seg_end - 1, 0, seg_end + 1, bar_h], fill=(10, 10, 14)
                )
            cur_x = seg_end

    base_img.paste(inner, (x1, y1), mask)
    draw.rounded_rectangle(
        [x1, y1, x2, y2], radius=radius, outline=(55, 55, 70), width=1
    )


def _draw_stage_analytics_panel(
    base_img: Image.Image,
    draw: ImageDraw.Draw,
    width: int,
    panel_y: int,
    panel_bottom: int,
    stage: dict,
    data_all: dict,
    stage_id: str,
):
    """Fills extra stage-summary canvas space with market share bar, GoE YT/Twitch split, and records."""
    ms = stage.get("market_share", {})
    total_vh = stage.get("total_watch_hours", 0)

    font_hdr = _get_font(14, bold=True, font_type="rajdhani")
    font_card_hdr = _get_font(15, bold=True, font_type="rajdhani")
    font_lbl = _get_font(14, bold=False, font_type="rajdhani")
    font_val = _get_font(14, bold=True, font_type="rajdhani")

    # 1. Stage-wide 100% Watch-Hours Share Bar
    draw.text(
        (50, panel_y + 9),
        f"ROZKŁAD WIDZOGODZIN ETAPU ({total_vh:,} h):".replace(",", " "),
        fill=(180, 180, 195),
        font=font_hdr,
        anchor="lm",
    )
    draw.text(
        (width - 50, panel_y + 9),
        f"GoE {ms.get('goe', 0.0)}%  •  Nerva {ms.get('nerva', 0.0)}%  •  Tobiasz {ms.get('tobias', 0.0)}%",
        fill=(230, 230, 240),
        font=font_hdr,
        anchor="rm",
    )
    _draw_segmented_bar(
        base_img,
        draw,
        50,
        panel_y + 22,
        width - 50,
        panel_y + 38,
        [
            (ms.get("goe", 0.0), (255, 24, 36)),
            (ms.get("nerva", 0.0), (59, 130, 246)),
            (ms.get("tobias", 0.0), (249, 115, 22)),
        ],
        radius=6,
    )

    card_y1 = panel_y + 48
    card_h = panel_bottom - card_y1
    tall = card_h >= 200
    card_w = 480
    left_x, right_x = 50, 550

    for cx, outline_col in ((left_x, (85, 30, 42)), (right_x, (40, 65, 85))):
        draw.rounded_rectangle(
            [cx, card_y1, cx + card_w, panel_bottom],
            radius=8,
            fill=(16, 16, 20),
            outline=outline_col,
            width=1,
        )

    # 2. Left Card: Bunkier GoE YouTube vs Twitch Split + Total On-Air Hours
    gp = stage.get("goe_platforms", {})
    yt_vh = gp.get("yt_watch_hours", 0)
    tw_vh = gp.get("tw_watch_hours", 0)
    yt_pk = gp.get("yt_peak", 0)
    tw_pk = gp.get("tw_peak", 0)
    yt_share = gp.get("yt_share", 0.0)
    tw_share = gp.get("tw_share", 0.0)

    draw.text(
        (left_x + 16, card_y1 + 20),
        "BUNKIER GOE: YOUTUBE vs TWITCH",
        fill=(255, 75, 90),
        font=font_card_hdr,
        anchor="lm",
    )

    plat_rows = [
        (
            "YouTube (@gadaja_):",
            f"{yt_vh:,} h ({yt_share}%)  •  pik {yt_pk:,}".replace(",", " "),
            (239, 68, 68),
            (255, 110, 120),
        ),
        (
            "Twitch (GoE_stream):",
            f"{tw_vh:,} h ({tw_share}%)  •  pik {tw_pk:,}".replace(",", " "),
            (145, 70, 255),
            (192, 132, 252),
        ),
    ]
    for idx, (pl_lbl, pl_val, dot_col, val_col) in enumerate(plat_rows):
        ry = card_y1 + (52 if tall else 49) + idx * (28 if tall else 25)
        draw.ellipse([left_x + 16, ry - 4, left_x + 24, ry + 4], fill=dot_col)
        draw.text(
            (left_x + 32, ry),
            pl_lbl,
            fill=(220, 220, 230),
            font=font_lbl,
            anchor="lm",
        )
        draw.text(
            (left_x + card_w - 16, ry),
            pl_val,
            fill=val_col,
            font=font_val,
            anchor="rm",
        )

    bar_y1 = card_y1 + (104 if tall else 96)
    _draw_segmented_bar(
        base_img,
        draw,
        left_x + 16,
        bar_y1,
        left_x + card_w - 16,
        bar_y1 + 12,
        [(yt_share, (239, 68, 68)), (tw_share, (145, 70, 255))],
        radius=5,
    )

    div_y = bar_y1 + (26 if tall else 22)
    draw.line(
        [(left_x + 16, div_y), (left_x + card_w - 16, div_y)],
        fill=(38, 38, 48),
        width=1,
    )

    dur_lbl_y = div_y + (18 if tall else 15)
    draw.text(
        (left_x + 16, dur_lbl_y),
        "CZAS NA ANTENIE W ETAPIE (OKNO LIVE):",
        fill=(255, 204, 0),
        font=_get_font(13, bold=True, font_type="rajdhani"),
        anchor="lm",
    )

    dur_val_y = dur_lbl_y + (24 if tall else 21)
    dur_items = [
        (f"GoE: {stage.get('goe', {}).get('duration_hours', 0)} h", (255, 75, 90)),
        (f"Nerva: {stage.get('nerva', {}).get('duration_hours', 0)} h", (96, 165, 250)),
        (
            f"Tobiasz: {stage.get('tobias', {}).get('duration_hours', 0)} h",
            (251, 146, 60),
        ),
    ]
    for d_idx, (d_str, d_col) in enumerate(dur_items):
        dx = left_x + 16 + d_idx * 152
        draw.text((dx, dur_val_y), d_str, fill=d_col, font=font_val, anchor="lm")

    played_matches = [
        m for m in stage.get("matches", []) if m.get("points_count", 0) > 0
    ]
    if tall and played_matches:
        longest_goe = max(
            played_matches, key=lambda m: m.get("goe", {}).get("duration_hours", 0)
        )
        draw.text(
            (left_x + 16, panel_bottom - 20),
            f"Najdłuższe studio GoE: {longest_goe['name']} ({longest_goe['goe'].get('duration_str', '')})",
            fill=(165, 165, 180),
            font=_get_font(13, bold=False, font_type="rajdhani"),
            anchor="lm",
        )

    # 3. Right Card: Stage Records & Quarterfinals->Semifinals Progression
    played_cnt = max(1, len(played_matches))
    avg_vh_match = round(total_vh / played_cnt)

    best_share_m = (
        max(
            played_matches,
            key=lambda m: m.get("market_share", {}).get("goe", 0.0),
        )
        if played_matches
        else None
    )
    best_goe_m = (
        max(played_matches, key=lambda m: m.get("goe", {}).get("peak", 0))
        if played_matches
        else None
    )

    q_stage = data_all.get("stages", {}).get("quarters", {})
    if stage_id == "semis" and q_stage.get("matches_count", 0) > 0:
        draw.text(
            (right_x + 16, card_y1 + 20),
            "DYNAMIKA (VS ĆWIERĆFINAŁY) & FINAŁ",
            fill=(0, 229, 255),
            font=font_card_hdr,
            anchor="lm",
        )
        q_avg_match = round(
            q_stage["total_watch_hours"] / max(1, q_stage["matches_count"])
        )
        d_vh_pct = (
            round(((avg_vh_match - q_avg_match) / q_avg_match) * 100)
            if q_avg_match > 0
            else 0
        )
        q_pk = q_stage.get("total_scene_peak", 0)
        s_pk = stage.get("total_scene_peak", 0)
        d_pk_pct = round(((s_pk - q_pk) / q_pk) * 100) if q_pk > 0 else 0

        kv_rows = [
            (
                "Watch-time / mecz BO5:",
                f"{avg_vh_match:,} h ({d_vh_pct:+}%)".replace(",", " "),
                (74, 222, 128) if d_vh_pct >= 0 else (255, 95, 110),
            ),
            (
                "Rekord sceny etapu:",
                f"{s_pk:,} ({d_pk_pct:+}%)".replace(",", " "),
                (0, 229, 255),
            ),
            (
                "Rekord Bunkra GoE:",
                (
                    f"{best_goe_m['goe']['peak']:,} ({best_goe_m['match_short']})".replace(
                        ",", " "
                    )
                    if best_goe_m
                    else "--"
                ),
                (255, 95, 110),
            ),
            (
                "Skala telemetryczna:",
                f"{stage.get('total_points', 0):,} próbek pomiarowych".replace(
                    ",", " "
                ),
                (235, 235, 245),
            ),
        ]
        for idx, (klbl, kval, vcol) in enumerate(kv_rows):
            ry = card_y1 + 54 + idx * 29
            draw.text(
                (right_x + 16, ry),
                klbl,
                fill=(180, 180, 195),
                font=font_lbl,
                anchor="lm",
            )
            draw.text(
                (right_x + card_w - 16, ry),
                kval,
                fill=vcol,
                font=font_val,
                anchor="rm",
            )

        finals_stage = data_all.get("stages", {}).get("finals", {})
        finals_match = (
            finals_stage.get("matches", [{}])[0] if finals_stage.get("matches") else {}
        )
        finals_title = finals_match.get("match_short") or "BLG vs Gen.G"
        finals_time = finals_match.get("schedule", {}).get("match_start", "20:00")
        draw.rounded_rectangle(
            [right_x + 16, panel_bottom - 48, right_x + card_w - 16, panel_bottom - 14],
            radius=6,
            fill=(28, 22, 12),
            outline=(180, 140, 20),
            width=1,
        )
        draw.text(
            (right_x + card_w // 2, panel_bottom - 31),
            f"NASTĘPNY ETAP: WIELKI FINAŁ (14.11 • {finals_time}) • {finals_title}",
            fill=(255, 204, 0),
            font=_get_font(14, bold=True, font_type="rajdhani"),
            anchor="mm",
        )
    else:
        draw.text(
            (right_x + 16, card_y1 + 20),
            "REKORDY I BILANS ETAPU",
            fill=(0, 229, 255),
            font=font_card_hdr,
            anchor="lm",
        )
        kv_rows = [
            (
                "Najwyższy udział GoE:",
                (
                    f"{best_share_m['match_short']} ({best_share_m['market_share']['goe']}%)"
                    if best_share_m
                    else "--"
                ),
                (255, 95, 110),
            ),
            (
                "Rekord Bunkra GoE:",
                (
                    f"{best_goe_m['goe']['peak']:,} ({best_goe_m['match_short']})".replace(
                        ",", " "
                    )
                    if best_goe_m
                    else "--"
                ),
                (255, 95, 110),
            ),
            (
                "Rekord całej sceny:",
                f"{stage.get('total_scene_peak', 0):,} ({stage.get('total_scene_peak_match', '')})".replace(
                    ",", " "
                ),
                (0, 229, 255),
            ),
            (
                "Średnio na mecz BO5:",
                f"{avg_vh_match:,} h  •  {stage.get('total_points', 0):,} próbek".replace(
                    ",", " "
                ),
                (235, 235, 245),
            ),
        ]
        for idx, (klbl, kval, vcol) in enumerate(kv_rows):
            ry = card_y1 + 52 + idx * 27
            draw.text(
                (right_x + 16, ry),
                klbl,
                fill=(180, 180, 195),
                font=font_lbl,
                anchor="lm",
            )
            draw.text(
                (right_x + card_w - 16, ry),
                kval,
                fill=vcol,
                font=font_val,
                anchor="rm",
            )


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
    box_h = 108
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
        draw.text((bx + 14, y_boxes + 34), val, fill=col, font=font_stat_val)
        draw.text(
            (bx + 14, y_boxes + 84),
            sub,
            fill=(135, 135, 145),
            font=font_stat_sub,
        )

    # 4. Three Camp Cards (GoE Red, Nervarien Blue, Tobiasz Orange)
    c_y = 325
    c_w = 310
    c_h = 96
    c_xs = [50, 385, 720]

    camps_data = [
        (
            "BUNKIER GOE",
            stage.get("goe", {}),
            (255, 24, 36),
            (255, 75, 90),
        ),
        (
            "NERVARIEN & CO-STREAMY",
            stage.get("nerva", {}),
            (59, 130, 246),
            (96, 165, 250),
        ),
        (
            "TOBIASZ",
            stage.get("tobias", {}),
            (249, 115, 22),
            (251, 146, 60),
        ),
    ]

    font_camp_hdr = _get_font(16, bold=True, font_type="rajdhani")
    font_camp_val = _get_font(15, bold=True, font_type="rajdhani")
    font_camp_sub = _get_font(15, bold=False, font_type="rajdhani")

    for (cname, cstats, ccolor, txt_col), cx in zip(camps_data, c_xs):
        draw.rounded_rectangle(
            [cx, c_y, cx + c_w, c_y + c_h],
            radius=8,
            fill=(18, 18, 22),
            outline=ccolor,
            width=2,
        )
        draw.ellipse([cx + 12, c_y + 15, cx + 22, c_y + 25], fill=ccolor)
        draw.text(
            (cx + 28, c_y + 20),
            cname,
            fill=txt_col,
            font=font_camp_hdr,
            anchor="lm",
        )
        peak_str = f"Pik: {cstats.get('peak', 0):,}".replace(",", " ")
        avg_str = f"Śr. live: {cstats.get('live_avg', 0):,}".replace(",", " ")
        vh_str = f"Watch: {cstats.get('watch_hours', 0):,}".replace(",", " ") + " h"
        share_str = f"Udział: {cstats.get('share', 0.0)}%"

        draw.text(
            (cx + 14, c_y + 49),
            peak_str,
            fill=(255, 255, 255),
            font=font_camp_val,
            anchor="lm",
        )
        draw.text(
            (cx + 158, c_y + 49),
            avg_str,
            fill=(200, 200, 210),
            font=font_camp_sub,
            anchor="lm",
        )
        draw.text(
            (cx + 14, c_y + 74),
            vh_str,
            fill=(0, 229, 255),
            font=font_camp_val,
            anchor="lm",
        )
        draw.text(
            (cx + 158, c_y + 74),
            share_str,
            fill=txt_col,
            font=font_camp_val,
            anchor="lm",
        )

    # 5. Match-by-Match Visual Rows + Dynamic Analytics Panel
    matches = stage.get("matches", [])
    row_y_start = 454
    available_h = 640
    show_analytics_panel = len(matches) <= 4
    is_rich_row = len(matches) <= 2

    if is_rich_row:
        row_h = 176
        compact = False
        card_inner_h = row_h - 10
        panel_y = 814
    elif show_analytics_panel:
        row_h = 104
        compact = False
        card_inner_h = row_h - 8
        panel_y = 876
    else:
        row_h = min(108, available_h // max(1, len(matches)))
        compact = row_h < 96
        card_inner_h = row_h - 8
        panel_y = 0

    draw.text(
        (50, 438),
        "ZESTAWIENIE MECZÓW (SZCZYTY I CZAS TRWANIA):",
        fill=(180, 180, 190),
        font=_get_font(14, bold=True, font_type="rajdhani"),
        anchor="lm",
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

    font_row_title = _get_font(
        19 if is_rich_row else (16 if compact else 18), bold=True, font_type="anton"
    )
    font_row_peak = _get_font(
        16 if is_rich_row else 15, bold=True, font_type="rajdhani"
    )
    font_bar_lbl = _get_font(13 if compact else 14, bold=True, font_type="rajdhani")
    font_bar_right = _get_font(13 if compact else 14, bold=False, font_type="rajdhani")
    font_rich_sub = _get_font(14, bold=True, font_type="rajdhani")

    for i, m in enumerate(matches):
        my = row_y_start + i * row_h
        m_w = width - 100
        is_upcoming_row = m.get("points_count", 0) == 0
        row_outline = (180, 140, 20) if is_upcoming_row else (40, 40, 50)
        draw.rounded_rectangle(
            [50, my, 50 + m_w, my + card_inner_h],
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
        title_cy = my + (20 if (is_upcoming_row or is_rich_row) else 16)
        draw.text(
            (65, title_cy),
            title_line,
            fill=(255, 204, 0) if is_upcoming_row else (255, 255, 255),
            font=font_row_title,
            anchor="lm",
        )

        if is_upcoming_row:
            sched_match = m.get("schedule", {}).get("match_start", "20:00")
            sched_goe = m.get("schedule", {}).get("goe_start", "19:00")
            draw.text(
                (width - 65, title_cy),
                f"NADCHODZĄCY ({sched_match} CET)",
                fill=(255, 204, 0),
                font=font_row_peak,
                anchor="rm",
            )
            draw.text(
                (65, my + card_inner_h - 22),
                f"Start studia GoE: ~{sched_goe} CET  •  Ceremonia Otwarcia i Mecz: {sched_match} CET  •  Barclays Center",
                fill=(180, 180, 195),
                font=_get_font(15, font_type="rajdhani"),
                anchor="lm",
            )
            continue

        pk_time = m.get("total_peak_time", "")
        if show_analytics_panel and pk_time and pk_time != "--":
            tot_p_str = f"Pik sceny: {m['total_peak']:,} ({pk_time})".replace(",", " ")
        else:
            tot_p_str = f"Pik meczu: {m['total_peak']:,}".replace(",", " ")
        draw.text(
            (width - 65, title_cy),
            tot_p_str,
            fill=(0, 229, 255),
            font=font_row_peak,
            anchor="rm",
        )

        # 3 Comparative Progress Bars inside the row (GoE Red, Nerva Blue, Tobiasz Orange)
        bar_x = 65
        bar_max_w = 400
        bar_half_h = 5 if compact else 6
        bar_cy_start = my + (48 if is_rich_row else (38 if compact else 42))
        spacing = 20 if is_rich_row else (15 if compact else 18)

        bar_specs = [
            ("GoE", m["goe"], (255, 24, 36), (255, 75, 90), None),
            ("Nerva", m["nerva"], (59, 130, 246), (96, 165, 250), None),
            (
                "Tobiasz",
                m["tobias"],
                (249, 115, 22),
                (251, 146, 60),
                "Tobiasz: Offline (Brak transmisji)",
            ),
        ]

        for b_idx, (b_lbl, b_stats, b_col, txt_col, empty_lbl) in enumerate(bar_specs):
            cy = bar_cy_start + b_idx * spacing
            pk_val = b_stats["peak"]
            if pk_val <= 0 and empty_lbl:
                draw.text(
                    (bar_x, cy),
                    empty_lbl,
                    fill=(125, 125, 138),
                    font=font_bar_lbl,
                    anchor="lm",
                )
                continue

            bw = max(2, int((pk_val / max_p) * bar_max_w)) if pk_val > 0 else 0
            if bw > 0:
                draw.rectangle(
                    [bar_x, cy - bar_half_h, bar_x + bw, cy + bar_half_h],
                    fill=b_col,
                )
            draw.text(
                (bar_x + bw + (8 if bw > 0 else 0), cy),
                f"{b_lbl}: {pk_val:,}".replace(",", " "),
                fill=txt_col,
                font=font_bar_lbl,
                anchor="lm",
            )
            dur_suffix = (
                f" ({b_stats['duration_str']})"
                if is_rich_row and b_stats.get("duration_str")
                else ""
            )
            right_txt = (
                f"{b_lbl} śr: {b_stats['live_avg']:,} | {b_stats['watch_hours']:,}h{dur_suffix}"
            ).replace(",", " ")
            draw.text(
                (width - 65, cy),
                right_txt,
                fill=(200, 200, 210),
                font=font_bar_right,
                anchor="rm",
            )

        if is_rich_row:
            draw.line(
                [(65, my + 108), (width - 65, my + 108)],
                fill=(34, 34, 44),
                width=1,
            )
            ms_m = m.get("market_share", {})
            _draw_segmented_bar(
                img,
                draw,
                65,
                my + 118,
                width - 65,
                my + 129,
                [
                    (ms_m.get("goe", 0.0), (255, 24, 36)),
                    (ms_m.get("nerva", 0.0), (59, 130, 246)),
                    (ms_m.get("tobias", 0.0), (249, 115, 22)),
                ],
                radius=5,
            )
            yt_m_vh = m.get("goe_yt", {}).get("watch_hours", 0)
            tw_m_vh = m.get("goe_tw", {}).get("watch_hours", 0)
            tot_plat_m = yt_m_vh + tw_m_vh
            yt_m_pct = round((yt_m_vh / tot_plat_m) * 100, 1) if tot_plat_m > 0 else 0.0
            tw_m_pct = round(100.0 - yt_m_pct, 1) if tot_plat_m > 0 else 0.0
            draw.text(
                (65, my + 146),
                f"Udział meczu: GoE {ms_m.get('goe', 0.0)}%  •  Nerva {ms_m.get('nerva', 0.0)}%  •  Tobiasz {ms_m.get('tobias', 0.0)}%",
                fill=(210, 210, 222),
                font=font_rich_sub,
                anchor="lm",
            )
            draw.text(
                (width - 65, my + 146),
                f"Bunkier YT vs TW: {yt_m_vh:,}h ({yt_m_pct}%) vs {tw_m_vh:,}h ({tw_m_pct}%)".replace(
                    ",", " "
                ),
                fill=(185, 185, 200),
                font=font_rich_sub,
                anchor="rm",
            )

    if show_analytics_panel:
        _draw_stage_analytics_panel(
            img,
            draw,
            width,
            panel_y,
            1094,
            stage,
            data_all,
            stage_id,
        )

    # 6. Disclaimers Box
    disc_y = 1105
    draw.rounded_rectangle(
        [50, disc_y, width - 50, disc_y + 86],
        radius=6,
        fill=(14, 14, 18),
        outline=(50, 50, 60),
        width=1,
    )
    draw.text(
        (65, disc_y + 17),
        "ADNOTACJE METODOLOGICZNE & RAPORT DANYCH:",
        fill=(255, 204, 0),
        font=_get_font(13, bold=True, font_type="rajdhani"),
        anchor="lm",
    )
    disc_lines = [
        "• Dzień 1: Oczyszczono 2 fale viewbotów YT (GoE); brak streamu Tobiasza; opóźnione wykrycie co-streamu Damiana.",
        "• Dni 2-6: Wygładzono chwilowe błędy API YouTube; Dzień 3 przycięty o 02:11 (koniec meczu).",
        "• 'True Live Window' + całkowanie czasem (metoda trapezów): dokładne widzogodziny bez dublowania próbek.",
    ]
    for d_idx, dline in enumerate(disc_lines):
        draw.text(
            (65, disc_y + 37 + d_idx * 18),
            dline,
            fill=(160, 160, 175),
            font=_get_font(12, font_type="rajdhani"),
            anchor="lm",
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
