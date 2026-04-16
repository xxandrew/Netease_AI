# 🕹️ UI Usability Analyzer — 游戏界面易用性分析器

基于 **GPT-4o Vision API** 的游戏界面易用性自动化诊断工具。  
输入一张游戏截图，从 7 个专业维度输出问题列表、优化建议与综合评分，生成 **HTML 可视化报告 + JSON 结构化数据**。

---

## ✨ 功能特性

| 维度 | 分析内容 | 数据来源 |
|---|---|---|
| 🔴 热区尺寸 | px → dp 换算，对照平台规范（移动 ≥44dp）| 标注数据（精确）|
| 🟠 费茨定律 | 操作距离与按键大小，计算 Fitts ID | 标注数据 + GPT |
| 🟡 热区间距 | 相邻按键边缘间距，预防误触 | 标注数据（精确）|
| 🟡 热区重叠 | 负间距/重叠检测，P0 Bug 级别标注 | 标注数据 + GPT |
| 🔵 认知负荷 | 同屏元素数量，图标辨识度，视觉层级 | GPT Vision |
| 🔵 视野遮挡 | UI 占屏比，透明度策略评估 | 标注数据 + GPT |
| 🟢 拇指热区 | 舒适区 / 可达区 / 困难区分布 | 标注数据 + GPT |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# Windows
set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# macOS / Linux
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 运行分析

```bash
# 最简调用：仅截图
python analyzer.py --image screenshot.png

# 指定分辨率 + 平台
python analyzer.py --image screenshot.png --resolution 1920x1080 --platform mobile

# 传入按键标注数据（精确计算热区/间距）
python analyzer.py --image screenshot.png --buttons buttons.json --output ./my_reports

# 查看完整帮助
python analyzer.py --help
```

---

## 📋 命令行参数说明

| 参数 | 简写 | 默认值 | 说明 |
|---|---|---|---|
| `--image` | `-i` | *必填* | 截图路径（jpg/png/webp）|
| `--resolution` | `-r` | `1920x1080` | 分辨率，格式 `WIDTHxHEIGHT` |
| `--platform` | `-p` | `mobile` | 平台：`mobile` / `tablet` / `pc` |
| `--buttons` | `-b` | 无 | 按键标注 JSON 文件路径（可选）|
| `--output` | `-o` | `./reports` | 报告输出目录 |
| `--dpi_scale` | — | `1.0` | DPI 缩放：@1x=1.0，@2x=2.0 |
| `--api_key` | — | 无 | API Key（优先用环境变量）|

---

## 📁 按键标注 JSON 格式

当需要精确计算热区尺寸、间距、重叠时，提供按键标注数据：

```json
[
  {"name": "技能1",   "x": 1720, "y": 900, "width": 88,  "height": 88},
  {"name": "技能2",   "x": 1620, "y": 950, "width": 80,  "height": 80},
  {"name": "技能3",   "x": 1520, "y": 920, "width": 80,  "height": 80},
  {"name": "普通攻击","x": 1820, "y": 980, "width": 96,  "height": 96},
  {"name": "返回",    "x": 20,   "y": 20,  "width": 28,  "height": 28},
  {"name": "设置",    "x": 54,   "y": 20,  "width": 32,  "height": 32}
]
```

- `x`, `y`：按键热区左上角坐标（px，以截图左上角为原点）
- `width`, `height`：热区宽高（px）

> 💡 **坐标数据来源**：设计稿标注（Figma/蓝湖）、开发侧 UI 坐标表、或手工截图测量

---

## 📂 输出文件说明

分析完成后，在 `--output` 目录下生成两个文件：

```
reports/
├── usability_report_截图名_时间戳.html   ← 可视化 HTML 报告（直接用浏览器打开）
└── usability_data_截图名_时间戳.json    ← 结构化 JSON 数据（供后续处理）
```

**HTML 报告内容：**
- 综合评分（0-100，含彩色进度条）
- 7个维度各自的详情表格 + 问题列表 + 优化建议（含开发成本 L/M/H）
- GPT AI 整体评价

**JSON 数据结构：**
```json
{
  "image_path": "screenshot.png",
  "resolution": [1920, 1080],
  "platform": "mobile",
  "timestamp": "2026-01-01 12:00:00",
  "total_score": 78,
  "dimensions": [
    {
      "name": "热区尺寸",
      "score": 85,
      "issues": ["..."],
      "suggestions": ["... | 开发成本：L（资源替换）"],
      "details": { "rows": [...] }
    }
  ],
  "gpt_raw": { ... }
}
```

---

## 🐍 作为模块调用

```python
from analyzer import UIUsabilityAnalyzer

analyzer = UIUsabilityAnalyzer(
    image_path  = "screenshot.png",
    resolution  = (1920, 1080),
    platform    = "mobile",
    button_data = [
        {"name": "技能1",   "x": 1720, "y": 900, "width": 88, "height": 88},
        {"name": "普通攻击","x": 1820, "y": 980, "width": 96, "height": 96},
    ],
    output_dir  = "./reports",
)

result = analyzer.run()
print(f"综合得分：{result.total_score}")
print(f"HTML 报告：{result.report_html}")
print(f"JSON 数据：{result.data_json}")
```

---

## 📐 评分规则

| 得分区间 | 含义 | 颜色标记 |
|---|---|---|
| 80–100 | 易用性良好 | 🟢 绿色 |
| 60–79  | 存在中等风险，建议优化 | 🟡 橙色 |
| 0–59   | 存在严重易用性问题 | 🔴 红色 |

**综合评分权重：**

| 维度 | 权重 | 理由 |
|---|---|---|
| 热区尺寸 | 20% | 基础可用性门槛 |
| 费茨定律 | 20% | 直接影响操作效率 |
| 热区间距 | 15% | 高频误触风险 |
| 热区重叠 | 15% | 功能性 Bug 级别 |
| 认知负荷 | 15% | 影响学习成本 |
| 视野遮挡 | 10% | 影响游戏体验 |
| 拇指热区 | 5%  | 综合舒适度 |

---

## ⚠️ 注意事项

1. **API Key 安全**：请勿将 API Key 提交到代码仓库，始终使用环境变量
2. **精度说明**：GPT-4o Vision 对像素坐标的判断存在估算误差，精确计算依赖 `--buttons` 标注数据
3. **分辨率基准**：1920×1080 截图默认 `@1x`（1px=1dp）；如为 Retina 截图（@2x），需传入 `--dpi_scale 2.0`
4. **平台选择**：`--platform` 影响 dp 最小尺寸标准和间距阈值，请根据实际目标平台选择

---

## 📅 开发路线

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1 | 截图输入 → GPT-4o Vision → HTML/JSON 报告 | ✅ 完成 |
| Phase 2 | Figma API 接入，精确读取设计稿坐标 | ⏳ 待排期 |
| Phase 3 | 批量截图对比（版本间易用性追踪）| ⏳ 待排期 |
| Phase 4 | 热力图叠加（问题区域可视化标注）| ⏳ 待排期 |

---

## 📖 理论依据

- **Fitts's Law**（1954）— 操作时间与目标大小/距离关系
- **ISO 9241-9** — 触控设备最小热区规范
- **Apple HIG** — iOS/macOS 交互指南（最小触控目标 44×44pt）
- **Google Material Design** — 最小触控目标 48×48dp
- **Cognitive Load Theory**（Sweller 1988）— 工作记忆容量与界面复杂度
- **Miller's Law**（7±2）— 人类工作记忆信息块上限
- **Steven Hoober 单手操作研究**（2013）— 移动端拇指热区分布
