#!/usr/bin/env python3
"""
scripts/generate_with_reference.py — Generate image using a reference image.

Uploads the reference image to OBS first, then calls wuyinkeji with the public URL
to produce a character/style-consistent new image.

Usage:
    PYTHONPATH=. python3 scripts/generate_with_reference.py \
        --ref /path/to/ref.jpg \
        --prompt "same character, smiling, holding a laptop" \
        --out outputs/consistent.png
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.imagegen import generate_image, save_image
from core.obs import upload_reference


def slugify(text: str) -> str:
    import re
    return re.sub(r"[^\w\-]+", "_", text).strip("_")[:50]


def main():
    p = argparse.ArgumentParser(description="Generate image from reference")
    p.add_argument("--ref", required=True, help="Path to local reference image")
    p.add_argument("--prompt", required=True, help="Generation prompt")
    p.add_argument("--out", default="outputs/ref_based.png", help="Output image path")
    p.add_argument("--size", default="1:1", help="Image size ratio")
    p.add_argument("--remote-key", default="", help="Optional OBS remote key")
    args = p.parse_args()

    ref_path = Path(args.ref)
    if not ref_path.exists():
        print(f"Reference image not found: {args.ref}")
        sys.exit(1)

    remote_key = args.remote_key or f"动漫制作/references/{slugify(args.prompt)}/{int(time.time())}.jpg"
    ref_url = upload_reference(str(ref_path), remote_key)
    if not ref_url:
        print("Failed to upload reference image. Aborting.")
        sys.exit(1)

    print(f"  🎨 Generating with reference...")
    img_bytes, source = generate_image(
        prompt=args.prompt,
        size=args.size,
        ref_urls=[ref_url],
        timeout=300,
    )

    out_path = save_image(img_bytes, args.out)
    print(f"  ✅ Saved ({source}, {len(img_bytes)//1024}KB): {out_path}")


if __name__ == "__main__":
    main()
