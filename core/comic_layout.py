"""
core/comic_layout.py — PIL-based manga page layout engine.

Supports horizontal (16:9, 2×3) and vertical (9:16, 3×2) grids,
right-to-left reading order, narration boxes and speech bubbles.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_fonts():
    """Return (title_font, bubble_font, small_font) using system CJK fallbacks."""
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    font_path = None
    for c in candidates:
        if Path(c).exists():
            font_path = c
            break

    if font_path:
        return (
            ImageFont.truetype(font_path, 40),
            ImageFont.truetype(font_path, 22),
            ImageFont.truetype(font_path, 16),
        )
    return ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()


def draw_rounded_rect(draw, xy, fill, outline=None, radius=15, width=2):
    """Draw a rounded rectangle (PIL >= 8.0)."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_centered(draw, text, box, font, fill="black"):
    """Draw multi-line text centered inside a bounding box."""
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    bbox = draw.textbbox((0, 0), "Aa", font=font)
    line_h = bbox[3] - bbox[1] + 4
    total_h = len(lines) * line_h
    start_y = y1 + (y2 - y1 - total_h) // 2
    for i, line in enumerate(lines):
        lb = draw.textbbox((0, 0), line, font=font)
        tw = lb[2] - lb[0]
        x = x1 + (x2 - x1 - tw) // 2
        y = start_y + i * line_h
        draw.text((x, y), line, font=font, fill=fill)


def panel_layout(W: int, H: int, layout: str, header_h: int = 80):
    """
    Compute panel boxes and right-to-left reading order.

    Args:
        W, H: base image size (without header).
        layout: "landscape" (2 rows x 3 cols) or "portrait" (3 rows x 2 cols).
        header_h: height reserved for the title header above the base image.

    Returns:
        {
            "reading_order": list of panel keys in reading order,
            "boxes": dict mapping panel key -> (x1, y1, x2, y2),
            "panel_names": list of panel keys,
        }
    """
    if layout == "landscape":
        cols, rows = 3, 2
        panel_keys = [
            "top_right",
            "top_center",
            "top_left",
            "bottom_right",
            "bottom_center",
            "bottom_left",
        ]
    elif layout == "portrait":
        cols, rows = 2, 3
        panel_keys = [
            "r0_c1",
            "r0_c0",
            "r1_c1",
            "r1_c0",
            "r2_c1",
            "r2_c0",
        ]
    else:
        raise ValueError(f"Unknown layout: {layout}")

    col_w = W // cols
    row_h = H // rows
    boxes = {}
    for r in range(rows):
        for c in range(cols):
            x1 = c * col_w
            y1 = header_h + r * row_h
            x2 = W if c == cols - 1 else (c + 1) * col_w
            y2 = header_h + H if r == rows - 1 else header_h + (r + 1) * row_h
            key = panel_keys[r * cols + (cols - 1 - c)]
            boxes[key] = (x1, y1, x2, y2)

    return {
        "reading_order": panel_keys,
        "boxes": boxes,
        "panel_names": panel_keys,
    }


def _draw_bubble(draw, box, text, font):
    """Draw a single white rounded bubble with centered text."""
    draw_rounded_rect(draw, box, fill="white", outline="black", radius=12, width=2)
    draw_text_centered(draw, text, (box[0] + 8, box[1] + 5, box[2] - 8, box[3] - 5), font)


def add_comic_layout(
    base_path: Path,
    out_path: Path,
    meta_path: Path,
    title: str,
    content: list[dict],
    layout: str = "landscape",
):
    """
    Overlay panel numbers, narration boxes and speech bubbles onto a manga base image.

    Args:
        base_path: path to raw wuyinkeji output.
        out_path: path for final PNG.
        meta_path: path for sidecar JSON metadata.
        title: page title shown in the header.
        content: list of 6 panel content dicts (narration/speech).
        layout: "landscape" or "portrait".
    """
    base = Image.open(base_path)
    W, H = base.size
    header_h = 80

    img = Image.new("RGB", (W, H + header_h), "white")
    img.paste(base, (0, header_h))

    title_font, bubble_font, small_font = load_fonts()
    draw = ImageDraw.Draw(img)

    # Title
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - (tb[2] - tb[0])) // 2, 20), title, font=title_font, fill="black")

    # Reading order hint
    hint = "阅读顺序：从右至左 →"
    hb = draw.textbbox((0, 0), hint, font=small_font)
    draw.text((W - (hb[2] - hb[0]) - 20, 60), hint, font=small_font, fill="black")

    layout_info = panel_layout(W, H, layout, header_h=header_h)
    reading_order = layout_info["reading_order"]
    boxes = layout_info["boxes"]

    for idx, panel_key in enumerate(reading_order):
        item = content[idx]
        x1, y1, x2, y2 = boxes[panel_key]
        margin = 10

        # Panel number
        draw.text((x2 - 28, y1 + 8), f"{idx + 1}", font=bubble_font, fill="black")

        if item["type"] == "narration":
            box_w = (x2 - x1) - 2 * margin
            box_h = 55
            bx1 = x1 + margin
            by1 = y1 + margin + 35
            bx2 = bx1 + box_w
            by2 = by1 + box_h
            draw_rounded_rect(
                draw, (bx1, by1, bx2, by2), fill="white", outline="black", radius=10, width=2
            )
            draw_text_centered(
                draw, item["text"], (bx1 + 8, by1 + 5, bx2 - 8, by2 - 5), bubble_font
            )
        else:
            full_text = f'{item["speaker"]}：{item["text"]}'
            lines = full_text.split("\n")
            max_w = max(
                draw.textbbox((0, 0), line, font=bubble_font)[2]
                - draw.textbbox((0, 0), line, font=bubble_font)[0]
                for line in lines
            )
            text_w = min(max_w + 24, x2 - x1 - 2 * margin)
            text_h = len(lines) * 30 + 16

            if item.get("pos") == "top":
                bx1, by1 = x1 + margin, y1 + margin + 35
            else:
                bx1, by1 = x1 + margin, y2 - text_h - margin - 10
            bx2, by2 = bx1 + text_w, by1 + text_h

            _draw_bubble(draw, (bx1, by1, bx2, by2), full_text, bubble_font)

            if "extra" in item:
                extra_lines = item["extra"].split("\n")
                emax_w = max(
                    draw.textbbox((0, 0), line, font=bubble_font)[2]
                    - draw.textbbox((0, 0), line, font=bubble_font)[0]
                    for line in extra_lines
                )
                ew = min(emax_w + 24, x2 - x1 - 2 * margin)
                eh = len(extra_lines) * 30 + 16
                ex1 = x2 - ew - margin
                ey1 = y2 - eh - margin - 10
                ex2 = x2 - margin
                ey2 = y2 - margin - 10
                _draw_bubble(draw, (ex1, ey1, ex2, ey2), item["extra"], bubble_font)

    img.save(out_path)

    metadata = {
        "title": title,
        "layout": layout,
        "panels": [
            {"order": i + 1, "panel": reading_order[i], **content[i]}
            for i in range(len(reading_order))
        ],
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
