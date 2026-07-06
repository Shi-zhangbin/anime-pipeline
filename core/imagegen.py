"""
core/imagegen.py — wuyinkeji image generator

Supports reference image URLs for character-consistent generation.
No SVG fallback: failures are raised directly.
"""
import os, sys, time
from core.config import (
    WUYINKEJI_KEY,
    WUYINKEJI_SUBMIT_URL,
    WUYINKEJI_DETAIL_URL,
    WUYINKEJI_SIZE_MAP,
)

try:
    import requests
except ImportError:
    requests = None


def _wuyinkeji_generate(
    prompt: str,
    size: str = "1:1",
    timeout: int = 300,
    urls: list[str] | None = None,
) -> bytes:
    """Generate image via wuyinkeji async API. Returns image bytes."""
    if not requests:
        raise RuntimeError("requests not installed")
    if not WUYINKEJI_KEY:
        raise RuntimeError("WUYINKEJI_KEY not configured")

    api_size = WUYINKEJI_SIZE_MAP.get(size, "1:1")
    body = {"prompt": prompt, "size": api_size, "key": WUYINKEJI_KEY}
    if urls:
        body["urls"] = urls

    r = requests.post(WUYINKEJI_SUBMIT_URL, json=body, timeout=15)
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"wuyinkeji submit failed: {data.get('msg', '?')}")
    task_id = data["data"]["id"]

    wait = 3
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(wait)
        r = requests.get(
            WUYINKEJI_DETAIL_URL,
            params={"key": WUYINKEJI_KEY, "id": task_id},
            timeout=15,
        )
        resp = r.json()
        if resp.get("code") != 200:
            wait = min(wait * 1.5, 30)
            continue
        status = resp.get("data", {}).get("status", 0)
        if status == 2:
            result_urls = resp.get("data", {}).get("result", [])
            if result_urls:
                img_r = requests.get(result_urls[0], timeout=60)
                return img_r.content
            raise RuntimeError("wuyinkeji: no result URL returned")
        elif status == -1:
            raise RuntimeError("wuyinkeji: content rejected (status=-1)")
        wait = min(wait * 1.5, 30)

    raise TimeoutError(f"wuyinkeji: timeout after {timeout}s")


def generate_image(
    prompt: str,
    size: str = "1:1",
    timeout: int = 300,
    ref_urls: list[str] | None = None,
) -> tuple[bytes, str]:
    """
    Generate an image via wuyinkeji.

    Args:
        prompt: Image generation prompt.
        size: Aspect ratio string ("1:1", "16:9", etc.).
        timeout: Max seconds to wait for wuyinkeji async API.
        ref_urls: Optional list of public reference image URLs for consistent generation.

    Returns:
        (image_bytes, "wuyinkeji")

    Raises:
        RuntimeError: If requests is missing, key is missing, or API rejects the prompt.
        TimeoutError: If generation times out.
    """
    data = _wuyinkeji_generate(prompt, size, timeout=timeout, urls=ref_urls)
    return data, "wuyinkeji"


def save_image(img_bytes: bytes, output_path: str) -> str:
    """Save image bytes to disk, creating parent directories if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)
    return output_path


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a cute anime girl reading a book"
    data, source = generate_image(prompt, size="1:1")
    print(f"Source: {source}, size: {len(data)} bytes")
    out = "/tmp/test_anime_gen.jpg"
    save_image(data, out)
    print(f"Saved to {out}")
