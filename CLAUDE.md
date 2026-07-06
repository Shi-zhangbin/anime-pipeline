# CLAUDE.md — Anime Pipeline

## 项目一句话定位

Anime Pipeline 是一个基于 **wuyinkeji AI 生图 + 华为云 OBS 参考图中转** 的二次元图片生成工作流项目。核心围绕两个国产算力 IP 角色 **昇腾酱** 和 **鲲鹏君** 展开，用于生成角色立绘、参考图一致性变体及周边图片。

## 核心能力

1. **文生图**：调用 wuyinkeji API 直接生成图片。
2. **参考图生图**：本地参考图 → 上传 OBS 获取公开 URL → 作为 ref_url 传给 wuyinkeji → 生成高一致性图片。
3. **角色资产管理**：角色设定文档、生成脚本、参考图上传均围绕 `characters/` 目录组织。

## 项目结构

```
anime-pipeline/
├── .env                          # API 密钥（gitignored）
├── .gitignore
├── CLAUDE.md                     # 本文件：项目抽象总结
├── core/                         # 核心基础设施
│   ├── config.py                 # 读取 .env 中的 wuyinkeji/OBS 配置
│   ├── imagegen.py               # wuyinkeji 图片生成（支持 ref_urls）
│   └── obs.py                    # 华为云 OBS 上传/列表/获取 URL
├── scripts/
│   └── generate_with_reference.py # 参考图生图 CLI
├── skills/
│   └── anime-image-gen.md        # skill 文档与使用指南
└── characters/                   # 角色设定文档
    ├── 昇腾酱-Ascend-chan.md
    └── 鲲鹏君-Kunpeng-kun.md
```

## 关键文件索引

| 想看什么 | 去哪里看 |
|---------|---------|
| 角色定位、世界观、性格、外貌 | `characters/昇腾酱-Ascend-chan.md`、`characters/鲲鹏君-Kunpeng-kun.md` |
| 图片生成 API 用法 | `core/imagegen.py`、`skills/anime-image-gen.md` |
| 参考图上传到 OBS | `core/obs.py`、`scripts/generate_with_reference.py` |
| 环境变量说明 | `.env`、`.gitignore` |
| 完整 skill 使用指南 | `skills/anime-image-gen.md` |

## 使用红线

1. **只生成图片**：不走视频管线。
2. **参考图必须公开**：本地图片作为 wuyinkeji 参考时，必须先上传到 OBS 获取公开 URL。
3. **输出目录规范**：生成结果统一放到 `outputs/` 或 `characters/outputs/`，不往根目录写图片。
4. **动漫内容安全**：禁止恐怖、血腥、过度暴露、恐怖谷等不适内容。
5. **不泄露密钥**：`.env` 已在 `.gitignore` 中，永远不要将其提交到 git。

## 快速入口

```bash
# 直接生成
PYTHONPATH=. python3 core/imagegen.py "anime girl, purple twin tails"

# 参考图生图
PYTHONPATH=. python3 scripts/generate_with_reference.py \
  --ref /path/to/ref.jpg \
  --prompt "same character, smiling" \
  --out outputs/consistent.png

# OBS 上传
PYTHONPATH=. python3 -m core.obs upload /path/to/ref.jpg anime-pipeline/refs/ref01.jpg
```

具体实现细节、参数说明、错误处理请查看对应源文件和 `skills/anime-image-gen.md`。
