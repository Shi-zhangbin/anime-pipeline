---
name: anime-image-gen
description: 使用 wuyinkeji API 生成图片，支持先上传参考图到华为云 OBS 再用参考图 URL 调用 wuyinkeji 生成高一致性角色/风格图片；也支持基于 scenario YAML 批量生成 Q版双人漫画页。
---

# Anime Image Gen · 二次元图片生成技能

## 能做什么

1. **纯文生图**：直接调用 wuyinkeji API 生成图片。
2. **参考图生图**：把本地参考图上传到 OBS 拿到公开 URL，再传给 wuyinkeji 作为参考，生成风格/角色一致的新图片。
3. **Q版双人漫画页**：读取 `scenarios/*.yaml` 剧情脚本，自动生成横屏（16:9）或竖屏（9:16）6 格日漫页面，并用 PIL 叠加标题、对白气泡和旁白。

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
pip install requests python-dotenv esdk-obs-python pyyaml pillow
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

# 设置自动删除（按前缀）
PYTHONPATH=. python3 -m core.obs set-lifecycle anime-pipeline/ 3
```

`set-lifecycle` 会在桶上新增一条生命周期规则：指定前缀下的对象在 N 天后自动删除。例如上面的命令会让 `anime-pipeline/` 前缀下所有对象在 3 天后被 OBS 自动清理，不用手动删。

> 注意：`setBucketLifecycle` 是覆盖桶的生命周期配置，脚本会先读取现有规则、替换/追加同 id 的规则，再写回。不同前缀可以设置多条规则。

## 漫画 / 小剧场生成

基于 `scenarios/*.yaml` 剧情脚本生成 6 格 Q版日漫页。

### 横屏 16:9

```bash
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml \
  --layout landscape \
  --date 2026-07-07
```

### 竖屏 9:16

```bash
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml \
  --layout portrait \
  --date 2026-07-07
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

`content` 中 `speaker` 使用角色 id（`ascend-chan` / `kunpeng-kun`），脚本会自动映射为中文名。

## 错误处理

`generate_image` 在以下情况会直接抛出异常：

- `requests` 未安装
- `.env` 中 `WUYINKEJI_KEY` 未配置
- wuyinkeji API 返回错误或被拒绝
- 超过 `timeout` 时间仍未完成

调用方应自行捕获异常并决定后续处理。
