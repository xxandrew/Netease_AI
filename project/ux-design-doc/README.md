# G79 交互文档工具包

> ⚠️ **内部使用，严禁外传**

AI 辅助撰写交互说明 + Figma 插件一键生成文档。

---

## 两段式工作流

```
① AI 撰写阶段（CodeMaker）
   Figma 交互稿 + 策划 PRD
         ↓
   AI 读截图 → 逐界面写交互说明
         ↓
   interaction-spec.md

② 文档生成阶段（脚本 + Figma 插件）
   interaction-spec.md
         ↓
   md2docjson.mjs → figma-doc.json
         ↓
   Figma 插件「文档助手」→ 自动渲染交互文档
```

---

## 目录结构

```
ux-design-doc/
├── README.md                    ← 本文件
├── SKILL.md                     ← 安装给 CodeMaker（AI 撰写阶段）
├── uxdoc.md                     ← AI 执行指南（工作流、格式规范）
├── specs/
│   ├── writing-guide.md         ← 结构原则、字段顺序、术语规范
│   ├── widget-templates.md      ← 19 类控件模板
│   └── field-reference.md       ← 字段格式、HTML class、常见错误对照
├── scripts/
│   ├── figma-capture.py         ← Figma 截图导出（AI 撰写阶段用）
│   ├── md2docjson.mjs           ← MD → Figma 文档 JSON（文档生成阶段用）
│   ├── md2html.mjs              ← MD → HTML（可选，生成可分享 HTML）
│   └── validate.mjs             ← 格式检查
├── figma-plugin/                ← Figma 插件（开箱即用，无需安装 Node）
│   ├── README.md                ← 插件安装和使用说明
│   ├── manifest.json
│   └── dist/
│       ├── code.js
│       └── index.html
└── case-{功能}-{MMDD}/          ← 你的工作产物（自建）
    ├── design/                  ← 截图放这里
    ├── interaction-spec.md      ← AI 生成的交互说明源文件
    ├── figma-doc.json           ← 插件输入 JSON
    └── interaction-spec.html    ← 可选，HTML 版本
```

---

## 前置条件

| 工具 | 用途 | 阶段 |
|------|------|------|
| [Node.js](https://nodejs.org/) | 运行脚本 | 文档生成 |
| [Python 3](https://www.python.org/) | 从 Figma 导出截图 | AI 撰写 |
| Figma API Token | 访问 Figma 文件 | AI 撰写 |
| [Figma 桌面版](https://www.figma.com/downloads/) | 运行插件 | 文档生成 |
| [CodeMaker](https://codemaker.ai/) | AI 辅助写作 | AI 撰写 |

### 配置 Figma Token

1. 登录 Figma → 头像菜单 → **Settings** → **Security**
2. **Personal access tokens** → 生成 Token
3. 命令行设置环境变量（建议写入系统变量持久生效）：
   ```cmd
   set FIGMA_TOKEN=你的token
   ```

---

## 阶段一：AI 撰写交互说明

### 安装 CodeMaker Skill

```cmd
mkdir "%USERPROFILE%\.codemaker\skills\ux-design-doc"
copy "SKILL.md" "%USERPROFILE%\.codemaker\skills\ux-design-doc\SKILL.md"
```

安装后**重启 CodeMaker 对话**生效。

### 使用方式

1. 新建 case 目录（必须以 `case-` 开头）：
   ```
   case-背包系统-0420/
   ```
2. 在 CodeMaker 说「撰写交互文档」或「帮我写 xxx 的 case」
3. 提供 Figma 交互稿链接 + 策划 PRD
4. **AI 会自动引导完成所有步骤**，无需手动操作

产出：`case目录/interaction-spec.md`

---

## 阶段二：生成 Figma 文档

### 第一步：生成 JSON

在 case 目录下运行：

```bash
node ../scripts/md2docjson.mjs interaction-spec.md
```

生成 `figma-doc.json`，自动在 VSCode 中打开预览。

### 第二步：安装 Figma 插件（首次使用）

详见 `figma-plugin/README.md`。

### 第三步：在 Figma 中生成文档

1. 打开交互稿 Figma 文件
2. **确保界面已转为 Component 或 Variant**（Frame 无效）
3. 打开插件「文档助手」
4. 粘贴 `figma-doc.json` 内容 → 点击「生成文档」

---

## 可选：生成 HTML 文档

```bash
# 格式检查
node ../scripts/validate.mjs interaction-spec.md

# 生成 HTML
node ../scripts/md2html.mjs interaction-spec.md
```

产出：`interaction-spec.html`（可直接分享）

---

## 常见问题

**Q：figma-capture.py 提示「未找到 FIGMA_TOKEN」**  
A：执行 `set FIGMA_TOKEN=你的token`，或写入系统环境变量。

**Q：Node.js 命令找不到**  
A：安装 Node.js 后重新打开命令行窗口。

**Q：中文路径下 Python 脚本乱码**  
A：命令前加 `-X utf8`：`python -X utf8 ../scripts/figma-capture.py`

**Q：Figma 文档里界面是空的**  
A：检查界面是否已转为 Component/Variant；插件只扫描**当前 Page**，界面需在同一页。

**Q：AI 没有按规范工作**  
A：确认 SKILL.md 已安装且重启了对话；检查工作目录是否在 `ux-design-doc/` 内。