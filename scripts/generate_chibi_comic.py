#!/usr/bin/env python3
"""
scripts/generate_chibi_comic.py — Generate a Q版 duo manga page.

Usage:
    PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
        --scenario trillion-model \
        --size 16:9 \
        --out outputs/chibi_comic/

Output:
    outputs/chibi_comic/<scenario>/
    ├── base.png              # raw wuyinkeji output
    ├── page_01_intro.png     # final manga page with borders + text
    └── page_01_intro.json    # panel metadata, prompts, dialogue
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont

from core.imagegen import generate_image, save_image

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "characters" / "reference_manifest.json"


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_chibi_refs(manifest: dict) -> list[str]:
    """Return both characters' chibi-model-sheet URLs."""
    chars = manifest.get("characters", {})
    return [
        chars["ascend-chan"]["chibi-model-sheet"],
        chars["kunpeng-kun"]["chibi-model-sheet"],
    ]


def build_prompt() -> str:
    return (
        "Japanese manga comic page, 2 rows by 3 columns, 6 panels total, "
        "right-to-left reading order, clean black panel borders, white gutters. "
        "Same two chibi characters consistently across all panels, super deformed big heads small bodies. "
        "Panel 1 top-right: both characters standing together on a cloud data platform, heroic intro pose, "
        "Kunpeng-kun on left silver-white hair blue coat small data wings, "
        "Ascend-chan on right purple twin tails orange gradient tips tiny AI drones, bright sparkles. "
        "Panel 2 top-middle: Ascend-chan close-up winking confidently with one hand on hip, cheerful energetic. "
        "Panel 3 top-left: Kunpeng-kun close-up arms crossed, calm reliable gentle smile. "
        "Panel 4 bottom-right: Ascend-chan dynamic action pose with orange neuron energy aura, excited shouting expression, tiny AI drones flying around. "
        "Panel 5 bottom-middle: Kunpeng-kun spreading semi-transparent blue data wings wide, forming a stable platform, protective stance. "
        "Panel 6 bottom-left: both characters high-fiving, Ascend-chan jumping with joy, Kunpeng-kun smiling warmly, sparkles and data particles. "
        "Clean chibi anime style, bold outlines, soft cel-shading, no text, no speech bubbles, leave empty areas for captions."
    )


def get_panel_content() -> list[dict]:
    return [
        {
            "type": "narration",
            "text": "在计算联邦，有一对最佳搭档——\n通用计算大哥鲲鹏君 和 AI算力小妹昇腾酱。",
            "pos": "top",
        },
        {
            "type": "speech",
            "speaker": "昇腾酱",
            "text": "让我来！万亿参数大模型，\n一秒搞定！",
            "pos": "bottom",
        },
        {
            "type": "speech",
            "speaker": "鲲鹏君",
            "text": "别急，先想清楚再动手。",
            "pos": "bottom",
        },
        {
            "type": "speech",
            "speaker": "昇腾酱",
            "text": "算力即正义！训练？推理？\n全都交给我！",
            "pos": "top",
        },
        {
            "type": "speech",
            "speaker": "鲲鹏君",
            "text": "交给我，稳的。",
            "pos": "top",
        },
        {
            "type": "speech",
            "speaker": "昇腾酱",
            "text": "赢了！我果然是最强的！",
            "pos": "top",
            "extra": "鲲鹏君：嗯，你最行。",
        },
    ]


def load_fonts():
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
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_centered(draw, text, box, font, fill="black"):
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


def add_comic_layout(base_path: Path, out_path: Path, meta_path: Path):
    base = Image.open(base_path)
    W, H = base.size
    header_h = 80

    img = Image.new("RGB", (W, H + header_h), "white")
    img.paste(base, (0, header_h))

    title_font, bubble_font, small_font = load_fonts()
    draw = ImageDraw.Draw(img)

    title_text = "计算联邦日常 · 第1话"
    tb = draw.textbbox((0, 0), title_text, font=title_font)
    draw.text(((W - (tb[2] - tb[0])) // 2, 20), title_text, font=title_font, fill="black")

    hint = "阅读顺序：从右至左 →"
    hb = draw.textbbox((0, 0), hint, font=small_font)
    draw.text((W - (hb[2] - hb[0]) - 20, 60), hint, font=small_font, fill="black")

    col_w = W // 3
    col_h = H // 2
    header = header_h
    panels = {
        "top_left": (0, header, col_w, header + col_h),
        "top_center": (col_w, header, 2 * col_w, header + col_h),
        "top_right": (2 * col_w, header, W, header + col_h),
        "bottom_left": (0, header + col_h, col_w, header + H),
        "bottom_center": (col_w, header + col_h, 2 * col_w, header + H),
        "bottom_right": (2 * col_w, header + col_h, W, header + H),
    }
    reading_order = ["top_right", "top_center", "top_left", "bottom_right", "bottom_center", "bottom_left"]
    panel_content = get_panel_content()

    for idx, panel_key in enumerate(reading_order):
        content = panel_content[idx]
        x1, y1, x2, y2 = panels[panel_key]
        margin = 12

        draw.text((x2 - 28, y1 + 8), f"{idx + 1}", font=bubble_font, fill="black")

        if content["type"] == "narration":
            box_w = (x2 - x1) - 2 * margin
            box_h = 55
            bx1 = x1 + margin
            by1 = y1 + margin + 35
            bx2 = bx1 + box_w
            by2 = by1 + box_h
            draw_rounded_rect(draw, (bx1, by1, bx2, by2), fill="white", outline="black", radius=10, width=2)
            draw_text_centered(draw, content["text"], (bx1 + 8, by1 + 5, bx2 - 8, by2 - 5), bubble_font)
        else:
            full_text = f'{content["speaker"]}：{content["text"]}'
            lines = full_text.split("\n")
            max_w = max(draw.textbbox((0, 0), line, font=bubble_font)[2] - draw.textbbox((0, 0), line, font=bubble_font)[0] for line in lines)
            text_w = min(max_w + 24, x2 - x1 - 2 * margin)
            text_h = len(lines) * 30 + 16

            if content["pos"] == "top":
                bx1, by1 = x1 + margin, y1 + margin + 35
            else:
                bx1, by1 = x1 + margin, y2 - text_h - margin - 10
            bx2, by2 = bx1 + text_w, by1 + text_h

            draw_rounded_rect(draw, (bx1, by1, bx2, by2), fill="white", outline="black", radius=12, width=2)
            draw_text_centered(draw, full_text, (bx1 + 8, by1 + 5, bx2 - 8, by2 - 5), bubble_font)

            if "extra" in content:
                extra_lines = content["extra"].split("\n")
                emax_w = max(draw.textbbox((0, 0), line, font=bubble_font)[2] - draw.textbbox((0, 0), line, font=bubble_font)[0] for line in extra_lines)
                ew = min(emax_w + 24, x2 - x1 - 2 * margin)
                eh = len(extra_lines) * 30 + 16
                ex1, ey1 = x2 - ew - margin, y2 - eh - margin - 10
                ex2, ey2 = x2 - margin, y2 - margin - 10
                draw_rounded_rect(draw, (ex1, ey1, ex2, ey2), fill="white", outline="black", radius=12, width=2)
                draw_text_centered(draw, content["extra"], (ex1 + 8, ey1 + 5, ex2 - 8, ey2 - 5), bubble_font)

    img.save(out_path)
    metadata = {
        "title": "计算联邦日常 · 第1话",
        "panels": [{"order": i + 1, "panel": reading_order[i], **panel_content[i]} for i in range(6)],
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def main():
    p = argparse.ArgumentParser(description="Generate a Q版 duo manga page")
    p.add_argument("--scenario", default="trillion-model", help="Scenario slug for output folder")
    p.add_argument("--size", default="16:9", help="Image size ratio")
    p.add_argument("--out", default="outputs/chibi_comic", help="Output directory")
    p.add_argument("--timeout", type=int, default=600, help="wuyinkeji timeout")
    args = p.parse_args()

    manifest = load_manifest()
    ref_urls = get_chibi_refs(manifest)

    out_dir = Path(args.out) / args.scenario
    out_dir.mkdir(parents=True, exist_ok=True)
    base_path = out_dir / "base.png"
    page_path = out_dir / "page_01_intro.png"
    meta_path = out_dir / "page_01_intro.json"

    print(f"🎨 Generating base manga page with {len(ref_urls)} references...")
    prompt = build_prompt()
    img_bytes, source = generate_image(prompt=prompt, size=args.size, timeout=args.timeout, ref_urls=ref_urls)
    save_image(img_bytes, str(base_path))
    print(f"  ✅ Saved base ({source}, {len(img_bytes) // 1024}KB): {base_path}")

    print("📝 Adding manga layout, borders, and Chinese text...")
    add_comic_layout(base_path, page_path, meta_path)
    print(f"  ✅ Saved page: {page_path}")
    print(f"  ✅ Saved metadata: {meta_path}")


if __name__ == "__main__":
    main()
