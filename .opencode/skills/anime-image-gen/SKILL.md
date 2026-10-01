---
name: anime-image-gen
description: 动漫制作项目专属的图片/漫画生成流程——Q版双人漫画页（scenarios YAML → 6 格日漫）、参考图一致性生图的项目约定（角色 id、提示词规范、输出结构）。底层 wuyinkeji 生图与 OBS 上传实现已收敛到全局 skill wuyinkeji-imagegen，本 skill 只定义项目特定的风格与工作流。当用户在动漫制作项目内要求生成图片、漫画页、参考图一致性生图时使用；通用生图需求直接用全局 wuyinkeji-imagegen。
---

# Anime Image Gen · 二次元图片生成技能

## 能做什么

1. **纯文生图**：调用全局 wuyinkeji-imagegen 生成图片。
2. **参考图生图**：本地参考图上传 OBS 拿公网 URL，再传给 wuyinkeji 生成风格/角色一致的新图片。
3. **Q版双人漫画页**：读取 `scenarios/*.yaml` 剧情脚本，生成横屏（16:9）或竖屏（9:16）6 格日漫页面，并用 PIL 叠加标题、对白气泡和旁白。

## 架构说明（2026-09 收敛后）

- 生图与 OBS 的**实现**在全局 skill：`~/.agents/skills/wuyinkeji-imagegen/scripts/`（`wuyinkeji_gen.py` + `obs_util.py`），是唯一真相源
- 项目内 `core/imagegen.py` 和 `core/obs.py` 只是**转发 shim**，不要在里面写实现
- 本文件只定义**项目特定**内容：角色、风格提示词、漫画流程、输出约定

## 前置依赖

项目根目录 `.env`（或全局 shell 环境变量）需包含：

```bash
WUYINKEJI_KEY=your_key_here
OBS_ACCESS_KEY_ID=your_key_here
OBS_SECRET_ACCESS_KEY=your_key_here
```

Python 依赖：`requests python-dotenv esdk-obs-python pyyaml pillow`

## 工作流

### 1. 直接生成图片

```bash
python3 ~/.agents/skills/wuyinkeji-imagegen/scripts/wuyinkeji_gen.py \
  "anime girl, purple twin tails, tech suit" outputs/result.png --size 1:1
```

或写 Python（经项目 shim，保持历史签名）：

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

流程：读取本地参考图 → 上传 OBS 拿公网 URL → `generate_image(prompt, ref_urls=[url])` → 保存到 `--out`。

## Python API

```python
from core.imagegen import generate_image, save_image
from core.obs import upload_reference

ref_url = upload_reference("/path/to/ref.jpg", "动漫制作/references/my_ref.jpg")

img_bytes, source = generate_image(
    prompt="same anime character, different pose",
    size="1:1",
    ref_urls=[ref_url] if ref_url else None,
)
save_image(img_bytes, "outputs/output.png")
```

## 最佳实践

- **参考图必须是公开 URL**：个人图片先传 OBS，wuyinkeji 只能访问公网图片
- **一次最多 1-3 张参考图**（`urls` 数组）
- **prompt 强调一致性**：`"same character"`, `"consistent style"`, `"same outfit"`
- **输出目录**：统一放 `outputs/` 或 `characters/outputs/`
- **内容安全**：禁止恐怖、血腥、过度暴露、恐怖谷等不适内容

## CLI：OBS 操作

```bash
# 上传任意文件到 OBS
PYTHONPATH=. python3 -m core.obs upload /path/to/ref.jpg 动漫制作/refs/ref01.jpg

# 列出 OBS 上的对象
PYTHONPATH=. python3 -m core.obs list 动漫制作/

# 获取公开 URL
PYTHONPATH=. python3 -m core.obs url 动漫制作/refs/ref01.jpg

# 设置自动删除（按前缀，N 天后自动清理）
PYTHONPATH=. python3 -m core.obs set-lifecycle 动漫制作/ 3
```

> `set-lifecycle` 由 shim 自动映射到 canonical 的 `lifecycle ensure`，行为不变：先读现有规则、追加匹配规则、再写回，不同前缀可有多条规则。

## 漫画 / 小剧场生成

基于 `scenarios/*.yaml` 剧情脚本生成 6 格 Q版日漫页。

```bash
# 横屏 16:9
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml --layout landscape --date 2026-07-07

# 竖屏 9:16
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml --layout portrait --date 2026-07-07
```

### 输出结构

```
outputs/chibi_comic/<scenario>/<YYYY-MM-DD>_<layout>/
├── base.png          # wuyinkeji 原始底图
├── page.png          # 加过分镜框、气泡、文字的成品
└── page.json         # 分镜元数据、台词
```

### 新增一话

复制 `scenarios/trillion-model.yaml`，修改：

- `id`: 主题目录名
- `title`: 页面标题
- `prompt.panels`: 6 个 panel 的画面描述
- `content`: 6 个 panel 的台词/旁白（按右→左、上→下阅读顺序）

`content` 中 `speaker` 使用角色 id（`ascend-chan` / `kunpeng-kun`），脚本自动映射为中文名。

## 错误处理

`generate_image` 在以下情况直接抛异常，调用方自行捕获：

- `requests` 未安装 / `WUYINKEJI_KEY` 未配置
- wuyinkeji 返回错误、内容被拒（status=-1）、服务端失败（status=3）
- 超过 `timeout` 未完成
