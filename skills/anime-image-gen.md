---
name: anime-image-gen
description: 使用 wuyinkeji API 生成图片，并支持先上传参考图到华为云 OBS，再用参考图 URL 调用 wuyinkeji 生成高一致性角色/风格图片。
---

# Anime Image Gen · 二次元图片生成技能

## 能做什么

1. **纯文生图**：直接调用 wuyinkeji API 生成图片。
2. **参考图生图**：把本地参考图上传到 OBS 拿到公开 URL，再传给 wuyinkeji 作为参考，生成风格/角色一致的新图片。

## 前置依赖

项目根目录 `.env` 需包含：

```bash
WUYINKEJI_KEY=your_key_here
OBS_ACCESS_KEY_ID=your_key_here
OBS_SECRET_ACCESS_KEY=your_key_here
OBS_ENDPOINT=obs.ap-southeast-1.myhuaweicloud.com
OBS_BUCKET=your_bucket_here
OBS_DOMAIN=your_bucket_here.obs.ap-southeast-1.myhuaweicloud.com
```

Python 依赖：

```bash
pip install requests python-dotenv esdk-obs-python
```

## 工作流

### 1. 直接生成图片

```bash
PYTHONPATH=. python3 core/imagegen.py "anime girl, purple twin tails, tech suit"
```

或写 Python：

```python
from core.imagegen import generate_image, save_image

img_bytes, source = generate_image(
    prompt="anime girl, purple twin tails, tech suit",
    size="1:1",
)
save_image(img_bytes, "outputs/result.png")
```

### 2. 参考图生图（保持角色一致）

```bash
PYTHONPATH=. python3 scripts/generate_with_reference.py \
  --ref /path/to/ref.jpg \
  --prompt "same character, smiling, holding a laptop" \
  --out outputs/consistent.png
```

流程：

1. 读取本地参考图
2. 上传到 OBS `anime-pipeline/references/<timestamp>.jpg`
3. 拿到公开 URL
4. 调用 `generate_image(prompt, ref_urls=[url])`
5. 保存生成结果到 `--out`

## Python API

```python
from core.imagegen import generate_image, save_image
from core.obs import upload_reference

# 上传参考图
ref_url = upload_reference(
    "/path/to/ref.jpg",
    "anime-pipeline/references/my_ref.jpg"
)

# 带参考图生成
img_bytes, source = generate_image(
    prompt="same anime character, different pose",
    size="1:1",
    ref_urls=[ref_url] if ref_url else None,
)

save_image(img_bytes, "outputs/output.png")
```

## 最佳实践

- **参考图必须是公开 URL**：wuyinkeji 只能访问公网可下载的图片，所以个人图片一定要先传 OBS。
- **一次最多传几张参考图**：wuyinkeji `urls` 字段支持数组，可传 1-3 张。
- **prompt 要强调一致性**：如 `"same character", "consistent style"`, `"same outfit"`。
- **输出目录**：统一放到 `outputs/` 或 `characters/outputs/`，不要写项目根目录。
- **动漫内容安全**：禁止恐怖、血腥、过度暴露、恐怖谷等不适内容。

## CLI：OBS 操作

```bash
# 上传任意文件到 OBS
PYTHONPATH=. python3 -m core.obs upload /path/to/ref.jpg anime-pipeline/refs/ref01.jpg

# 列出 OBS 上的对象
PYTHONPATH=. python3 -m core.obs list anime-pipeline/

# 获取公开 URL
PYTHONPATH=. python3 -m core.obs url anime-pipeline/refs/ref01.jpg
```

## 错误处理

`generate_image` 在以下情况会直接抛出异常：

- `requests` 未安装
- `.env` 中 `WUYINKEJI_KEY` 未配置
- wuyinkeji API 返回错误或被拒绝
- 超过 `timeout` 时间仍未完成

调用方应自行捕获异常并决定后续处理。
