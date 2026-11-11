"""Generates a clean esports infographic card in GoE / #bunkier Worlds 2026 aesthetic (1080x1350)."""

import os
import re
from PIL import Image, ImageDraw, ImageFont

from avatars import get_cached_avatar


def clean_text_for_font(text: str) -> str:
    """Strips emoji and special unicode characters that trigger missing glyph boxes in PIL."""
    if not text:
        return ""
    return re.sub(
        r"[\U00010000-\U0010ffff]|[\u25a0-\u25ff]|[\u2600-\u26ff]|[\u2700-\u27bf]",
        " ",
        text,
    ).strip()


def draw_vector_microphone(draw: ImageDraw.Draw, cx: int, cy: int):
    """Draws a crisp vector microphone icon matching the Worlds 2026 poster."""
    draw.rounded_rectangle(
        [cx - 5, cy - 12, cx + 5, cy + 2], radius=5, fill=(255, 255, 255)
    )
    draw.arc(
        [cx - 9, cy - 6, cx + 9, cy + 6],
        start=0,
        end=180,
        fill=(255, 255, 255),
        width=2,
    )
    draw.line([(cx, cy + 6), (cx, cy + 12)], fill=(255, 255, 255), width=2)
    draw.line([(cx - 6, cy + 12), (cx + 6, cy + 12)], fill=(255, 255, 255), width=2)


def _get_font(size: int, bold: bool = False, font_type: str = "regular"):
    """Loads bundled font (Anton, Rajdhani, Teko, or regular/bold), system font, or falls back gracefully."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if font_type == "anton":
        p = os.path.join(base_dir, "assets", "fonts", "anton.ttf")
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    elif font_type == "rajdhani":
        p = os.path.join(base_dir, "assets", "fonts", "rajdhani_bold.ttf")
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    elif font_type == "teko":
        p = os.path.join(base_dir, "assets", "fonts", "teko.ttf")
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    bundled_font = os.path.join(
        base_dir, "assets", "fonts", "font_bold.ttf" if bold else "font.ttf"
    )

    candidates = [
        bundled_font,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype(
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size
        )
    except Exception:
        pass
    try:
        return ImageFont.truetype("Arial", size)
    except Exception:
        pass
    return ImageFont.load_default()


def draw_top_emblem(
    draw: ImageDraw.Draw,
    width: int,
    cy: int,
    text: str = "WORLDS 2026",
    font: ImageFont.ImageFont = None,
):
    """Draws a centered Worlds 2026 emblem with microphone icon, separator pipe, and text."""
    if font is None:
        font = _get_font(26, bold=True, font_type="rajdhani")
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    total_w = 40 + text_w
    start_x = (width - total_w) // 2

    mic_cx = start_x + 9
    draw_vector_microphone(draw, mic_cx, cy)

    pipe_x = start_x + 28
    pipe_half = max(10, (bbox[3] - bbox[1]) // 2 + 1)
    draw.line(
        [(pipe_x, cy - pipe_half), (pipe_x, cy + pipe_half)],
        fill=(255, 255, 255),
        width=2,
    )

    text_x = start_x + 40
    draw.text((text_x, cy), text, fill=(255, 255, 255), font=font, anchor="lm")


def draw_duel_bar(
    base_img: Image.Image,
    draw: ImageDraw.Draw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    goe_pct: float,
    radius: int = 8,
):
    """Draws a crisp dual-color proportional bar (GoE Red vs Nervarien White) in a pill container."""
    bar_w = x2 - x1
    bar_h = y2 - y1
    if bar_w <= 0 or bar_h <= 0:
        return

    # Container pill with dark background and crisp high-contrast border
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=radius,
        fill=(14, 14, 18),
        outline=(70, 70, 85),
        width=2,
    )

    goe_pct = max(0.0, min(100.0, goe_pct))
    split_w = int(bar_w * (goe_pct / 100.0))

    # Inner bar image for crisp masking of rounded capsule ends
    inner_mask = Image.new("L", (bar_w, bar_h), 0)
    d_mask = ImageDraw.Draw(inner_mask)
    d_mask.rounded_rectangle([0, 0, bar_w - 1, bar_h - 1], radius=radius, fill=255)

    inner_bar = Image.new("RGB", (bar_w, bar_h), (14, 14, 18))
    d_bar = ImageDraw.Draw(inner_bar)

    # Left segment: GoE Red (#ff0033)
    if split_w > 0:
        d_bar.rectangle([0, 0, split_w, bar_h], fill=(255, 0, 51))

    # Right segment: Nervarien White (#f0f2f5)
    if split_w < bar_w:
        d_bar.rectangle([split_w, 0, bar_w, bar_h], fill=(240, 242, 245))

    # Crisp divider notch between the two teams (2px wide)
    if 0 < split_w < bar_w:
        d_bar.rectangle([split_w - 1, 0, split_w + 1, bar_h], fill=(10, 10, 12))

    # Paste inner dual-bar using the rounded capsule mask
    base_img.paste(inner_bar, (x1, y1), inner_mask)

    # Re-draw the crisp container outline on top to ensure razor-sharp edges
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=radius,
        outline=(85, 85, 105),
        width=2,
    )


def draw_goe_background(draw: ImageDraw.Draw, w: int, h: int):
    """Draws geometric angular red-and-black shards inspired by Worlds 2026 / #bunkier posters."""
    draw.rectangle([0, 0, w, h], fill=(10, 10, 12))

    is_landscape = w > h

    if is_landscape:
        # 16:9 / Landscape (e.g. 1200x630 OG Banner)
        # Keep shards strictly in corners/perimeter so central cards & duel bar sit on clean black
        shards = [
            # Top-left corner framing
            (
                [
                    (0, 0),
                    (int(w * 0.35), 0),
                    (int(w * 0.16), int(h * 0.30)),
                    (0, int(h * 0.22)),
                ],
                (22, 12, 16),
            ),
            (
                [
                    (0, 0),
                    (int(w * 0.22), 0),
                    (int(w * 0.08), int(h * 0.24)),
                    (0, int(h * 0.16)),
                ],
                (90, 12, 20),
            ),
            (
                [
                    (0, 0),
                    (int(w * 0.12), 0),
                    (int(w * 0.03), int(h * 0.16)),
                    (0, int(h * 0.10)),
                ],
                (140, 16, 26),
            ),
            # Top-right corner framing
            (
                [
                    (w, 0),
                    (w - int(w * 0.35), 0),
                    (w - int(w * 0.16), int(h * 0.28)),
                    (w, int(h * 0.20)),
                ],
                (22, 12, 16),
            ),
            (
                [
                    (w, 0),
                    (w - int(w * 0.22), 0),
                    (w - int(w * 0.08), int(h * 0.22)),
                    (w, int(h * 0.14)),
                ],
                (110, 14, 24),
            ),
            (
                [
                    (w, 0),
                    (w - int(w * 0.12), 0),
                    (w - int(w * 0.03), int(h * 0.14)),
                    (w, int(h * 0.08)),
                ],
                (160, 18, 30),
            ),
            # Bottom-left corner framing (strictly below y=520, never touches the bar at y=458..478)
            (
                [
                    (0, h),
                    (int(w * 0.20), h),
                    (int(w * 0.08), h - int(h * 0.14)),
                    (0, h - int(h * 0.08)),
                ],
                (22, 12, 16),
            ),
            (
                [
                    (0, h),
                    (int(w * 0.12), h),
                    (int(w * 0.04), h - int(h * 0.09)),
                    (0, h - int(h * 0.05)),
                ],
                (110, 14, 24),
            ),
            # Bottom-right corner framing
            (
                [
                    (w, h),
                    (w - int(w * 0.22), h),
                    (w - int(w * 0.09), h - int(h * 0.15)),
                    (w, h - int(h * 0.09)),
                ],
                (22, 12, 16),
            ),
            (
                [
                    (w, h),
                    (w - int(w * 0.13), h),
                    (w - int(w * 0.04), h - int(h * 0.10)),
                    (w, h - int(h * 0.05)),
                ],
                (130, 16, 28),
            ),
        ]
        for poly, col in shards:
            draw.polygon(poly, fill=col)

        # Subtle crisp corner accent lines
        draw.line([(0, int(h * 0.18)), (int(w * 0.25), 0)], fill=(180, 20, 35), width=2)
        draw.line(
            [(w - int(w * 0.25), 0), (w, int(h * 0.16))], fill=(180, 20, 35), width=2
        )
        draw.line(
            [(0, h - int(h * 0.10)), (int(w * 0.15), h)], fill=(160, 18, 30), width=2
        )
        draw.line(
            [(w - int(w * 0.16), h), (w, h - int(h * 0.11))],
            fill=(160, 18, 30),
            width=2,
        )

    else:
        # Portrait (e.g. 1080x1350)
        # Deep dark crimson tones framing the top and bottom corners
        shards = [
            ([(0, 0), (w, 0), (w, 360), (0, 180)], (18, 10, 14)),
            ([(0, 0), (480, 0), (190, 500), (0, 380)], (100, 12, 18)),
            ([(0, 0), (280, 0), (80, 390), (0, 270)], (160, 16, 26)),
            ([(w, 0), (w - 500, 0), (w - 220, 440), (w, 350)], (110, 12, 20)),
            ([(w, 0), (w - 300, 0), (w - 110, 330), (w, 230)], (170, 18, 28)),
            ([(0, h), (w, h), (w, h - 280), (0, h - 190)], (18, 10, 14)),
            ([(0, h), (380, h), (210, h - 300), (0, h - 210)], (120, 14, 22)),
            ([(0, h), (220, h), (110, h - 220), (0, h - 150)], (160, 16, 26)),
            ([(w, h), (w - 420, h), (w - 180, h - 290), (w, h - 200)], (110, 12, 20)),
            ([(w, h), (w - 250, h), (w - 90, h - 210), (w, h - 140)], (160, 16, 26)),
        ]
        for poly, col in shards:
            draw.polygon(poly, fill=col)

        draw.line([(0, 140), (w, 380)], fill=(180, 20, 35), width=2)
        draw.line([(0, h - 280), (w, h - 140)], fill=(180, 20, 35), width=2)


def draw_slanted_text(
    base_img: Image.Image,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple,
    center_pos: tuple[int, int],
    slant_k: float = 0.20,
):
    """Renders text with forward italic athletic slant using affine shear transformation."""
    bbox = font.getbbox(text)
    pad = 20
    w = bbox[2] - bbox[0] + pad * 2
    h = bbox[3] - bbox[1] + pad * 2

    txt_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=fill)

    extra_w = int(h * slant_k)
    out_w = w + extra_w
    matrix = (1, slant_k, -slant_k * h, 0, 1, 0)
    sheared = txt_img.transform(
        (out_w, h), Image.AFFINE, matrix, resample=Image.Resampling.BICUBIC
    )

    x = center_pos[0] - out_w // 2
    y = center_pos[1] - h // 2
    base_img.paste(sheared, (x, y), sheared)


def create_battle_card(
    data: dict, output_path: str = "battle_card.png", platform: str = "ALL"
) -> str:
    """Renders a 1080x1350 clean GoE-style infographic poster with avatars and slanted typography."""
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    # Worlds 2026 condensed fonts
    font_top_emblem = _get_font(26, bold=True, font_type="rajdhani")
    font_main_title = _get_font(78, font_type="anton")
    font_sub_title = _get_font(22, font_type="rajdhani")
    font_team_name = _get_font(34, font_type="rajdhani")
    font_score = _get_font(86, font_type="anton")
    font_score_sub = _get_font(18, font_type="rajdhani")
    font_vs = _get_font(36, font_type="anton")
    font_badge = _get_font(14, font_type="rajdhani")
    font_card_ch = _get_font(22, font_type="rajdhani")
    font_card_det = _get_font(15, bold=False)
    font_card_viewers = _get_font(24, font_type="rajdhani")
    font_footer_pipes = _get_font(17, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(20, font_type="anton")
    font_system_note = _get_font(14, font_type="rajdhani")

    # Top Emblem (Crisp vector microphone icon + WORLDS 2026 text)
    top_label = (
        "WORLDS 2026 • WIELKI FINAŁ" if data.get("stage") == "finals" else "WORLDS 2026"
    )
    draw_top_emblem(draw, width, 48, top_label, font_top_emblem)

    # Slanted Main Title (matching poster: CO-STREAM GOE)
    draw_slanted_text(
        img,
        "CO-STREAM GOE",
        font_main_title,
        (255, 0, 51),
        (width // 2, 112),
        slant_k=0.20,
    )

    platform_tag = f"[{platform.upper()}] " if platform.upper() != "ALL" else ""
    ts = data.get("timestamp", "").split(" ")[-1]
    match_short = data.get("match_short")
    sub_prefix = (
        f"{match_short}  •  " if data.get("stage") == "finals" and match_short else ""
    )
    draw.text(
        (width // 2, 182),
        f"{sub_prefix}w Kieleckim bunkrze vs Nervarien  •  {platform_tag}{ts}",
        fill=(255, 255, 255),
        font=font_sub_title,
        anchor="mm",
    )

    # Filter streams if platform is specified
    goe_raw = data.get("groups", {}).get("GOE", {}).get("streams", [])
    nerva_raw = data.get("groups", {}).get("NERVA", {}).get("streams", [])
    tobiasz_raw = data.get("groups", {}).get("TOBIASZ", {}).get("streams", [])

    if platform.upper() == "TWITCH":
        goe_streams = [s for s in goe_raw if s.get("platform") == "Twitch"]
        nerva_streams = [s for s in nerva_raw if s.get("platform") == "Twitch"]
        tobiasz_streams = [s for s in tobiasz_raw if s.get("platform") == "Twitch"]
    elif platform.upper() == "YOUTUBE":
        goe_streams = [s for s in goe_raw if s.get("platform") == "YouTube"]
        nerva_streams = [s for s in nerva_raw if s.get("platform") == "YouTube"]
        tobiasz_streams = [s for s in tobiasz_raw if s.get("platform") == "YouTube"]
    else:
        goe_streams = goe_raw
        nerva_streams = nerva_raw
        tobiasz_streams = tobiasz_raw

    goe_total = sum(s.get("viewers", 0) for s in goe_streams)
    nerva_total = sum(s.get("viewers", 0) for s in nerva_streams)
    tot = goe_total + nerva_total
    goe_pct = round((goe_total / tot * 100), 1) if tot > 0 else 50.0
    nerva_pct = round((nerva_total / tot * 100), 1) if tot > 0 else 50.0

    # GOE Box (Aesthetic of Bingo / Prediction Cards: deep black #0a0a0c, sharp 1px red #ff0033 border, radius 12)
    draw.rounded_rectangle(
        [50, 215, 485, 435],
        radius=12,
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )
    draw.text((75, 235), "GOE", fill=(255, 0, 51), font=font_team_name)
    draw.text(
        (75, 266),
        f"{goe_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (75, 394),
        f"{goe_pct}% WIDZÓW",
        fill=(255, 255, 255) if goe_total >= nerva_total else (160, 160, 170),
        font=font_score_sub,
    )

    # VS Center Circle
    draw.ellipse(
        [width // 2 - 40, 295, width // 2 + 40, 375],
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )
    draw.text((width // 2, 335), "VS", fill=(255, 255, 255), font=font_vs, anchor="mm")

    # NERVA Box
    draw.rounded_rectangle(
        [595, 215, 1030, 435],
        radius=12,
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )
    draw.text((620, 235), "NERVARIEN", fill=(255, 255, 255), font=font_team_name)
    draw.text(
        (620, 266),
        f"{nerva_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (620, 394),
        f"{nerva_pct}% WIDZÓW",
        fill=(255, 255, 255) if nerva_total > goe_total else (160, 160, 170),
        font=font_score_sub,
    )

    # Proportional Bar (Crisp GoE Red vs Nervarien White Pill)
    bar_x1, bar_y1, bar_x2, bar_y2 = 50, 455, 1030, 477
    draw_duel_bar(img, draw, bar_x1, bar_y1, bar_x2, bar_y2, goe_pct, radius=8)

    # Stream Cards with Avatars (include GOE, NERVA and TOBIASZ)
    all_streams = (
        [("GOE", st) for st in goe_streams]
        + [("NERVA", st) for st in nerva_streams]
        + [("TOBIASZ", st) for st in tobiasz_streams]
    )

    y_pos = 505
    card_h = 92 if len(all_streams) <= 5 else 80
    gap = 12 if len(all_streams) <= 5 else 8

    for grp_tag, st in all_streams:
        is_costream = (
            st.get("tag") == "costream"
            or st.get("costream") is True
            or "co-stream" in st.get("title", "").lower()
            or "costream" in st.get("id", "").lower()
            or grp_tag == "TOBIASZ"
        )
        is_live = st.get("is_live", False)

        # Card container (sharp 1px red border, deep black surface #0a0a0c, radius 12)
        border_col = (255, 0, 51) if is_live else (80, 20, 26)
        bg_col = (10, 10, 12)
        draw.rounded_rectangle(
            [50, y_pos, 1030, y_pos + card_h],
            radius=12,
            fill=bg_col,
            outline=border_col,
            width=1,
        )

        # Avatar Box with red border
        av_dim = card_h - 20
        av_size = (av_dim, av_dim)
        av_img = get_cached_avatar(st["id"], st.get("avatar_url", ""), size=av_size)
        av_x = 64
        av_y = y_pos + 10

        # Paste avatar
        img.paste(av_img, (av_x, av_y), av_img)
        # Red frame around avatar
        draw.rounded_rectangle(
            [av_x - 1, av_y - 1, av_x + av_dim + 1, av_y + av_dim + 1],
            radius=6,
            outline=(255, 0, 51),
            width=1,
        )

        content_x = av_x + av_dim + 16

        # Platform badge (Twitch purple / YouTube red)
        is_twitch = st.get("platform") == "Twitch"
        badge_bg = (145, 70, 255) if is_twitch else (255, 0, 51)
        draw.rounded_rectangle(
            [content_x, y_pos + 14, content_x + 85, y_pos + 38],
            radius=4,
            fill=badge_bg,
        )
        draw.text(
            (content_x + 42, y_pos + 26),
            st.get("platform", "Stream").upper(),
            fill=(255, 255, 255),
            font=font_badge,
            anchor="mm",
        )

        # Camp Tag
        if grp_tag == "GOE":
            camp_bg = (255, 0, 51)
        elif grp_tag == "TOBIASZ":
            camp_bg = (249, 115, 22)
        else:
            camp_bg = (50, 50, 60)

        camp_w = 90 if grp_tag == "TOBIASZ" else 85
        draw.rounded_rectangle(
            [content_x + 95, y_pos + 14, content_x + 95 + camp_w, y_pos + 38],
            radius=4,
            fill=camp_bg,
        )
        draw.text(
            (content_x + 95 + camp_w // 2, y_pos + 26),
            grp_tag,
            fill=(255, 255, 255),
            font=font_badge,
            anchor="mm",
        )

        # Costream Badge if applicable
        next_tag_x = content_x + 95 + camp_w + 10
        if is_costream:
            draw.rounded_rectangle(
                [next_tag_x, y_pos + 14, next_tag_x + 90, y_pos + 38],
                radius=4,
                fill=(245, 158, 11),
            )
            draw.text(
                (next_tag_x + 45, y_pos + 26),
                "CO-STREAM",
                fill=(0, 0, 0),
                font=font_badge,
                anchor="mm",
            )
            next_tag_x += 100

        # Channel name
        draw.text(
            (next_tag_x + 10, y_pos + 26),
            st.get("channel", ""),
            fill=(255, 255, 255) if is_live else (180, 180, 190),
            font=font_card_ch,
            anchor="lm",
        )

        # Title snippet (cleaned of unsupported emoji characters that cause tofu boxes)
        raw_title = st.get("title") or st.get("category") or "Transmisja na żywo"
        cleaned_title = clean_text_for_font(raw_title)
        title_snippet = cleaned_title[:65] + ("..." if len(cleaned_title) > 65 else "")
        draw.text(
            (content_x, y_pos + 56),
            title_snippet,
            fill=(150, 150, 165),
            font=font_card_det,
        )

        # Viewers on right
        if is_live:
            viewers_str = f"{st.get('viewers', 0):,} WIDZÓW".replace(",", " ")
            viewers_col = (255, 255, 255)
        else:
            viewers_str = "OFFLINE"
            viewers_col = (130, 130, 140)

        draw.text(
            (1010, y_pos + card_h // 2),
            viewers_str,
            fill=viewers_col,
            font=font_card_viewers,
            anchor="rm",
        )

        y_pos += card_h + gap

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

    # #BUNKIER Badge in red
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


def create_og_card(data: dict, output_path: str = "og_preview.png") -> str:
    """Generates a 1200x630 OpenGraph / Twitter Card preview banner in GoE-First #Bunkier aesthetic."""
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), color=(10, 10, 12))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    font_top_emblem = _get_font(20, bold=True, font_type="rajdhani")
    font_main_title = _get_font(62, font_type="anton")
    font_sub_title = _get_font(18, font_type="rajdhani")
    font_hero_title = _get_font(22, bold=True, font_type="rajdhani")
    font_hero_score = _get_font(58, font_type="anton")
    font_hero_sub = _get_font(17, font_type="rajdhani")
    font_mini_label = _get_font(14, bold=True, font_type="rajdhani")
    font_mini_val = _get_font(26, font_type="anton")
    font_mini_sub = _get_font(14, font_type="rajdhani")
    font_context_label = _get_font(15, bold=True, font_type="rajdhani")
    font_footer_pipes = _get_font(14, bold=True, font_type="rajdhani")
    font_bunkier_badge = _get_font(16, font_type="anton")
    font_system_note = _get_font(12, font_type="rajdhani")

    # 1. Top Emblem (Mathematically centered)
    is_finals = data.get("stage") == "finals"
    emblem_text = (
        "WORLDS 2026 • WIELKI FINAŁ (14.11)"
        if is_finals
        else "WORLDS 2026 • STUDIO BUNKROWE LIVE"
    )
    draw_top_emblem(
        draw,
        width,
        32,
        emblem_text,
        font_top_emblem,
    )

    # 2. Main Slanted Title (GoE Hero)
    draw_slanted_text(
        img,
        "CO-STREAM GOE",
        font_main_title,
        (255, 0, 51),
        (width // 2, 84),
        slant_k=0.20,
    )

    # 3. Subtitle
    match_short = data.get("match_short", "")
    sub_label = (
        f"{match_short} • w Kieleckim Bunkrze"
        if is_finals and match_short
        else "w Kieleckim Bunkrze • Widownia i Wyniki na Żywo"
    )
    draw.text(
        (width // 2, 124),
        sub_label,
        fill=(255, 255, 255),
        font=font_sub_title,
        anchor="mm",
    )

    # 4. Stream Data Calculation
    goe_raw = data.get("groups", {}).get("GOE", {}).get("streams", [])
    nerva_raw = data.get("groups", {}).get("NERVA", {}).get("streams", [])

    goe_streams = list(goe_raw)
    nerva_streams = [
        s for s in nerva_raw if not s.get("is_costream") and not s.get("is_curiosity")
    ]

    goe_total = sum(s.get("viewers", 0) for s in goe_streams)
    nerva_total = sum(s.get("viewers", 0) for s in nerva_streams)
    is_live = any(s.get("is_live", False) for s in goe_streams + nerva_streams)
    is_finished = data.get("is_finished", False)
    st = data.get("summary_stats", {})

    # Extract YouTube vs Twitch
    yt_st = next((s for s in goe_streams if s.get("platform") == "YouTube"), None)
    tw_st = next((s for s in goe_streams if s.get("platform") == "Twitch"), None)
    yt_v = (
        (yt_st.get("viewers", 0) if yt_st else 0)
        if is_live
        else (st.get("yt_peak", 0) if is_finished else 0)
    )
    tw_v = (
        (tw_st.get("viewers", 0) if tw_st else 0)
        if is_live
        else (st.get("tw_peak", 0) if is_finished else 0)
    )
    sum_yt_tw = yt_v + tw_v
    yt_pct = round((yt_v / sum_yt_tw * 100), 1) if sum_yt_tw > 0 else 50.0

    # Duel context stats
    if is_finished:
        pk_g = st.get("goe_peak", 0)
        pk_n = st.get("nerva_peak", 0)
        tot_duel = pk_g + pk_n
        goe_pct = round((pk_g / tot_duel * 100), 1) if tot_duel > 0 else 50.0
    else:
        tot_duel = goe_total + nerva_total
        goe_pct = round((goe_total / tot_duel * 100), 1) if tot_duel > 0 else 50.0

    # 5. Big GoE Hero Card
    card_x1, card_y1, card_x2, card_y2 = 60, 142, 1140, 434
    draw.rounded_rectangle(
        [card_x1, card_y1, card_x2, card_y2],
        radius=12,
        fill=(10, 10, 12),
        outline=(255, 0, 51),
        width=1,
    )

    # Hero Card Header
    draw.text(
        (90, 162),
        "WIDOWNIA CO-STREAM GOE (KIELECKI BUNKIER)",
        fill=(255, 0, 51),
        font=font_hero_title,
    )

    if is_live:
        status_text = "NA ŻYWO"
        status_color = (255, 24, 36)
        main_val = f"{goe_total:,}".replace(",", " ")
        main_sub = (
            f"ŁĄCZNIE NA ŻYWO • PIK: {(st.get('goe_peak') or goe_total):,}".replace(
                ",", " "
            )
        )
    elif is_finished:
        status_text = "TRANSMISJA ZAKOŃCZONA"
        status_color = (160, 160, 175)
        main_val = f"{st.get('goe_peak', 0):,} PIK".replace(",", " ")
        main_sub = f"ŚREDNIA WIDOWNIA: {st.get('goe_avg', 0):,} WIDZÓW".replace(
            ",", " "
        )
    else:
        goe_start = data.get("schedule", {}).get("goe_start", "21:15")
        status_text = f"START O {goe_start} CET"
        status_color = (255, 77, 109)
        main_val = f"{goe_start} CET"
        match_start = data.get("schedule", {}).get("match_start", "23:00")
        main_sub = f"START STUDIA BUNKROWEGO • MECZ: {match_start}"

    if is_live:
        bbox_st = font_hero_title.getbbox(status_text)
        st_w = bbox_st[2] - bbox_st[0]
        dot_r = 5
        dot_x = 1110 - st_w - 14
        dot_y = 162 + (bbox_st[3] - bbox_st[1]) // 2
        draw.ellipse(
            [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
            fill=(255, 24, 36),
        )
        draw.text(
            (1110, 162),
            status_text,
            fill=status_color,
            font=font_hero_title,
            anchor="ra",
        )
    else:
        draw.text(
            (1110, 162),
            status_text,
            fill=status_color,
            font=font_hero_title,
            anchor="ra",
        )

    # Main Big Number
    draw.text((90, 190), main_val, fill=(255, 255, 255), font=font_hero_score)
    draw.text((90, 260), main_sub, fill=(255, 77, 109), font=font_hero_sub)

    # 6. Platform Breakdown Mini-Cards (YouTube & Twitch)
    # Left: YouTube (@gadaja_)
    yt_card_x1, yt_card_y1, yt_card_x2, yt_card_y2 = 90, 296, 580, 374
    draw.rounded_rectangle(
        [yt_card_x1, yt_card_y1, yt_card_x2, yt_card_y2],
        radius=8,
        fill=(14, 14, 18),
        outline=(239, 68, 68),
        width=1,
    )
    draw.ellipse([106, 311, 116, 321], fill=(239, 68, 68))
    draw.text(
        (124, 309),
        "YouTube (Gadają o Esporcie)",
        fill=(239, 68, 68),
        font=font_mini_label,
    )
    yt_disp_val = (
        f"{yt_v:,} widzów".replace(",", " ")
        if (is_live or is_finished)
        else "Transmisja @gadaja_"
    )
    draw.text((106, 333), yt_disp_val, fill=(255, 255, 255), font=font_mini_val)
    yt_sub_txt = (
        f"{yt_pct}% widowni Bunkra"
        if (is_live or is_finished)
        else "Główny kanał YouTube"
    )
    draw.text(
        (564, 344), yt_sub_txt, fill=(200, 200, 210), font=font_mini_sub, anchor="ra"
    )

    # Right: Twitch (GoE_stream)
    tw_card_x1, tw_card_y1, tw_card_x2, tw_card_y2 = 620, 296, 1110, 374
    draw.rounded_rectangle(
        [tw_card_x1, tw_card_y1, tw_card_x2, tw_card_y2],
        radius=8,
        fill=(14, 14, 18),
        outline=(168, 85, 247),
        width=1,
    )
    draw.ellipse([636, 311, 646, 321], fill=(168, 85, 247))
    draw.text(
        (654, 309),
        "Twitch (GoE_stream)",
        fill=(168, 85, 247),
        font=font_mini_label,
    )
    tw_disp_val = (
        f"{tw_v:,} widzów".replace(",", " ")
        if (is_live or is_finished)
        else "Transmisja GoE_stream"
    )
    draw.text((636, 333), tw_disp_val, fill=(255, 255, 255), font=font_mini_val)
    tw_pct = round(100.0 - yt_pct, 1)
    tw_sub_txt = (
        f"{tw_pct}% widowni Bunkra" if (is_live or is_finished) else "Kanał Twitch"
    )
    draw.text(
        (1094, 344), tw_sub_txt, fill=(200, 200, 210), font=font_mini_sub, anchor="ra"
    )

    # Platform Split Bar
    bar_split_y1, bar_split_y2 = 388, 404
    split_w = int((1110 - 90) * (yt_pct / 100.0))
    draw.rounded_rectangle(
        [90, bar_split_y1, 1110, bar_split_y2],
        radius=6,
        fill=(14, 14, 18),
        outline=(50, 50, 60),
        width=1,
    )
    if split_w > 0:
        draw.rounded_rectangle(
            [90, bar_split_y1, 90 + split_w, bar_split_y2],
            radius=6,
            fill=(239, 68, 68),
        )
    if split_w < (1110 - 90):
        draw.rounded_rectangle(
            [90 + split_w, bar_split_y1, 1110, bar_split_y2],
            radius=6,
            fill=(168, 85, 247),
        )

    # 7. Contextual Market Duel Bar (Nervarien Battle Context)
    if is_live:
        diff = goe_total - nerva_total
        diff_str = (
            f"+{diff:,} przewagi Bunkra".replace(",", " ")
            if diff >= 0
            else f"{diff:,} straty do Nervy".replace(",", " ")
        )
        context_str = f"KONTEKST RYNKOWY: GoE skupia {goe_pct}% widowni starcia (GoE: {goe_total:,} vs Nerva: {nerva_total:,} • {diff_str})".replace(
            ",", " "
        )
    elif is_finished:
        pk_goe = st.get("goe_peak", 0)
        pk_nerva = st.get("nerva_peak", 0)
        context_str = f"KONTEKST RYNKOWY: GoE {pk_goe:,} pik vs Nervarien {pk_nerva:,} pik (Średnia: {st.get('goe_avg', 0):,} vs {st.get('nerva_avg', 0):,})".replace(
            ",", " "
        )
    else:
        sched = data.get("schedule", {})
        goe_start = sched.get("goe_start", "19:00")
        nerva_start = sched.get("nerva_start", "19:30")
        match_start = sched.get("match_start", "20:00")
        context_str = f"KONTEKST RYNKOWY: GoE (start {goe_start}) vs Nervarien (~{nerva_start} • mecz {match_start})"

    draw.text(
        (width // 2, 456),
        context_str,
        fill=(255, 255, 255),
        font=font_context_label,
        anchor="mm",
    )

    # Proportional Bar (GoE Red vs Nervarien White Pill)
    bar_x1, bar_y1, bar_x2, bar_y2 = 120, 474, 1080, 492
    draw_duel_bar(img, draw, bar_x1, bar_y1, bar_x2, bar_y2, goe_pct, radius=8)

    # 8. Footer (Roster + Bunkier Badge)
    roster_pipes = (
        "DEJF | CZARNYPIOTRUS | BIALITO | MAJUTEK | PEDRO | MAGVAYER | JASKIER"
    )
    draw.text(
        (width // 2, 520),
        roster_pipes,
        fill=(255, 255, 255),
        font=font_footer_pipes,
        anchor="mm",
    )

    bunkier_w = 110
    bunkier_h = 24
    bx = (width - bunkier_w) // 2
    by = 542
    draw.rounded_rectangle(
        [bx, by, bx + bunkier_w, by + bunkier_h], radius=4, fill=(255, 0, 51)
    )
    draw.text(
        (width // 2, by + bunkier_h // 2),
        "#BUNKIER",
        fill=(255, 255, 255),
        font=font_bunkier_badge,
        anchor="mm",
    )

    draw.text(
        (width // 2, 592),
        "maciejsonik.github.io/goe-bunkier • Statystyki widowni Co-stream GoE • Worlds 2026",
        fill=(140, 140, 150),
        font=font_system_note,
        anchor="mm",
    )

    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    from scraper import fetch_all_data

    data = fetch_all_data()
    out = create_battle_card(data, "battle_card.png")
    print(f"Card saved with Worlds 2026 styling: {out}")
