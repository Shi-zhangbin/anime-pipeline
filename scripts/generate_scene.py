#!/usr/bin/env python3
"""
scripts/generate_scene.py — Generate a scene image with automatic reference selection.

Loads the character reference manifest and picks the best 1-3 reference URLs
for the requested scene type, then calls wuyinkeji.

Usage:
    PYTHONPATH=. python3 scripts/generate_scene.py \
        --character ascend-chan \
        --scene-type wide \
        --prompt "Ascend-chan standing in a server room, pointing forward, neuron storm aura" \
        --out outputs/scenes/ascend_server_room.png
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.imagegen import generate_image, save_image

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "characters" / "reference_manifest.json"


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_refs(manifest: dict, character: str, scene_type: str) -> list[str]:
    """Resolve reference URLs for a character and scene type."""
    presets = manifest.get("scene_ref_presets", {})
    characters = manifest.get("characters", {})

    if character not in characters:
        raise ValueError(f"Unknown character: {character}. Known: {list(characters.keys())}")

    view_keys = presets.get(scene_type)
    if not view_keys:
        raise ValueError(f"Unknown scene_type: {scene_type}. Known: {list(presets.keys())}")

    refs = []
    for key in view_keys:
        url = characters[character].get(key, "")
        if url:
            refs.append(url)

    if not refs:
        raise RuntimeError(f"No reference URLs configured for {character}/{scene_type}. "
                           f"Please generate and upload reference images first.")

    return refs


def main():
    p = argparse.ArgumentParser(description="Generate a scene image with auto reference selection")
    p.add_argument("--character", required=True,
                   help="Character key, e.g. ascend-chan or kunpeng-kun")
    p.add_argument("--scene-type", default="wide",
                   help="Scene type: wide, dialogue, closeup, icon")
    p.add_argument("--prompt", required=True, help="Scene generation prompt")
    p.add_argument("--out", default="outputs/scene.png", help="Output image path")
    p.add_argument("--size", default="16:9", help="Image size ratio")
    p.add_argument("--timeout", type=int, default=300, help="wuyinkeji timeout")
    args = p.parse_args()

    manifest = load_manifest()
    ref_urls = get_refs(manifest, args.character, args.scene_type)

    print(f"  🎬 Scene: {args.scene_type} | Character: {args.character}")
    print(f"  📎 References ({len(ref_urls)}):")
    for url in ref_urls:
        print(f"     - {url}")

    img_bytes, source = generate_image(
        prompt=args.prompt,
        size=args.size,
        timeout=args.timeout,
        ref_urls=ref_urls,
    )

    out_path = save_image(img_bytes, args.out)
    print(f"  ✅ Saved ({source}, {len(img_bytes)//1024}KB): {out_path}")


if __name__ == "__main__":
    main()
