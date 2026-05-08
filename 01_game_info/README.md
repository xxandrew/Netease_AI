# 🎮 01_game_info — 游戏信息资料收集整理

> 负责游戏相关信息、资料、内容的收集、整理和管理。

---

## 模块概述

本模块专注于游戏行业信息的全方位收集与整理，包括但不限于：竞品分析、市场动态、玩法机制研究、美术风格参考等。

---

## 子目录说明

| 目录 | 说明 |
|------|------|
| `collectors/` | 信息采集器 — 爬虫脚本、API 对接、视觉诊断、视频解析工具 |
| `processors/` | 数据清洗与整理 — 格式转换、去重、分类处理 |
| `storage/` | 数据存储 — 本地文件/数据库存储方案，报告归档 |
| `resources/` | 参考资料 — 素材库、截图、游戏录屏等 |

---

## 🛠️ 技能包（Skills）

| 技能 | 文件 | 状态 | 说明 |
|---|---|---|---|
| 🗣️ **社交媒体舆情挖掘** | [`collectors/SKILL_舆情挖掘.md`](collectors/SKILL_舆情挖掘.md) | ✅ 已上线 v2.1 | 从小红书自动抓取玩家评论，6 维度 AI 分类，生成 HTML 报告 |
| 📸 **静态界面视觉诊断** | [`collectors/SKILL_视觉分析.md`](collectors/SKILL_视觉分析.md) | 🔧 开发中 | 对游戏截图进行视觉流线、热区、认知负荷分析 |
| 🎬 **游玩视频时序解析** | [`collectors/SKILL_视频解析.md`](collectors/SKILL_视频解析.md) | ✅ Phase 1 完成 | 从录屏中自动找出玩家卡点和关键操作节点 |
| 🕹️ **游戏界面易用性分析** | [`collectors/SKILL_界面易用性分析.md`](collectors/SKILL_界面易用性分析.md) | ✅ Phase 1 完成 | 7 维度量化分析（热区/费茨定律/认知负荷等），输出 HTML+JSON 报告 |

---

## 工作流程

```
信息源
  ├── 游戏截图  → collectors/vision_engine.py（视觉诊断）
  ├── 游戏录屏  → collectors/video_parser.py（视频解析）
  └── 其他资料  → collectors/（通用采集器）
        ↓
  processors（数据清洗 / 结构化整理）
        ↓
  storage（存储 + 报告归档）
        ↓
  resources（素材归档）
```

---

## 📋 Skill 快速索引

- **有玩家评论想分析** → 查看 [`SKILL_舆情挖掘.md`](collectors/SKILL_舆情挖掘.md)
- **有截图需要分析（视觉）** → 查看 [`SKILL_视觉分析.md`](collectors/SKILL_视觉分析.md)
- **有截图需要分析（易用性量化）** → 查看 [`SKILL_界面易用性分析.md`](collectors/SKILL_界面易用性分析.md)
- **有录屏需要解析** → 查看 [`SKILL_视频解析.md`](collectors/SKILL_视频解析.md)
