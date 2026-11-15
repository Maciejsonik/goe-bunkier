"""Mobile-first, high-readability X (Twitter) carousel generator for #bunkier Worlds 2026.

Splits dense summary data into 6 focused 1080x1350 slides with large typography
(minimum 18-24px body/labels, 54-68px KPIs) so everything is legible on mobile
without zooming.
"""

import json
import math
import os
from PIL import Image, ImageDraw

from config import DAYS_CONFIG
from generate_summary import _draw_segmented_bar, _get_font

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "carousel")

WIDTH = 1080
HEIGHT = 1350
MARGIN = 48

C_BG = (8, 8, 11)
C_CARD = (15, 15, 20)
C_CARD_DARK = (10, 10, 14)
C_BORDER = (46, 46, 58)
C_CRIMSON = (255, 0, 51)
C_GOE = (255, 24, 36)
C_NERVA = (59, 130, 246)
C_TOBIAS = (249, 115, 22)
C_CYAN = (34, 211, 238)
C_GOLD = (250, 204, 21)
C_TEXT = (242, 242, 248)
C_MUTED = (165, 165, 182)


def _fmt_num(val: int) -> str:
    return f"{int(val):,}".replace(",", " ")


def _new_canvas(kicker: str, title: str, subtitle: str, slide_idx: int, total_slides: int = 6):
    """Creates a clean dark-crimson 1080x1350 slide with header and footer."""
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)

    # Subtle diagonal crimson accent lines
    draw.polygon([(0, 0), (420, 0), (0, 320)], fill=(22, 6, 10))
    draw.polygon([(WIDTH, HEIGHT), (WIDTH - 420, HEIGHT), (WIDTH, HEIGHT - 320)], fill=(20, 6, 10))
    draw.line([(0, 4), (WIDTH, 4)], fill=C_CRIMSON, width=8)

    # Header
    draw.text(
        (WIDTH // 2, 54),
        kicker.upper(),
        fill=C_MUTED,
        font=_get_font(22, bold=True, font_type="rajdhani"),
        anchor="mm",
    )
    draw.text(
        (WIDTH // 2, 108),
        title.upper(),
        fill=C_CRIMSON,
        font=_get_font(56, bold=True, font_type="anton"),
        anchor="mm",
    )
    draw.text(
        (WIDTH // 2, 162),
        subtitle,
        fill=C_TEXT,
        font=_get_font(23, bold=False, font_type="rajdhani"),
        anchor="mm",
    )

    # Footer
    footer_y = HEIGHT - 48
    draw.rounded_rectangle(
        [WIDTH // 2 - 110, footer_y - 20, WIDTH // 2 + 110, footer_y + 20],
        radius=8,
        fill=C_CRIMSON,
    )
    draw.text(
        (WIDTH // 2, footer_y),
        "#BUNKIER",
        fill=(255, 255, 255),
        font=_get_font(22, bold=True, font_type="anton"),
        anchor="mm",
    )
    draw.text(
        (MARGIN, footer_y),
        "WORLDS 2026 • STATYSTYKI",
        fill=C_MUTED,
        font=_get_font(18, bold=True, font_type="rajdhani"),
        anchor="lm",
    )
    draw.text(
        (WIDTH - MARGIN, footer_y),
        f"SLAJD {slide_idx}/{total_slides}",
        fill=C_TEXT,
        font=_get_font(20, bold=True, font_type="rajdhani"),
        anchor="rm",
    )
    return img, draw


def _draw_kpi_card(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int, label: str, value: str, sub: str, val_color=C_TEXT, border_color=C_CRIMSON):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14, fill=C_CARD, outline=border_color, width=2)
    draw.text((x1 + 26, y1 + 34), label.upper(), fill=C_MUTED, font=_get_font(21, bold=True, font_type="rajdhani"), anchor="lm")
    draw.text((x1 + 26, y1 + 104), value, fill=val_color, font=_get_font(62, bold=True, font_type="anton"), anchor="lm")
    draw.text((x1 + 26, y2 - 32), sub, fill=C_MUTED, font=_get_font(20, bold=False, font_type="rajdhani"), anchor="lm")


def build_slide_1_tournament_kpi(ta: dict) -> str:
    """Slide 1: Tournament macro KPIs + 3-camp watch-time split."""
    t = ta["stages"]["tournament"]
    ms = t["market_share"]
    gp = t["goe_platforms"]

    img, draw = _new_canvas(
        "WORLDS 2026 • FAZA PUCHAROWA",
        "PODSUMOWANIE TURNIEJU",
        "7 meczów BO5 • Cała polska scena co-streamów",
        1,
    )

    # 2x2 Big KPI Grid (y: 204..636)
    col_w = (WIDTH - 2 * MARGIN - 20) // 2
    row_h = 204
    y1 = 206
    y2 = y1 + row_h + 20
    x_l = MARGIN
    x_r = MARGIN + col_w + 20

    _draw_kpi_card(
        draw, x_l, y1, x_l + col_w, y1 + row_h,
        "WATCH-TIME SCENY",
        f"{_fmt_num(t['total_watch_hours'])} h",
        "Łącznie 3 główne obozy (7× BO5)",
        val_color=C_CYAN,
    )
    _draw_kpi_card(
        draw, x_r, y1, x_r + col_w, y1 + row_h,
        "REKORD WIDOWNI",
        _fmt_num(t["total_scene_peak"]),
        f"Szczyt na finale ({t['total_scene_peak_match']})",
        val_color=C_GOE,
    )
    _draw_kpi_card(
        draw, x_l, y2, x_l + col_w, y2 + row_h,
        "UDZIAŁ #BUNKIER (GOE)",
        f"{ms['goe']:.1f}%",
        f"{_fmt_num(t['goe']['watch_hours'])} h • Średnio {_fmt_num(t['goe']['live_avg'])} live",
        val_color=C_GOE,
    )
    _draw_kpi_card(
        draw, x_r, y2, x_r + col_w, y2 + row_h,
        "BUNKIER: YT vs TWITCH",
        f"{gp['yt_share']:.1f}% YT",
        f"YT {_fmt_num(gp['yt_watch_hours'])} h  •  Twitch {_fmt_num(gp['tw_watch_hours'])} h",
        val_color=C_TEXT,
    )

    # 3-Camp Breakdown Section (y: 676..1250)
    sec_y = 678
    draw.text(
        (MARGIN, sec_y),
        "PODZIAŁ WATCH-TIME MIĘDZY 3 OBOZY:",
        fill=C_TEXT,
        font=_get_font(24, bold=True, font_type="rajdhani"),
        anchor="lm",
    )
    _draw_segmented_bar(
        img, draw, MARGIN, sec_y + 24, WIDTH - MARGIN, sec_y + 52,
        [(ms["nerva"], C_NERVA), (ms["goe"], C_GOE), (ms["tobias"], C_TOBIAS)],
        radius=10,
    )

    camps = [
        ("NERVARIEN & CO-STREAMY", C_NERVA, t["nerva"], ms["nerva"]),
        ("BUNKIER GOE (YT + TWITCH)", C_GOE, t["goe"], ms["goe"]),
        ("TOBIASZ", C_TOBIAS, t["tobias"], ms["tobias"]),
    ]
    cy = sec_y + 76
    card_h = 152
    for name, col, cdata, share in camps:
        draw.rounded_rectangle([MARGIN, cy, WIDTH - MARGIN, cy + card_h], radius=14, fill=C_CARD, outline=col, width=2)
        draw.ellipse([MARGIN + 22, cy + 32, MARGIN + 38, cy + 48], fill=col)
        draw.text((MARGIN + 52, cy + 40), name, fill=col, font=_get_font(25, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text((WIDTH - MARGIN - 24, cy + 40), f"{share:.1f}% SCENY", fill=C_TEXT, font=_get_font(26, bold=True, font_type="rajdhani"), anchor="rm")

        draw.text(
            (MARGIN + 26, cy + 102),
            f"{_fmt_num(cdata['watch_hours'])} h",
            fill=C_CYAN,
            font=_get_font(42, bold=True, font_type="anton"),
            anchor="lm",
        )
        draw.text(
            (WIDTH - MARGIN - 24, cy + 102),
            f"Pik: {_fmt_num(cdata['peak'])}   •   Śr. live: {_fmt_num(cdata['live_avg'])}",
            fill=C_TEXT,
            font=_get_font(24, bold=True, font_type="rajdhani"),
            anchor="rm",
        )
        cy += card_h + 18

    out_path = os.path.join(OUT_DIR, "carousel_1_turniej_kpi.png")
    img.save(out_path)
    return out_path


def build_slide_2_matches(ta: dict) -> str:
    """Slide 2: All 7 BO5 matches with large readable labels and bars."""
    matches = ta["stages"]["tournament"]["matches"]
    img, draw = _new_canvas(
        "WORLDS 2026 • 7 MECZÓW BO5",
        "MECZ PO MECZU",
        "Szczyty widowni (Pik) i udział w każdym dniu fazy pucharowej",
        2,
    )

    y = 204
    card_h = 136
    gap = 14
    max_peak = max(max(m["goe"]["peak"], m["nerva"]["peak"], m["tobias"]["peak"]) for m in matches)
    bar_max_w = 500

    for m in matches:
        draw.rounded_rectangle([MARGIN, y, WIDTH - MARGIN, y + card_h], radius=12, fill=C_CARD, outline=C_BORDER, width=2)
        title = f"{m['name']} • {m['match']} ({m['score']})"
        draw.text((MARGIN + 22, y + 26), title, fill=C_TEXT, font=_get_font(24, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text(
            (WIDTH - MARGIN - 22, y + 26),
            f"Pik sceny: {_fmt_num(m['total_peak'])}",
            fill=C_CYAN,
            font=_get_font(24, bold=True, font_type="rajdhani"),
            anchor="rm",
        )

        # 3 camp peak bars
        bars = [
            ("GoE", m["goe"]["peak"], m["market_share"]["goe"], C_GOE),
            ("Nerva", m["nerva"]["peak"], m["market_share"]["nerva"], C_NERVA),
            ("Tobiasz", m["tobias"]["peak"], m["market_share"]["tobias"], C_TOBIAS),
        ]
        by = y + 54
        for lbl, pk, sh, col in bars:
            bw = max(6, int((pk / max_peak) * bar_max_w)) if pk > 0 else 4
            draw.rounded_rectangle([MARGIN + 22, by, MARGIN + 22 + bw, by + 16], radius=4, fill=col)
            txt = f"{lbl}: {_fmt_num(pk)} ({sh:.1f}%)" if pk > 0 else f"{lbl}: brak streamu"
            draw.text(
                (MARGIN + 32 + bw, by + 8),
                txt,
                fill=C_TEXT if pk > 0 else C_MUTED,
                font=_get_font(19, bold=True, font_type="rajdhani"),
                anchor="lm",
            )
            by += 24

        y += card_h + gap

    out_path = os.path.join(OUT_DIR, "carousel_2_turniej_mecze.png")
    img.save(out_path)
    return out_path


def build_slide_3_finals(ta: dict) -> str:
    """Slide 3: Grand Final 14.11 with tall, crisp 3-camp timeline chart."""
    f_stage = ta["stages"]["finals"]
    ms = f_stage["market_share"]
    m = f_stage["matches"][0]

    img, draw = _new_canvas(
        "WORLDS 2026 • WIELKI FINAŁ (14.11)",
        "BILIBILI GAMING 3 : 1 GEN.G",
        "Przebieg oglądalności 3 obozów oraz bilans meczu o puchar",
        3,
    )

    # Top 3 KPI cards (y: 204..364)
    col_w = (WIDTH - 2 * MARGIN - 32) // 3
    kpis = [
        ("WATCH-TIME FINAŁU", f"{_fmt_num(f_stage['total_watch_hours'])} h", "Łącznie 3 obozy", C_CYAN),
        ("REKORD SCENY", _fmt_num(f_stage["total_scene_peak"]), f"Szczyt o {m['total_peak_time']}", C_GOE),
        ("PIK #BUNKIER", _fmt_num(m["goe"]["peak"]), f"Śr. {_fmt_num(m['goe']['live_avg'])} • {ms['goe']:.1f}%", C_TEXT),
    ]
    for i, (lbl, val, sub, col) in enumerate(kpis):
        kx1 = MARGIN + i * (col_w + 16)
        kx2 = kx1 + col_w
        draw.rounded_rectangle([kx1, 204, kx2, 364], radius=12, fill=C_CARD, outline=C_CRIMSON, width=2)
        draw.text((kx1 + 20, 232), lbl, fill=C_MUTED, font=_get_font(19, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text((kx1 + 20, 286), val, fill=col, font=_get_font(48, bold=True, font_type="anton"), anchor="lm")
        draw.text((kx1 + 20, 338), sub, fill=C_MUTED, font=_get_font(19, bold=False, font_type="rajdhani"), anchor="lm")

    # Tall Timeline Chart Card (y: 386..966)
    chart_top, chart_bot = 386, 966
    draw.rounded_rectangle([MARGIN, chart_top, WIDTH - MARGIN, chart_bot], radius=14, fill=C_CARD, outline=C_BORDER, width=2)
    draw.text((MARGIN + 24, chart_top + 32), "PRZEBIEG OGLĄDALNOŚCI NA ŻYWO", fill=C_TEXT, font=_get_font(23, bold=True, font_type="rajdhani"), anchor="lm")

    legend = [("GOE", C_GOE), ("NERVARIEN", C_NERVA), ("TOBIASZ", C_TOBIAS)]
    cur_lx = WIDTH - MARGIN - 24
    font_leg = _get_font(20, bold=True, font_type="rajdhani")
    for lbl, col in reversed(legend):
        bw = font_leg.getbbox(lbl)[2] - font_leg.getbbox(lbl)[0]
        cur_lx -= bw
        draw.text((cur_lx, chart_top + 32), lbl, fill=C_TEXT, font=font_leg, anchor="lm")
        draw.rectangle([cur_lx - 24, chart_top + 24, cur_lx - 8, chart_top + 40], fill=col)
        cur_lx -= 44

    history_file = os.path.join(BASE_DIR, "history_day-7.json")
    with open(history_file, "r", encoding="utf-8") as f:
        pts = json.load(f)

    px1, py1 = MARGIN + 78, chart_top + 68
    px2, py2 = WIDTH - MARGIN - 24, chart_bot - 52
    pw, ph = px2 - px1, py2 - py1
    draw.rectangle([px1, py1, px2, py2], fill=C_CARD_DARK, outline=(36, 36, 48), width=1)

    raw_vals = [
        (p.get("goe_total", 0), p.get("nerva_total", 0), p.get("streams", {}).get("ttobias_lol", {}).get("viewers", 0))
        for p in pts
    ]
    max_raw = max(max(v) for v in raw_vals)
    max_y = int(math.ceil((max_raw * 1.12) / 5000) * 5000)
    font_ax = _get_font(19, bold=True, font_type="rajdhani")

    for i in range(5):
        gy = py2 - int((i / 4) * ph)
        val = int((i / 4) * max_y)
        draw.line([(px1, gy), (px2, gy)], fill=(30, 30, 42), width=1)
        draw.text((px1 - 12, gy), "0" if val == 0 else f"{val // 1000}k", fill=C_MUTED, font=font_ax, anchor="rm")

    # Event markers
    n_pts = len(pts)
    for ev in DAYS_CONFIG.get("day-7", {}).get("events", []):
        ev_t, ev_l = ev.get("time", ""), ev.get("label", "")
        idx = next((i for i, p in enumerate(pts) if p.get("timestamp", "").split()[-1].startswith(ev_t)), None)
        if idx is not None:
            ex = px1 + int((idx / (n_pts - 1)) * pw)
            for dy in range(py1 + 4, py2, 10):
                draw.line([(ex, dy), (ex, min(dy + 5, py2))], fill=(140, 120, 65), width=2)
            draw.text((ex + 8, py1 + 10), f"{ev_t} {ev_l}", fill=C_GOLD, font=_get_font(18, bold=True, font_type="rajdhani"), anchor="lt")

    buckets = 200
    goe_c, nerva_c, tob_c = [], [], []
    for b in range(buckets):
        i0 = int((b / buckets) * n_pts)
        i1 = max(i0 + 1, int(((b + 1) / buckets) * n_pts))
        sl = raw_vals[i0:i1]
        gv = sum(x[0] for x in sl) / len(sl)
        nv = sum(x[1] for x in sl) / len(sl)
        tv = sum(x[2] for x in sl) / len(sl)
        x = px1 + int((b / (buckets - 1)) * pw)
        goe_c.append((x, py2 - int((gv / max_y) * ph)))
        nerva_c.append((x, py2 - int((nv / max_y) * ph)))
        tob_c.append((x, py2 - int((tv / max_y) * ph)))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.polygon([(px1, py2)] + nerva_c + [(px2, py2)], fill=(59, 130, 246, 35))
    odraw.polygon([(px1, py2)] + goe_c + [(px2, py2)], fill=(255, 24, 36, 48))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    for coords, col, w in [(tob_c, C_TOBIAS, 4), (nerva_c, C_NERVA, 5), (goe_c, C_GOE, 5)]:
        for i in range(len(coords) - 1):
            draw.line([coords[i], coords[i + 1]], fill=col, width=w)

    pk_idx = max(range(n_pts), key=lambda i: raw_vals[i][1])
    pk_val = raw_vals[pk_idx][1]
    pk_ts = pts[pk_idx]["timestamp"].split()[-1][:5]
    pkx = px1 + int((pk_idx / (n_pts - 1)) * pw)
    pky = py2 - int((pk_val / max_y) * ph)
    draw.ellipse([pkx - 7, pky - 7, pkx + 7, pky + 7], fill=C_NERVA, outline=(255, 255, 255), width=3)
    draw.text((pkx - 14, max(py1 + 20, pky - 4)), f"PIK: {_fmt_num(pk_val)} ({pk_ts})", fill=(200, 225, 255), font=_get_font(20, bold=True, font_type="rajdhani"), anchor="rm")

    for t in range(5):
        idx = int((t / 4) * (n_pts - 1))
        ts_hm = pts[idx]["timestamp"].split()[-1][:5]
        tx = px1 + int((idx / (n_pts - 1)) * pw)
        anchor = "lm" if t == 0 else ("rm" if t == 4 else "mm")
        draw.text((tx, py2 + 24), ts_hm, fill=C_MUTED, font=font_ax, anchor=anchor)

    # Bottom 3 camp cards (y: 988..1260)
    cy = 988
    ch = 84
    rows = [
        ("NERVARIEN & CO-STREAMY", C_NERVA, m["nerva"], ms["nerva"]),
        ("TOBIASZ", C_TOBIAS, m["tobias"], ms["tobias"]),
        ("BUNKIER GOE", C_GOE, m["goe"], ms["goe"]),
    ]
    for name, col, cd, sh in rows:
        draw.rounded_rectangle([MARGIN, cy, WIDTH - MARGIN, cy + ch], radius=12, fill=C_CARD, outline=col, width=2)
        draw.text((MARGIN + 22, cy + ch // 2), name, fill=col, font=_get_font(23, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text(
            (WIDTH - MARGIN - 22, cy + ch // 2),
            f"{_fmt_num(cd['watch_hours'])} h ({sh:.1f}%)   •   Pik: {_fmt_num(cd['peak'])}   •   Śr: {_fmt_num(cd['live_avg'])}",
            fill=C_TEXT,
            font=_get_font(22, bold=True, font_type="rajdhani"),
            anchor="rm",
        )
        cy += ch + 14

    out_path = os.path.join(OUT_DIR, "carousel_3_final_14_11.png")
    img.save(out_path)
    return out_path


def build_slide_4_x_kpi(xa: dict) -> str:
    """Slide 4: X #bunkier KPIs + Bunkier vs Community + Daily bar chart."""
    tot = xa["totals"]
    grp = xa["groups"]
    dr = xa["date_range"]

    img, draw = _new_canvas(
        "WORLDS 2026 • AKCJA NA X",
        "#BUNKIER NA X",
        f"{dr['start_label']} – {dr['end_label']} • Zasięgi, posty i zaangażowanie społeczności",
        4,
    )

    col_w = (WIDTH - 2 * MARGIN - 20) // 2
    row_h = 180
    x_l, x_r = MARGIN, MARGIN + col_w + 20
    y1, y2 = 204, 204 + row_h + 18

    _draw_kpi_card(draw, x_l, y1, x_l + col_w, y1 + row_h, "POSTY ŁĄCZNIE", _fmt_num(tot["posts"]), f"{_fmt_num(tot['hashtag_posts'])} z #bunkier • +{tot['non_hashtag_posts']} Worlds", C_GOE)
    _draw_kpi_card(draw, x_r, y1, x_r + col_w, y1 + row_h, "WYŚWIETLENIA", f"{tot['views'] / 1_000_000:.2f} M", f"Dokładnie {_fmt_num(tot['views'])} wyświetleń", C_CYAN)
    _draw_kpi_card(draw, x_l, y2, x_l + col_w, y2 + row_h, "UNIKALNI AUTORZY", _fmt_num(tot["unique_authors"]), "Ekipa Bunkra + cała społeczność", C_TEXT)
    _draw_kpi_card(draw, x_r, y2, x_r + col_w, y2 + row_h, "INTERAKCJE", _fmt_num(tot["interactions"]), f"ER {tot['engagement_rate_pct']}% • {_fmt_num(tot['likes'])} polubień", C_NERVA)

    # Bunkier vs Community (y: 604..818)
    by = 606
    draw.rounded_rectangle([MARGIN, by, WIDTH - MARGIN, by + 204], radius=14, fill=C_CARD, outline=C_BORDER, width=2)
    draw.text((MARGIN + 24, by + 28), "EKIPA BUNKRA vs SPOŁECZNOŚĆ:", fill=C_TEXT, font=_get_font(23, bold=True, font_type="rajdhani"), anchor="lm")

    p_b = grp["bunkier"]["posts_pct"]
    p_c = grp["community"]["posts_pct"]
    v_b = grp["bunkier"]["views_pct"]
    v_c = grp["community"]["views_pct"]

    draw.text((MARGIN + 24, by + 68), "UDZIAŁ W POSTACH:", fill=C_MUTED, font=_get_font(20, bold=True, font_type="rajdhani"), anchor="lm")
    draw.text((WIDTH - MARGIN - 24, by + 68), f"Bunkier {p_b:.1f}%  •  Społeczność {p_c:.1f}%", fill=C_TEXT, font=_get_font(21, bold=True, font_type="rajdhani"), anchor="rm")
    _draw_segmented_bar(img, draw, MARGIN + 24, by + 88, WIDTH - MARGIN - 24, by + 114, [(p_b, C_GOE), (p_c, C_NERVA)], radius=8)

    draw.text((MARGIN + 24, by + 144), "UDZIAŁ W ZASIĘGU (WYŚW.):", fill=C_MUTED, font=_get_font(20, bold=True, font_type="rajdhani"), anchor="lm")
    draw.text((WIDTH - MARGIN - 24, by + 144), f"Bunkier {v_b:.1f}%  •  Społeczność {v_c:.1f}%", fill=C_TEXT, font=_get_font(21, bold=True, font_type="rajdhani"), anchor="rm")
    _draw_segmented_bar(img, draw, MARGIN + 24, by + 164, WIDTH - MARGIN - 24, by + 190, [(v_b, C_GOE), (v_c, C_NERVA)], radius=8)

    # Daily Posts Chart (y: 830..1260)
    cy1, cy2 = 830, 1260
    draw.rounded_rectangle([MARGIN, cy1, WIDTH - MARGIN, cy2], radius=14, fill=C_CARD, outline=C_BORDER, width=2)
    draw.text((MARGIN + 24, cy1 + 30), "AKTYWNOŚĆ DZIENNA (POSTY / DZIEŃ)", fill=C_TEXT, font=_get_font(23, bold=True, font_type="rajdhani"), anchor="lm")
    draw.text((WIDTH - MARGIN - 24, cy1 + 30), "Czerwony = dni BO5", fill=C_GOE, font=_get_font(20, bold=True, font_type="rajdhani"), anchor="rm")

    daily = xa["daily"]
    max_p = max(d["posts"] for d in daily)
    px1, py1 = MARGIN + 26, cy1 + 76
    px2, py2 = WIDTH - MARGIN - 26, cy2 - 50
    slot_w = (px2 - px1) / len(daily)
    bar_w = int(slot_w * 0.66)

    for idx, d in enumerate(daily):
        cx = int(px1 + idx * slot_w + slot_w / 2)
        bh = max(8, int((d["posts"] / max_p) * (py2 - py1 - 24)))
        col = C_GOE if d.get("is_match_day") else C_NERVA
        draw.rounded_rectangle([cx - bar_w // 2, py2 - bh, cx + bar_w // 2, py2], radius=6, fill=col)
        draw.text((cx, py2 - bh - 14), str(d["posts"]), fill=C_TEXT, font=_get_font(18, bold=True, font_type="rajdhani"), anchor="mm")
        # Show every label rotated-free by using compact DD.MM every 2nd day + highlight match days
        if idx % 2 == 0 or d["label"] in ("04.11", "14.11", "15.11"):
            draw.text((cx, py2 + 22), d["label"], fill=C_TEXT if d.get("is_match_day") else C_MUTED, font=_get_font(18, bold=d.get("is_match_day", False), font_type="rajdhani"), anchor="mm")

    out_path = os.path.join(OUT_DIR, "carousel_4_x_kpi.png")
    img.save(out_path)
    return out_path


def build_slide_5_x_top_authors(xa: dict) -> str:
    """Slide 5: TOP 10 Authors on X with big, effortless-to-read rows."""
    authors = xa["top_authors"][:10]
    tot_views = max(1, xa["totals"]["views"])
    top10_views = sum(a["views"] for a in authors)
    top10_share = (top10_views / tot_views) * 100

    img, draw = _new_canvas(
        "WORLDS 2026 • AKCJA NA X",
        "TOP 10 AUTORÓW WG ZASIĘGU",
        f"TOP 10 wygenerowało {top10_share:.1f}% całego zasięgu ({_fmt_num(top10_views)} wyśw.)",
        5,
    )

    y = 204
    row_h = 96
    gap = 10
    max_v = max(1, authors[0]["views"])

    for idx, a in enumerate(authors, start=1):
        is_b = a["role"] == "bunkier"
        col = C_GOE if is_b else C_NERVA
        draw.rounded_rectangle([MARGIN, y, WIDTH - MARGIN, y + row_h], radius=12, fill=C_CARD, outline=C_CRIMSON if idx == 1 else C_BORDER, width=2)

        # Rank pill
        rx1 = MARGIN + 16
        draw.rounded_rectangle([rx1, y + 18, rx1 + 52, y + 60], radius=8, fill=C_GOLD if idx <= 3 else (38, 38, 48))
        draw.text((rx1 + 26, y + 39), f"#{idx}", fill=(12, 12, 16) if idx <= 3 else C_TEXT, font=_get_font(22, bold=True, font_type="rajdhani"), anchor="mm")

        draw.text((rx1 + 68, y + 38), f"@{a['handle']}", fill=col, font=_get_font(27, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text((WIDTH - MARGIN - 22, y + 38), f"{_fmt_num(a['views'])} wyśw.", fill=C_CYAN, font=_get_font(26, bold=True, font_type="rajdhani"), anchor="rm")

        # Progress bar + sub stats
        bar_x1, bar_x2 = rx1 + 68, WIDTH - MARGIN - 22
        bw = max(12, int((a["views"] / max_v) * (bar_x2 - bar_x1)))
        draw.rounded_rectangle([bar_x1, y + 66, bar_x2, y + 76], radius=4, fill=(28, 28, 36))
        draw.rounded_rectangle([bar_x1, y + 66, bar_x1 + bw, y + 76], radius=4, fill=col)

        share_pct = (a["views"] / tot_views) * 100
        draw.text(
            (WIDTH - MARGIN - 22, y + 84),
            f"{a['posts']} postów ({a['hashtag_posts']} #)  •  {_fmt_num(a['interactions'])} int.  •  {share_pct:.1f}% akcji",
            fill=C_MUTED,
            font=_get_font(18, bold=False, font_type="rajdhani"),
            anchor="rm",
        )
        y += row_h + gap

    out_path = os.path.join(OUT_DIR, "carousel_5_x_top_autorzy.png")
    img.save(out_path)
    return out_path


def _wrap_lines(text: str, font, max_w: int, max_lines: int = 2) -> list[str]:
    # Strip supplementary-plane emojis / unsupported symbols to avoid tofu boxes in Rajdhani
    clean = "".join(ch for ch in text if ord(ch) < 0x2600)
    words = " ".join(clean.replace("\n", " ").split()).split(" ")
    lines = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if font.getbbox(cand)[2] - font.getbbox(cand)[0] <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and words:
        # Append ellipsis if text was truncated
        joined = " ".join(lines)
        full = " ".join(words)
        if len(joined) < len(full):
            while lines[-1] and font.getbbox(lines[-1] + "...")[2] - font.getbbox(lines[-1] + "...")[0] > max_w:
                lines[-1] = lines[-1][:-1].rstrip()
            lines[-1] = lines[-1] + "..."
    return lines


def build_slide_6_x_top_posts(xa: dict) -> str:
    """Slide 6: TOP 5 most-viewed posts on X with full 2-line readable text."""
    posts = xa["top_posts"][:5]
    img, draw = _new_canvas(
        "WORLDS 2026 • AKCJA NA X",
        "TOP 5 POSTÓW WG ZASIĘGU",
        "Najpopularniejsze pojedyncze wpisy z całej akcji #bunkier",
        6,
    )

    y = 206
    card_h = 192
    gap = 18
    font_body = _get_font(23, bold=False, font_type="rajdhani")

    for idx, p in enumerate(posts, start=1):
        col = C_GOE if p["role"] == "bunkier" else C_NERVA
        draw.rounded_rectangle([MARGIN, y, WIDTH - MARGIN, y + card_h], radius=14, fill=C_CARD, outline=C_CRIMSON if idx == 1 else C_BORDER, width=2)

        rx1 = MARGIN + 20
        draw.rounded_rectangle([rx1, y + 20, rx1 + 52, y + 60], radius=8, fill=C_GOLD if idx <= 3 else (38, 38, 48))
        draw.text((rx1 + 26, y + 40), f"#{idx}", fill=(12, 12, 16) if idx <= 3 else C_TEXT, font=_get_font(22, bold=True, font_type="rajdhani"), anchor="mm")

        tag_str = " • #bunkier" if p.get("has_bunkier_hashtag") else ""
        draw.text((rx1 + 68, y + 40), f"@{p['author_handle']} • {p['date_label']}{tag_str}", fill=col, font=_get_font(24, bold=True, font_type="rajdhani"), anchor="lm")
        draw.text((WIDTH - MARGIN - 22, y + 40), f"{_fmt_num(p['views'])} wyśw.", fill=C_CYAN, font=_get_font(28, bold=True, font_type="rajdhani"), anchor="rm")

        lines = _wrap_lines(p.get("display_text", p.get("text", "")), font_body, WIDTH - 2 * MARGIN - 48, max_lines=2)
        for li, line in enumerate(lines):
            draw.text((rx1, y + 88 + li * 30), line, fill=C_TEXT, font=font_body, anchor="lm")

        er = (p["interactions"] / max(1, p["views"])) * 100
        draw.text(
            (rx1, y + card_h - 28),
            f"{_fmt_num(p['likes'])} polubień   •   {p['reposts']} RT   •   {p['replies']} odp.",
            fill=C_MUTED,
            font=_get_font(20, bold=True, font_type="rajdhani"),
            anchor="lm",
        )
        draw.text(
            (WIDTH - MARGIN - 22, y + card_h - 28),
            f"ER {er:.2f}%",
            fill=C_TEXT,
            font=_get_font(20, bold=True, font_type="rajdhani"),
            anchor="rm",
        )
        y += card_h + gap

    out_path = os.path.join(OUT_DIR, "carousel_6_x_top_posty.png")
    img.save(out_path)
    return out_path


def generate_all_carousel() -> list[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(BASE_DIR, "tournament_analytics.json"), "r", encoding="utf-8") as f:
        ta = json.load(f)
    with open(os.path.join(BASE_DIR, "x_bunkier_analytics.json"), "r", encoding="utf-8") as f:
        xa = json.load(f)

    paths = [
        build_slide_1_tournament_kpi(ta),
        build_slide_2_matches(ta),
        build_slide_3_finals(ta),
        build_slide_4_x_kpi(xa),
        build_slide_5_x_top_authors(xa),
        build_slide_6_x_top_posts(xa),
    ]
    for p in paths:
        print(f"✅ Wygenerowano slajd karuzeli: {p}")
    return paths


if __name__ == "__main__":
    generate_all_carousel()
