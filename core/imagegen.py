"""
core/imagegen.py — wuyinkeji 图片生成（转发 shim）

实现已收敛到全局唯一真相源：~/.agents/skills/wuyinkeji-imagegen/scripts/wuyinkeji_gen.py
本文件只保留项目历史签名（ref_urls 参数名、(bytes, "wuyinkeji") 元组返回值），不含实现。
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.environ.get("AGENT_SKILLS_HOME", os.path.expanduser("~/.agents/skills")),
    "wuyinkeji-imagegen", "scripts"))

from wuyinkeji_gen import generate_image as _generate, save_image  # noqa: F401,E402


def generate_image(
    prompt: str,
    size: str = "1:1",
    timeout: int = 300,
    ref_urls: list | None = None,
) -> tuple:
    """生成图片，返回 (image_bytes, "wuyinkeji")。"""
    return _generate(prompt, size=size, timeout=timeout, urls=ref_urls), "wuyinkeji"
