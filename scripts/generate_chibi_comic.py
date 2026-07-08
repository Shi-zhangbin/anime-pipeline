#!/usr/bin/env python3
"""
scripts/generate_chibi_comic.py — Generate a Q版 duo manga page from a scenario YAML.

Usage:
    # Default: landscape 16:9
    PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
        --scenario scenarios/trillion-model.yaml

    # Vertical 9:16
    PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
        --scenario scenarios/trillion-model.yaml \
        --layout portrait

    # Override output date / theme root
    PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
        --scenario scenarios/trillion-model.yaml \
        --date 2026-07-07 \
        --out outputs/chibi_comic/

Output:
    outputs/chibi_comic/<scenario>/<YYYY-MM-DD>_<layout>/
    ├── base.png              # raw wuyinkeji output
    ├── page.png              # final manga page with borders + text
    └── page.json             # panel metadata, prompts, dialogue
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import yaml
except ImportError:
    yaml = None

from core.imagegen import generate_image, save_image
from core.comic_layout import add_comic_layout

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "characters" / "reference_manifest.json"
ROLES_PATH = Path(__file__).resolve().parent.parent / "characters" / "roles.yaml"


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required: pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_manifest() -> dict:
    import json

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_roles() -> dict:
    return load_yaml(ROLES_PATH)


def resolve_ref_urls(manifest: dict, scenario: dict) -> list[str]:
    """Resolve scenario ref keys into stable OBS URLs for every character."""
    urls = []
    chars = manifest.get("characters", {})
    for char_id in scenario["characters"]:
        char_urls = chars.get(char_id, {})
        for ref_key in scenario.get("refs", []):
            url = char_urls.get(ref_key)
            if url:
                urls.append(url)
    return urls


def character_description(roles: dict, char_id: str) -> str:
    """Return a short English appearance prompt for a character."""
    char = roles.get("characters", {}).get(char_id, {})
    desc = char.get("appearance_prompt", "").strip()
    return desc or f"{char.get('name_en', char_id)} chibi character"


def build_prompt(scenario: dict, roles: dict, layout: str) -> str:
    """Build the full image generation prompt from scenario + roles."""
    prompt_cfg = scenario.get("prompt", {})

    # Character block
    char_block = "Two consistent chibi characters across all panels: "
    char_parts = []
    for char_id in scenario["characters"]:
        char = roles.get("characters", {}).get(char_id, {})
        name_en = char.get("name_en", char_id)
        desc = character_description(roles, char_id)
        char_parts.append(f"{name_en}: {desc}")
    char_block += "; ".join(char_parts) + "."

    # Grid description
    grid_key = "landscape_grid" if layout == "landscape" else "portrait_grid"
    grid_desc = prompt_cfg.get(grid_key, prompt_cfg.get("grid", ""))

    # Panel descriptions
    panel_texts = prompt_cfg.get("panels", [])
    panel_block = " ".join(f"Panel {i + 1}: {desc}" for i, desc in enumerate(panel_texts))

    parts = [
        prompt_cfg.get("base", ""),
        char_block,
        grid_desc,
        panel_block,
        prompt_cfg.get("style", ""),
    ]
    return " ".join(p.strip() for p in parts if p.strip())


def localize_content(content: list[dict], roles: dict) -> list[dict]:
    """Map speaker ids to Chinese names for bubble rendering."""
    char_names = {
        cid: info.get("name_cn", cid)
        for cid, info in roles.get("characters", {}).items()
    }
    localized = []
    for item in content:
        new_item = dict(item)
        if "speaker" in new_item:
            new_item["speaker"] = char_names.get(new_item["speaker"], new_item["speaker"])
        if "extra" in new_item:
            # e.g. "kunpeng-kun: ..." -> "鲲鹏君：..."
            for cid, cname in char_names.items():
                if new_item["extra"].startswith(f"{cid}:"):
                    new_item["extra"] = f"{cname}：" + new_item["extra"][len(cid) + 1:]
                    break
        localized.append(new_item)
    return localized


def main():
    p = argparse.ArgumentParser(description="Generate a Q版 duo manga page from a scenario")
    p.add_argument("--scenario", default="scenarios/trillion-model.yaml", help="Path to scenario YAML")
    p.add_argument("--layout", choices=["landscape", "portrait"], default="landscape", help="Page layout")
    p.add_argument("--size", default=None, help="Override image size ratio (e.g. 16:9, 9:16)")
    p.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Output date folder prefix")
    p.add_argument("--out", default="outputs/chibi_comic", help="Output root directory")
    p.add_argument("--timeout", type=int, default=600, help="wuyinkeji timeout")
    args = p.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_absolute() and not scenario_path.exists():
        # Try resolving under project root
        root = Path(__file__).resolve().parent.parent
        candidate = root / scenario_path
        if candidate.exists():
            scenario_path = candidate

    manifest = load_manifest()
    roles = load_roles()
    scenario = load_yaml(scenario_path)

    layout = args.layout
    if args.size:
        size = args.size
    elif layout == "portrait":
        size = "9:16"
    else:
        size = scenario.get("size", "16:9")

    ref_urls = resolve_ref_urls(manifest, scenario)
    prompt = build_prompt(scenario, roles, layout)

    out_dir = Path(args.out) / scenario["id"] / f"{args.date}_{layout}"
    out_dir.mkdir(parents=True, exist_ok=True)
    base_path = out_dir / "base.png"
    page_path = out_dir / "page.png"
    meta_path = out_dir / "page.json"

    print(f"🎨 Generating {layout} base manga page with {len(ref_urls)} references...")
    print(f"   size={size}, scenario={scenario['id']}, output={out_dir}")
    img_bytes, source = generate_image(prompt=prompt, size=size, timeout=args.timeout, ref_urls=ref_urls)
    save_image(img_bytes, str(base_path))
    print(f"  ✅ Saved base ({source}, {len(img_bytes) // 1024}KB): {base_path}")

    print("📝 Adding manga layout, borders, and Chinese text...")
    content = localize_content(scenario.get("content", []), roles)
    add_comic_layout(base_path, page_path, meta_path, scenario["title"], content, layout)
    print(f"  ✅ Saved page: {page_path}")
    print(f"  ✅ Saved metadata: {meta_path}")


if __name__ == "__main__":
    main()
