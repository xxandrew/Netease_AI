# 🎮 游戏数据追踪看板 (Game Tracker)

> 多平台游戏数据实时追踪与分析平台，面向游戏运营/选品/研究人员，支持 Steam 多区、手游多区数据采集、智能异常检测、AI 报告生成及一键导出分析 PPT。

---

## 🧭 项目用途

本项目是一个**游戏行业数据追踪 Skill**，用于：

- 实时监控多平台、多地区热门游戏的在线人数、排名等关键指标
- 自动检测数据异常（暴涨/暴跌/新游冲榜/游戏下架）
- 分析游戏趋势（涨幅排行、周环比、连续涨跌）
- 对比不同地区的榜单差异与热度重叠
- 自定义关注特定游戏，追踪其排名与在线变化
- 利用 AI（OpenAI GPT）自动生成日报/周报
- 一键生成指定游戏的**完整数据分析 PPT（6页）**

适用场景：游戏运营数据周会、选品调研、竞品监控、市场热点追踪。

---

## ✨ 功能一览

### 📊 总览看板
- Steam 全球 / 手游多区 关键指标卡
- Steam Top 10 在线人数柱状图

### 🕹️ Steam 多区数据（Top 50）
| 区域 | 数据来源 | 指标 |
|------|---------|------|
| 🌍 全球 | SteamSpy API | 实时在线人数、峰值、好评率、标签 |
| 🇨🇳 中国 | Steam 官方畅销榜 | 排行、价格 |
| 🇺🇸 美国 | Steam 官方畅销榜 | 排行、价格 |
| 🇯🇵 日本 | Steam 官方畅销榜 | 排行、价格 |
| 🇰🇷 韩国 | Steam 官方畅销榜 | 排行、价格 |

### 📱 手游多区数据（Top 20）
| 区域 | 来源 |
|------|------|
| 🇨🇳 中国 App Store | Apple RSS API |
| 🇨🇳 中国 TapTap | TapTap 爬虫 |
| 🇺🇸 美国 App Store | Apple RSS API |
| 🇯🇵 日本 App Store | Apple RSS API |
| 🇰🇷 韩国 App Store | Apple RSS API |

### 🔍 数据检测（6 大类）
| 检测类型 | 说明 |
|---------|------|
| 🚨 异常检测 | 暴涨/暴跌/新进榜/消失，可调灵敏度（1.5x/2x/3x）|
| 📈 趋势分析 | 涨跌幅排行、连续涨跌天数、周环比 |
| 🌍 跨区域对比 | 多区同热游戏、区域独热、榜单重叠率矩阵 |
| 👁️ Watch List | 自定义关注游戏，实时追踪在线/排名变化 |
| 📋 榜单 Diff | 任意两次采集之间的新进榜/掉榜/排名涨跌 Top10 |
| 🧹 数据质量 | 各数据源新鲜度、缺失率、重复率检测 |

### 🤖 AI 报告 & PPT
- 一键生成 AI 日报/周报（需配置 OpenAI Key，否则降级为数据摘要）
- **一键导出游戏分析 PPT（6页）**：封面、执行摘要、趋势图、区域对比、榜单变动时间线、竞品横向对比

### ⏰ 定时采集
- 每 **1 小时** 自动采集所有平台数据
- 每天 **08:00** 自动生成 AI 日报
- 每周一 **08:30** 自动生成 AI 周报

---

## 🚀 快速启动

### 1. 安装依赖

```bash
cd C:\Netease_Ai\project\game_tracker
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
copy .env.example .env
# 用文本编辑器打开 .env，填入以下内容（均为可选）
```

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI Key，用于 AI 报告生成 | 否 |
| `TWITCH_CLIENT_ID` | Twitch 开发者 Client ID | 否 |
| `TWITCH_ACCESS_TOKEN` | Twitch Access Token | 否 |

> 不配置任何 Key 也可正常运行，AI 报告降级为数据摘要，Twitch 使用内置模拟数据。

### 3. 启动服务

```bash
python app.py
```

浏览器访问 **http://127.0.0.1:5000**

---

## 📁 项目结构

```
C:\Netease_Ai\project\game_tracker\
│
├── app.py                  # Flask 主入口 + 全部 API 路由
├── scheduler.py            # 定时采集 & AI 报告调度（APScheduler）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
│
├── crawler/                # 数据爬虫模块
│   ├── steam.py            # Steam 五区 Top50（SteamSpy + 官方畅销榜）
│   ├── mobile.py           # 手游四区（Apple RSS + TapTap）
│   └── twitch.py           # Twitch API（已采集，页面暂隐藏）
│
├── database/
│   └── db.py               # SQLite 数据库操作（增删查、分区查询）
│
├── monitor/
│   └── engine.py           # 6 大类数据检测引擎
│
├── report/
│   ├── generator.py        # AI 日报/周报生成（OpenAI）
│   └── ppt_generator.py    # 游戏分析 PPT 生成器（python-pptx + matplotlib）
│
├── templates/
│   └── index.html          # 前端单页应用（纯 HTML/CSS/JS，无框架）
│
└── data/
    └── game_tracker.db     # SQLite 数据库（首次运行自动创建）
```

---

## 🔌 API 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/steam` | Steam 所有区域最新数据（按 region_code 分组）|
| GET | `/api/steam/region/<code>` | 指定区域 Steam 数据 |
| GET | `/api/steam/trend?name=xxx` | 指定游戏历史在线趋势 |
| GET | `/api/mobile` | 手游所有区域最新数据（按 region_code 分组）|
| GET | `/api/mobile/region/<code>` | 指定区域手游数据 |
| POST | `/api/refresh` | 手动触发一次数据采集 |
| POST | `/api/report/generate` | 生成 AI 日报/周报 |
| GET | `/api/reports` | 历史 AI 报告列表 |
| GET | `/api/monitor/anomalies` | 异常检测 |
| GET | `/api/monitor/trends` | 趋势分析 |
| GET | `/api/monitor/cross_region` | 跨区域对比 |
| GET/POST/DELETE | `/api/monitor/watchlist` | Watch List 管理 |
| GET | `/api/monitor/diff` | 榜单变动 Diff |
| GET | `/api/monitor/quality` | 数据质量报告 |
| GET | `/api/ppt/generate?name=xxx&days=30` | 生成并下载游戏分析 PPT |

---

## 📦 依赖说明

| 包 | 用途 |
|----|------|
| `flask` | Web 服务框架 |
| `requests` + `beautifulsoup4` + `lxml` | 数据爬虫 |
| `apscheduler` | 定时任务调度 |
| `openai` | AI 报告生成 |
| `python-pptx` | PPT 文件生成 |
| `matplotlib` + `numpy` | PPT 内嵌图表生成 |
| `python-dotenv` | 环境变量管理 |
| `pandas` | 数据处理 |

---

## 📝 更新日志

### v1.0.0 — 2026-04-13

#### 🎉 初始版本发布

**基础功能**
- 搭建 Flask Web 服务，单页应用前端（深色科技风 UI）
- SQLite 数据库设计，支持 Steam / Twitch / 手游三张数据表
- APScheduler 定时任务：每小时采集、每日日报、每周周报

**数据采集**
- Steam：SteamSpy Public API 爬取全球 Top50（在线人数、峰值、好评率、标签）
- Steam：五区分区支持（🌍全球 / 🇨🇳中国 / 🇺🇸美国 / 🇯🇵日本 / 🇰🇷韩国），每区 Top50
- 手游：Apple RSS API 爬取四区 App Store 免费游戏榜（中/美/日/韩）
- 手游：TapTap 爬虫（国内安卓榜，含降级 Mock 数据）
- Twitch：Helix API 爬取直播热度（含无 Key 时的 Mock 降级）
- 所有爬虫均有完整 Mock 数据兜底，断网/反爬时正常运行

**前端看板**
- 总览页：4 项指标卡 + Steam/Twitch 柱状图
- Steam 页：五区胶囊 Tab，全球展示在线进度条/好评率，各区展示畅销榜
- 手游页：四区胶囊 Tab，中国区双列（App Store + TapTap）
- 点击 Steam 游戏行可弹出历史在线趋势折线图

**AI 报告**
- 集成 OpenAI GPT，一键生成日报/周报，支持历史报告归档查看
- 无 API Key 时自动降级为数据摘要，不影响其他功能

**数据检测模块（6 大类）**
- 🚨 异常检测：基于历史均值，识别暴涨/暴跌/新进榜/消失，支持灵敏度调节
- 📈 趋势分析：涨幅/跌幅排行、连续涨跌次数统计、周环比排行
- 🌍 跨区域对比：多区同热游戏列表、各区独热标签云、区域间榜单重叠率矩阵
- 👁️ Watch List：自定义关注游戏，实时显示在线变化量和排名涨跌
- 📋 榜单 Diff：任意平台/区域两次采集之间的新进榜、掉榜、排名涨跌 Top10
- 🧹 数据质量：各数据源新鲜度（绿/橙/红）、总记录数、字段缺失率、重复数

**PPT 生成**
- 一键导出指定游戏的数据分析 PPT（6 页，深色科技风）
- 支持自定义分析周期（7/14/30/90 天）
- 页面内容：封面 → 执行摘要（6 项指标卡）→ 趋势折线图（在线+排名）→ 区域排名对比（图+表）→ 榜单变动时间线 → 竞品横向对比条形图

**工程**
- 项目路径规范化，统一存放于 `C:\Netease_Ai\project\game_tracker\`
- 所有爬虫失败均有降级 Mock 数据，保证演示可用性
- 数据库兼容旧版本（ALTER TABLE 自动补字段）
- 数据库启动时自动清理无 region_code 的旧数据，避免分区查询失效

---

## ⚠️ 注意事项

1. **首次启动**会在后台自动采集一次数据（约 30 秒），期间看板数据可能为空，稍等后点击「🔄 刷新数据」
2. **PPT 图表中文乱码**：确保系统安装了「微软雅黑」或「黑体」字体，否则中文自动降级为英文字体
3. **Steam 区域爬虫**：中国大陆访问 `store.steampowered.com` 可能需要代理，否则自动使用 Mock 数据
4. **数据积累**：趋势图、异常检测、Diff 功能需要至少 **2 次采集记录**才能正常使用，建议运行 2 小时后体验完整功能