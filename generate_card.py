"""Generates a clean esports infographic card in GoE aesthetic with slanted typography and avatars (1080x1350)."""

import os
from PIL import Image, ImageDraw, ImageFont

from avatars import get_cached_avatar


def _get_font(size: int, bold: bool = False):
    """Loads bundled font, system font, or falls back gracefully."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_font = os.path.join(
        base_dir, "assets", "fonts", "font_bold.ttf" if bold else "font.ttf"
    )

    candidates = [
        bundled_font,
        # Linux standard paths (GitHub Actions Ubuntu)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # macOS standard paths
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
    """Draws geometric angular shards inspired by the GoE poster aesthetic."""
    draw.rectangle([0, 0, w, h], fill=(8, 8, 10))

    shards = [
        ([(0, 0), (w, 0), (w, 320), (0, 160)], (18, 10, 12)),
        ([(0, 0), (450, 0), (180, 480), (0, 360)], (140, 15, 22)),
        ([(0, 0), (280, 0), (80, 380), (0, 260)], (190, 20, 28)),
        ([(w, 0), (w - 480, 0), (w - 200, 420), (w, 340)], (160, 18, 25)),
        ([(w, 0), (w - 300, 0), (w - 100, 320), (w, 220)], (225, 24, 34)),
        ([(0, h), (w, h), (w, h - 260), (0, h - 180)], (20, 10, 14)),
        ([(0, h), (380, h), (220, h - 340), (0, h - 240)], (180, 20, 28)),
        ([(0, h), (240, h), (120, h - 260), (0, h - 180)], (225, 24, 34)),
        ([(w, h), (w - 420, h), (w - 180, h - 320), (w, h - 220)], (150, 16, 24)),
        ([(w, h), (w - 260, h), (w - 90, h - 240), (w, h - 160)], (210, 22, 30)),
    ]

    for poly, col in shards:
        draw.polygon(poly, fill=col)

    draw.line([(0, 120), (w, 360)], fill=(225, 24, 34, 180), width=4)
    draw.line([(0, h - 320), (w, h - 140)], fill=(225, 24, 34, 180), width=3)


def draw_slanted_text(
    base_img: Image.Image,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple,
    center_pos: tuple[int, int],
    slant_k: float = 0.22,
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
    # Matrix maps output (x, y) to input (x, y): x_in = x - k*(h - y)
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
    img = Image.new("RGB", (width, height), color=(8, 8, 10))
    draw = ImageDraw.Draw(img)

    draw_goe_background(draw, width, height)

    font_top_emblem = _get_font(26, bold=True)
    font_main_title = _get_font(74, bold=True)
    font_sub_title = _get_font(25, bold=False)
    font_team_name = _get_font(28, bold=True)
    font_score = _get_font(84, bold=True)
    font_score_sub = _get_font(18, bold=True)
    font_vs = _get_font(38, bold=True)
    font_card_ch = _get_font(19, bold=True)
    font_card_det = _get_font(15, bold=False)
    font_footer_pipes = _get_font(16, bold=True)

    # Top Emblem
    draw.text(
        (width // 2, 60),
        "🎙️   |   WORLDS 2026",
        fill=(255, 255, 255),
        font=font_top_emblem,
        anchor="mm",
    )

    # Slanted Main Title (matching poster: CO-STREAM GOE)
    draw_slanted_text(
        img,
        "CO-STREAM GOE",
        font_main_title,
        (255, 24, 36),
        (width // 2, 135),
        slant_k=0.22,
    )

    platform_tag = f"[{platform.upper()}] " if platform.upper() != "ALL" else ""
    draw.text(
        (width // 2, 185),
        f"w Kieleckim bunkrze vs Nervarien  •  {platform_tag}{data.get('timestamp', '').split(' ')[-1]}",
        fill=(255, 255, 255),
        font=font_sub_title,
        anchor="mm",
    )

    # Filter streams if platform is specified
    goe_raw = data["groups"].get("GOE", {}).get("streams", [])
    nerva_raw = data["groups"].get("NERVA", {}).get("streams", [])

    if platform.upper() == "TWITCH":
        goe_streams = [s for s in goe_raw if s["platform"] == "Twitch"]
        nerva_streams = [s for s in nerva_raw if s["platform"] == "Twitch"]
    elif platform.upper() == "YOUTUBE":
        goe_streams = [s for s in goe_raw if s["platform"] == "YouTube"]
        nerva_streams = [s for s in nerva_raw if s["platform"] == "YouTube"]
    else:
        goe_streams = goe_raw
        nerva_streams = nerva_raw

    goe_total = sum(s.get("viewers", 0) for s in goe_streams)
    nerva_total = sum(s.get("viewers", 0) for s in nerva_streams)
    tot = goe_total + nerva_total
    goe_pct = round((goe_total / tot * 100), 1) if tot > 0 else 50.0
    nerva_pct = round((nerva_total / tot * 100), 1) if tot > 0 else 50.0

    # GOE Box
    draw.rounded_rectangle(
        [50, 230, 485, 470],
        radius=14,
        fill=(14, 14, 18),
        outline=(255, 24, 36),
        width=3,
    )
    draw.text((75, 255), "GOE", fill=(255, 24, 36), font=font_team_name)
    draw.text(
        (75, 305),
        f"{goe_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (75, 415),
        f"{goe_pct}% WIDZÓW",
        fill=(255, 255, 255) if goe_total >= nerva_total else (160, 160, 170),
        font=font_score_sub,
    )

    # VS Center
    draw.ellipse(
        [width // 2 - 40, 315, width // 2 + 40, 395],
        fill=(14, 14, 18),
        outline=(255, 24, 36),
        width=3,
    )
    draw.text((width // 2, 355), "VS", fill=(255, 255, 255), font=font_vs, anchor="mm")

    # NERVA Box
    draw.rounded_rectangle(
        [595, 230, 1030, 470],
        radius=14,
        fill=(14, 14, 18),
        outline=(255, 24, 36),
        width=3,
    )
    draw.text((620, 255), "NERVARIEN", fill=(255, 255, 255), font=font_team_name)
    draw.text(
        (620, 305),
        f"{nerva_total:,}".replace(",", " "),
        fill=(255, 255, 255),
        font=font_score,
    )
    draw.text(
        (620, 415),
        f"{nerva_pct}% WIDZÓW",
        fill=(160, 160, 170),
        font=font_score_sub,
    )

    # Proportional Bar
    bar_x1, bar_y1, bar_x2, bar_y2 = 50, 495, 1030, 520
    draw.rounded_rectangle(
        [bar_x1, bar_y1, bar_x2, bar_y2],
        radius=6,
        fill=(25, 25, 32),
        outline=(255, 24, 36),
        width=1,
    )
    bar_w = bar_x2 - bar_x1
    goe_w = int(bar_w * (goe_pct / 100.0))
    goe_w = max(10, min(bar_w - 10, goe_w))
    draw.rounded_rectangle(
        [bar_x1, bar_y1, bar_x1 + goe_w, bar_y2], radius=6, fill=(255, 24, 36)
    )

    # Stream Cards with Avatars
    all_streams = [("GOE", st) for st in goe_streams] + [
        ("NERVA", st) for st in nerva_streams
    ]

    y_pos = 555
    card_h = 100 if len(all_streams) <= 5 else 85

    for grp_tag, st in all_streams:
        # Main container with red border
        draw.rounded_rectangle(
            [50, y_pos, 1030, y_pos + card_h],
            radius=10,
            fill=(12, 12, 16),
            outline=(255, 24, 36),
            width=2,
        )

        # Avatar Box (matching the studio facecams from poster)
        av_size = (card_h - 24, card_h - 24)
        av_img = get_cached_avatar(st["id"], st.get("avatar_url", ""), size=av_size)
        av_x = 65
        av_y = y_pos + 12

        # Paste avatar
        img.paste(av_img, (av_x, av_y), av_img)
        # Red frame around avatar
        draw.rounded_rectangle(
            [av_x - 1, av_y - 1, av_x + av_size[0] + 1, av_y + av_size[1] + 1],
            radius=4,
            outline=(255, 24, 36),
            width=2,
        )

        content_x = av_x + av_size[0] + 18

        # Platform badge
        is_twitch = st["platform"] == "Twitch"
        badge_bg = (145, 70, 255) if is_twitch else (225, 24, 36)
        draw.rounded_rectangle(
            [content_x, y_pos + 16, content_x + 85, y_pos + 42],
            radius=4,
            fill=badge_bg,
        )
        draw.text(
            (content_x + 42, y_pos + 29),
            st["platform"],
            fill=(255, 255, 255),
            font=font_card_det,
            anchor="mm",
        )

        # Team Tag
        draw.rounded_rectangle(
            [content_x + 95, y_pos + 16, content_x + 180, y_pos + 42],
            radius=4,
            fill=(255, 24, 36) if grp_tag == "GOE" else (40, 40, 50),
        )
        draw.text(
            (content_x + 137, y_pos + 29),
            grp_tag,
            fill=(255, 255, 255),
            font=font_card_det,
            anchor="mm",
        )

        # Channel name & Live dot
        status_dot = "🔴" if st["is_live"] else "⚫"
        draw.text(
            (content_x + 195, y_pos + 18),
            f"{status_dot}  {st['channel']}",
            fill=(255, 255, 255),
            font=font_card_ch,
        )

        # Title snippet
        raw_title = st.get("title") or st.get("category") or "Transmisja na żywo"
        title_snippet = raw_title[:60] + ("..." if len(raw_title) > 60 else "")
        draw.text(
            (content_x, y_pos + 56),
            title_snippet,
            fill=(180, 180, 190),
            font=font_card_det,
        )

        # Viewers on right
        viewers_str = (
            f"{st['viewers']:,} widzów".replace(",", " ")
            if st["is_live"]
            else "OFFLINE"
        )
        viewers_col = (255, 255, 255) if st["is_live"] else (120, 120, 130)
        draw.text(
            (1010, y_pos + 32),
            viewers_str,
            fill=viewers_col,
            font=font_card_ch,
            anchor="rm",
        )

        y_pos += card_h + 14

    # Footer - GoE Roster Pipes & #bunkier
    roster_pipes = (
        "DEJF | CZARNYPIOTRUS | BIALITO | MAJUTEK | PEDRO | MAGVAYER | JASKIER"
    )
    draw.text(
        (width // 2, 1250),
        roster_pipes,
        fill=(255, 255, 255),
        font=font_footer_pipes,
        anchor="mm",
    )
    draw.text(
        (width // 2, 1285),
        "#bunkier",
        fill=(255, 24, 36),
        font=_get_font(22, bold=True),
        anchor="mm",
    )

    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    from scraper import fetch_all_data

    data = fetch_all_data()
    out = create_battle_card(data, "infographsbot/battle_card.png")
    print(f"Card saved with avatars and slanted text: {out}")
