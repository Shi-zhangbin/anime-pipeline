# 动漫制作 — Agent 操作手册

> 本文件供运行此项目的 AI Agent 遵守。每次开始任务前必须先读取。
> 本文件覆盖全局 AGENTS.md 中的通用约定，补充项目特有规则。

## 项目定位

这是一个 **二次元角色 IP 图片生成工作流**，围绕两个国产算力 IP 角色（昇腾酱 & 鲲鹏君）展开。**不是视频管线，只产图片。**

- **核心能力**: 文生图、参考图生图、Q版漫画页生成
- **生图 API**: wuyinkeji（异步 submit-poll-download）
- **参考图中转**: 华为云 OBS（3 天自动清理）
- **主语言**: Python 3

## 快速入口

```bash
# 直接生成
PYTHONPATH=. python3 core/imagegen.py "anime girl, purple twin tails"

# 参考图生图
PYTHONPATH=. python3 scripts/generate_with_reference.py \
  --ref /path/to/ref.jpg --prompt "same character, smiling" --out outputs/xxx.png

# OBS 上传参考图
PYTHONPATH=. python3 -m core.obs upload /path/to/ref.jpg 动漫制作/refs/ref01.jpg

# Q版双人漫画（横屏）
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml --layout landscape --date 2026-07-07

# Q版双人漫画（竖屏）
PYTHONPATH=. python3 scripts/generate_chibi_comic.py \
  --scenario scenarios/trillion-model.yaml --layout portrait --date 2026-07-07
```

## 核心文件索引

| 想看什么 | 去哪里 |
|---------|--------|
| 角色详细设定（外貌/性格/背景） | `characters/昇腾酱-Ascend-chan.md`、`characters/鲲鹏君-Kunpeng-kun.md` |
| 角色快速引用（YAML） | `characters/roles.yaml` |
| 世界观背景 | `characters/story-summary.md` |
| 参考图 OBS URL 清单 | `characters/reference_manifest.json` |
| 生图 API 实现 | `core/imagegen.py` |
| OBS 操作 | `core/obs.py` |
| 漫画排版 | `core/comic_layout.py` |
| Q版漫画生成 | `scripts/generate_chibi_comic.py` |
| 漫画剧情脚本 | `scenarios/trillion-model.yaml` |
| Skill 使用指南 | `skills/anime-image-gen.md` |

## 角色信息

| 角色 | ID | 身份 | 代表色 | 性格 |
|------|-----|------|--------|------|
| 昇腾酱 | `ascend-chan` | AI 算力小妹 | 紫 `#9B59B6` + 橙 `#F39C12` | 元气、急性子、爱逞能 |
| 鲲鹏君 | `kunpeng-kun` | 通用计算大哥 | 深蓝 `#1A3A5C` + 银 `#C0C0C0` | 沉稳、可靠、宠妹 |

## 核心规则（红线）

1. **只生成图片，不走视频管线**。本项目没有 T0-T7 pipeline。
2. **参考图必须上传 OBS**：wuyinkeji 需要公开 URL，本地图片先上传 OBS 再作为 ref_url。
3. **输出目录规范**：
   - 核心资产 → `outputs/`（chibi/、refsheets/）
   - 过程产物 → `archive/outputs/`（漫画页、场景图等）
   - 漫画按 `outputs/chibi_comic/<scenario>/<YYYY-MM-DD>_<layout>/` 分布
   - 不往根目录写图片
4. **动漫内容安全**：禁止恐怖、血腥、过度暴露、恐怖谷等不适内容。
5. **不泄露密钥**：
   - OBS 凭证使用全局环境变量 `OBS_ACCESS_KEY_ID` / `OBS_SECRET_ACCESS_KEY`（已配置在 `~/.zshrc`），不要写入项目 `.env` 或任何文档。
   - 若项目 `.env` 存在，仅用于非密钥类本地配置（如超时时间、路径偏好）。
   - `.env` 已在 `.gitignore` 中，严禁提交。
6. **YAML 驱动**：角色设定走 `roles.yaml`，剧情走 `scenarios/*.yaml`，不硬编码。

## 项目结构

```
动漫制作/
├── characters/                 # 角色资料
│   ├── roles.yaml              # 角色统一入口（YAML）
│   ├── reference_manifest.json # 参考图 OBS URL 清单
│   ├── story-summary.md        # 世界观背景
│   ├── 昇腾酱-Ascend-chan.md   # 角色详细设定
│   └── 鲲鹏君-Kunpeng-kun.md   # 角色详细设定
├── core/                       # 核心基础设施
│   ├── config.py               # 读取 .env 配置
│   ├── imagegen.py             # wuyinkeji 生图
│   ├── obs.py                  # 华为云 OBS 操作
│   └── comic_layout.py         # PIL 漫画排版
├── scripts/                    # 工作流脚本
│   ├── generate_with_reference.py  # 参考图生图
│   ├── generate_scene.py           # 按场景类型生图
│   └── generate_chibi_comic.py     # Q版漫画页生成
├── scenarios/                  # 漫画剧情脚本（YAML）
│   └── trillion-model.yaml
├── skills/                     # Skill 文档
│   └── anime-image-gen.md
├── outputs/                    # 核心生成资产（保留）
│   ├── chibi/                  # Q版角色
│   └── refsheets/              # 参考表
└── archive/                    # 过程产物归档
    └── outputs/
```

## 已知风险

| 风险 | 说明 |
|------|------|
| wuyinkeji 超时 | 异步 API 轮询最多 5 分钟，大图可能超时 |
| OBS 上传失败 | 检查全局环境变量 `OBS_ACCESS_KEY_ID` / `OBS_SECRET_ACCESS_KEY` 是否已正确配置在 `~/.zshrc` 并 source 生效 |
| 角色一致性 | 无参考图时 AI 可能画出不同角色，优先使用 ref_url |
| 漫画排版 | 竖屏 9:16 的 3×2 格子可能被 AI 误解为 2×3，prompt 中需明确写明 grid 方向 |

---

*最后更新：2026-08-04*