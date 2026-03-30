
# 📋 会话接续档案 — 2026-03-30

> 新会话开始时，让 AI 读取本文件即可快速恢复上下文。

---

## 📐 新会话开场指令（复制这段）

```
读取 C:\Netease_Ai\session_notes.md 和 C:\Netease_Ai\collab_rules.md，
然后帮我运行舆情抓取脚本，游戏是「___」，模块是「___」
```

---

## ✅ 本次会话已完成的事项

### 1. 舆情分析 skill 文档同步到技能库
将 `C:\Users\xxn4472\Desktop\game_analyst` 下的 3 个 skill 按标准模式写入 `C:\Netease_Ai\01_game_info\collectors\`：

| 文件 | 状态 |
|---|---|
| `SKILL_舆情挖掘.md` | ✅ 已上线 v2.1 |
| `SKILL_视觉分析.md` | 🔧 开发中 |
| `SKILL_视频解析.md` | ✅ Phase 1 完成 |

同步更新了 `01_game_info/README.md` 和 `soul.md`。

### 2. PPT 生成
已生成：`C:\Netease_Ai\03_document_processing\ppt\outputs\20260326_AI技术在游戏交互环节的运用_v2.0.pptx`
参考模板：`C:\Users\xxn4472\Desktop\test1\MC_UXD-AI0323.pptx`

---

## ⏳ 下一步待做：运行舆情抓取

### 脚本位置
```
C:\Users\xxn4472\Desktop\game_analyst\tools\舆情挖掘\run_task.py
```

### 当前默认参数
```python
game   = '我的世界'
module = '山头服'
max_samples = 50
```

### 运行方式
新会话中直接说：
> "帮我运行舆情抓取脚本，游戏是 XXX，模块是 XXX"

AI 会修改 `run_task.py` 的 `game` / `module` 参数后执行：
```cmd
cd /d "C:\Users\xxn4472\Desktop\game_analyst\tools\舆情挖掘"
python run_task.py
```

### Cookie 状态
`cookies.json` 已配置，包含有效的小红书登录凭证（`web_session` / `a1` / `webId`）。
有效期约 30 天，若抓取失败提示 403 则需重新获取。

### 输出位置
```
C:\Users\xxn4472\Desktop\game_analyst\tools\舆情挖掘\outputs\
├── report_游戏名_模块_日期.html   ← 浏览器打开查看
└── sentiment_游戏名_模块_日期.xlsx
```

---

## 🗂️ 关键目录速查

| 目录 | 用途 |
|---|---|
| `C:\Netease_Ai\01_game_info\` | 游戏信息技能库（含 3 个 skill 文档）|
| `C:\Netease_Ai\03_document_processing\ppt\outputs\` | PPT 输出目录 |
| `C:\Users\xxn4472\Desktop\game_analyst\tools\舆情挖掘\` | 舆情抓取脚本目录 |
| `C:\Users\xxn4472\Desktop\game_analyst\tools\舆情挖掘\outputs\` | 舆情报告输出目录 |
