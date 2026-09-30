"""
core/config.py — environment configuration for 动漫制作

加载项目根 `.env`；wuyinkeji / OBS 的实现与常量已收敛到全局 skill
（~/.agents/skills/wuyinkeji-imagegen/），本项目不再保留。
"""
import os
from dotenv import load_dotenv

# Load .env from project root
_dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'
)
load_dotenv(_dotenv_path)

# ── Project paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
