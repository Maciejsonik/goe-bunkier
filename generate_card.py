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
        r'[\U00010000-\U0010ffff]|[\u25a0-\u25ff]|[\u2600-\u26ff]|[\u2700-\u27bf]',
        ' ',
        text,
    ).strip()


def draw_vector_microphone(draw: ImageDraw.Draw, cx: int, cy: int):
    """Draws a crisp vector microphone icon matching the Worlds 2026 poster."""
    draw.rounded_rectangle([cx - 5, cy - 12, cx + 5, cy + 2], radius=5, fill=(255, 255, 255))
    draw.arc([cx - 9, cy - 6, cx + 9, cy + 6], start=0, end=180, fill=(255, 255, 255), width=2)
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


def draw_goe_background(draw: ImageDraw.Draw, w: int, h: int):
    """Draws geometric angular red-and-black shards inspired by Worlds 2026 / #bunkier posters."""
    draw.rectangle([0, 0, w, h], fill=(10, 10, 12))

    shards = [
        ([(0, 0), (w, 0), (w, 360), (0, 180)], (18, 10, 14)),
        ([(0, 0), (480, 0), (190, 520), (0, 390)], (140, 12, 22)),
        ([(0, 0), (290, 0), (80, 410), (0, 280)], (210, 18, 30)),
        ([(w, 0), (w - 520, 0), (w - 220, 460), (w, 370)], (160, 14, 25)),
        ([(w, 0), (w - 320, 0), (w - 110, 340), (w, 240)], (255, 0, 51)),
        ([(0, h), (w, h), (w, h - 290), (0, h - 200)], (18, 10, 14)),
        ([(0, h), (410, h), (230, h - 370), (0, h - 260)], (180, 16, 28)),
        ([(0, h), (250, h), (130, h - 280), (0, h - 190)], (255, 0, 51)),
        ([(w, h), (w - 450, h), (w - 190, h - 350), (w, h - 240)], (140, 12, 22)),
        ([(w, h), (w - 280, h), (w - 100, h - 260), (w, h - 170)], (220, 18, 32)),
    ]

    for poly, col in shards:
        draw.polygon(poly, fill=col)

    draw.line([(0, 140), (w, 400)], fill=(255, 0, 51), width=3)
    draw.line([(0, h - 340), (w, h - 150)], fill=(255, 0, 51), width=3)


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

    # Slanted Main Title (matching poster: CO-STREAM GOE)
    draw_slanted_text(
        img,
        "CO-STREAM GOE",
        font_main_title,
        (255, 0, 51),
        (width // 2, 125),
        slant_k=0.20,
    )

    platform_tag = f"[{platform.upper()}] " if platform.upper() != "ALL" else ""
    ts = data.get("timestamp", "").split(" ")[-1]
    draw.text(
        (width // 2, 175),
        f"w Kieleckim bunkrze vs Nervarien  •  {platform_tag}{ts}",
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
        (75, 280),
        f"{goe_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (75, 390),
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
        (620, 280),
        f"{nerva_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (620, 390),
        f"{nerva_pct}% WIDZÓW",
        fill=(255, 255, 255) if nerva_total > goe_total else (160, 160, 170),
        font=font_score_sub,
    )

    # Proportional Bar
    bar_x1, bar_y1, bar_x2, bar_y2 = 50, 455, 1030, 477
    draw.rounded_rectangle(
        [bar_x1, bar_y1, bar_x2, bar_y2],
        radius=8,
        fill=(20, 20, 24),
        outline=(255, 0, 51),
        width=1,
    )
    bar_w = bar_x2 - bar_x1
    goe_w = int(bar_w * (goe_pct / 100.0))
    goe_w = max(10, min(bar_w - 10, goe_w))
    draw.rounded_rectangle(
        [bar_x1, bar_y1, bar_x1 + goe_w, bar_y2], radius=8, fill=(255, 0, 51)
    )

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


if __name__ == "__main__":
    from scraper import fetch_all_data

    data = fetch_all_data()
    out = create_battle_card(data, "battle_card.png")
    print(f"Card saved with Worlds 2026 styling: {out}")
