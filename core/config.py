"""
core/config.py — API keys + environment configuration for 动漫制作

Reads keys from `.env` at project root.
"""
import os
from dotenv import load_dotenv

# Load .env from project root
_dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'
)
load_dotenv(_dotenv_path)

# ── wuyinkeji (AI image generation) ──
WUYINKEJI_KEY = os.environ.get("WUYINKEJI_KEY", "")
WUYINKEJI_BASE = "https://api.wuyinkeji.com/api/async"
WUYINKEJI_SUBMIT_URL = f"{WUYINKEJI_BASE}/image_gpt"
WUYINKEJI_DETAIL_URL = f"{WUYINKEJI_BASE}/detail"

WUYINKEJI_SIZE_MAP = {
    "16:9": "16:9", "1:1": "1:1", "4:3": "4:3",
    "3:2": "3:2", "2:3": "2:3", "9:16": "9:16",
    "21:9": "21:9", "3:4": "3:4", "auto": "auto",
}

# ── Huawei Cloud OBS (reference image storage) ──
OBS_ACCESS_KEY_ID = os.environ.get("OBS_ACCESS_KEY_ID", "")
OBS_SECRET_ACCESS_KEY = os.environ.get("OBS_SECRET_ACCESS_KEY", "")
OBS_ENDPOINT = os.environ.get("OBS_ENDPOINT", "obs.ap-southeast-1.myhuaweicloud.com")
OBS_BUCKET = os.environ.get("OBS_BUCKET", "")
OBS_DOMAIN = os.environ.get("OBS_DOMAIN", "")
OBS_CHARACTER_DIR = "characters"

# ── Project paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
