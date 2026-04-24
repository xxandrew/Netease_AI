#!/usr/bin/env node
/**
 * md2docjson.mjs
 * Markdown (interaction-spec.md) + frame-map.json + bubble-map.json → figma-doc.json
 *
 * 用法（在 case 目录下运行）：
 *   node ../scripts/md2docjson.mjs [interaction-spec.md] [frame-map.json]
 *
 * 参数均可省略，默认：
 *   input      = ./interaction-spec.md
 *   map        = ./frame-map.json   （可不存在，缺失时 componentName = uiName）
 *   bubble-map = ./bubble-map.json  （可不存在，缺失时 bubbles = []）
 *   output     = ./figma-doc.json
 *
 * 字段映射规则（对应 PROGRESS.md Phase 4）：
 *   YAML frontmatter    → doc.title / doc.cehua / doc.uxd
 *   ## B. 方案说明       → sections[0].docTitle（取 title frontmatter）
 *   ### [N] 界面名称     → ui.uiName + ui.componentName（frame-map 查找）
 *   state: xxx 行        → ui.stateName
 *   #### N. 模块标题     → module.moduleTitle
 *   普通段落             → content item
 *   > 注意/提示/...      → mention item（role 从文本识别）
 *   ---                  → divider item
 *   **类型：** xxx       → skip（不渲染）
 *   **子类型：** xxx     → skip（不渲染）
 *   **控件状态：** xxx   → diagram_states item（states 数组）
 *   **滑动热区：** xxx   → diagram_slide item
 *   【需要通用组件图示：xxx】 → diagram_image item
 */

import fs from 'fs';
import path from 'path';

// ─── 参数处理 ──────────────────────────────────────────────────────
const args = process.argv.slice(2);
const mdFile    = args[0] ?? 'interaction-spec.md';
const mapFile   = args[1] ?? null;   // 显式指定时优先；否则自动检测
const outFile   = 'figma-doc.json';

if (!fs.existsSync(mdFile)) {
  console.error(`❌ 找不到文件：${mdFile}`);
  process.exit(1);
}

const mdText = fs.readFileSync(mdFile, 'utf8');

/**
 * 读取 frame-map（兼容两种格式）：
 *   1. flat-map.json（figma-capture 生成）：{ "Figma帧名": "Figma帧名", ... }
 *      → 用户可把 key 改成 MD 里的 uiName 来做映射
 *   2. 手动编写的 frame-map.json：同上平坦格式
 *   3. figma-capture 旧版 frame-map.json：{ frames: [{name, nodeId, ...}] }
 *      → 自动提取 name 列表转成平坦格式
 */
function loadFrameMap(explicitPath) {
  // 优先级：显式参数 > flat-map.json > frame-map.json
  const candidates = explicitPath
    ? [explicitPath]
    : ['flat-map.json', 'frame-map.json'];

  for (const p of candidates) {
    if (!fs.existsSync(p)) continue;
    try {
      const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
      // 嵌套格式（figma-capture frame-map.json）
      if (raw.frames && Array.isArray(raw.frames)) {
        const flat = {};
        for (const f of raw.frames) flat[f.name] = f.name;
        console.log(`   📍 读取 ${p}（嵌套格式，提取 ${raw.frames.length} 条）`);
        return flat;
      }
      // 平坦格式
      console.log(`   📍 读取 ${p}（平坦格式，${Object.keys(raw).length} 条）`);
      return raw;
    } catch (e) {
      console.warn(`   ⚠️  读取 ${p} 失败：${e.message}`);
    }
  }
  return {};
}

const frameMap = loadFrameMap(mapFile);

// ─── 读取 component-keys.json ──────────────────────────────────────
// 格式：{ "Figma组件名（与 structure.json key 一致）": "componentKey" }
// 来源：figma-capture.py 自动生成，或手动维护
function loadComponentKeys() {
  const p = 'component-keys.json';
  if (!fs.existsSync(p)) return {};
  try {
    const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
    console.log(`   🔑 读取 component-keys.json（${Object.keys(raw).length} 条）`);
    return raw;
  } catch (e) {
    console.warn(`   ⚠️  读取 component-keys.json 失败：${e.message}`);
    return {};
  }
}
const componentKeys = loadComponentKeys();

// ─── 读取 bubble-map.json ──────────────────────────────────────────
// 格式：{ "[1] 界面名称": [{ "num": 1, "x": 48, "y": 120 }, ...] }
// 来源：AI 读图时，识别各模块位置后手动填写到 bubble-map.json
function loadBubbleMap() {
  const p = 'bubble-map.json';
  if (!fs.existsSync(p)) return {};
  try {
    const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
    console.log(`   🫧 读取 bubble-map.json（${Object.keys(raw).length} 个界面有气泡数据）`);
    return raw;
  } catch (e) {
    console.warn(`   ⚠️  读取 bubble-map.json 失败：${e.message}`);
    return {};
  }
}

const bubbleMap = loadBubbleMap();

// ─── 前置：解析 YAML frontmatter（简易版，不依赖第三方库）──────────
function parseFrontmatter(text) {
  const meta = { title: '', cehua: '', uxd: '', version: '' };
  const lines = text.split('\n');
  let inFM = false;
  let fmEnd = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!inFM && line.trim() === '') continue; // 跳过开头空行
    if (!inFM) { inFM = true; fmEnd = i; continue; } // 第一行非空不是 ---，直接读 kv
    if (line.trim() === '---') { fmEnd = i + 1; break; }
    const m = line.match(/^(\w+):\s*(.*)$/);
    if (m) {
      const key = m[1].toLowerCase();
      const val = m[2].trim();
      if (key === 'title')   meta.title   = val;
      if (key === 'planner') meta.cehua   = val;
      if (key === 'uxd')     meta.uxd     = val;
      if (key === 'version') meta.version = val;
    }
  }
  // 更宽松：如果第一行不是 ---，就认为没有 frontmatter 包裹符，从头扫到第一个 ## 之前
  const bodyStart = text.indexOf('\n## ');
  const fmSection = bodyStart > 0 ? text.slice(0, bodyStart) : '';
  if (!meta.title) {
    const tm = fmSection.match(/^title:\s*(.+)$/m);
    if (tm) meta.title = tm[1].trim();
  }
  if (!meta.cehua) {
    const pm = fmSection.match(/^planner:\s*(.+)$/m);
    if (pm) meta.cehua = pm[1].trim();
  }
  if (!meta.uxd) {
    const um = fmSection.match(/^uxd:\s*(.+)$/m);
    if (um) meta.uxd = um[1].trim();
  }
  return meta;
}

// ─── 角色关键词识别 ────────────────────────────────────────────────
const ROLE_KEYWORDS = ['策划', '程序', 'GUI', 'VX', '拼接'];
function detectRole(text) {
  for (const r of ROLE_KEYWORDS) {
    if (text.includes(r)) return r;
  }
  return undefined;
}

// ─── 行分类工具 ────────────────────────────────────────────────────
function classifyLine(line) {
  const t = line.trim();
  if (/^### \[(\d+)\]\s+(.+)$/.test(t))    return 'ui-heading';
  if (/^#### \d+[.．]\s+.+$/.test(t))      return 'module-heading';
  if (/^##### /.test(t))                    return 'sub-heading';   // #SubTitle-2
  if (/^---+$/.test(t))                     return 'divider';
  if (/^>\s+/.test(t))                      return 'blockquote';
  if (/^\*\*类型[：:]\*\*/.test(t))         return 'type-label';    // skip
  if (/^\*\*子类型[：:]\*\*/.test(t))       return 'type-label';    // skip
  if (/^\*\*控件状态[：:]\*\*/.test(t))     return 'state-label';
  if (/^\*\*滑动热区[：:]\*\*/.test(t))     return 'slide-label';
  if (/^【需要通用组件图示[：:]/.test(t))    return 'image-ref';
  if (/^【需要交互图示/.test(t))             return 'hotspot-ref';  // diagram_hotspot
  if (/^【需要图示】/.test(t))               return 'callout-ref';  // diagram_callout
  if (t === '' || /^design:\s+/.test(t))    return 'skip';
  // ## [字母]. 标题 → section 分隔符（对应 #Title_Doc_Div）
  if (/^## [A-Za-z一-龥][.．]\s+.+$/.test(t)) return 'section-divider';
  // 其余 # 开头 → skip
  if (/^#+\s/.test(t))                      return 'section-heading';
  return 'text';
}

// ─── 把连续 text 行合并为一段 ──────────────────────────────────────
function buildContentText(lines) {
  return lines
    .map(l => l.trim())
    .filter(Boolean)
    .join('\n');
}

// ─── 主解析 ───────────────────────────────────────────────────────
function parseMd(text) {
  // 统一行尾（Windows \r\n → \n）
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const meta = parseFrontmatter(text);

  // 找 Section B（方案说明 / 界面说明 / 任意 ## [A-Z]. 非需求范围标题）
  let sectionBTitle = 'B. 界面说明';
  let body = text;
  for (const m of text.matchAll(/\n(## [A-Z]\.[^\n]+)\n/g)) {
    if (!m[1].includes('需求范围')) {
      sectionBTitle = m[1].trim().replace(/^## /, '');
      body = text.slice((m.index ?? 0) + m[0].length);
      break;
    }
  }

  const lines = body.split('\n');

  /** @type {import('../../../others/figma-plugin-doc/src/shared/g79-types').G79UI[]} */
  const uis = [];
  let currentUI   = null;
  let currentModule = null;
  let pendingText = []; // 暂存待合并的 text 行

  // 向后找第一个非空行的分类（用于判断 --- 是否是界面/章节分隔符）
  function peekNextKind(i) {
    for (let j = i + 1; j < lines.length; j++) {
      if (lines[j].trim() !== '') return classifyLine(lines[j]);
    }
    return 'skip';
  }

  function flushText() {
    if (pendingText.length === 0) return;
    const txt = buildContentText(pendingText);
    pendingText = [];
    if (!txt) return;
    if (!currentModule) return;
    currentModule.items.push({ type: 'content', text: txt });
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const kind = classifyLine(line);

    if (kind !== 'text') flushText(); // 非 text 行先把积累的文本 flush

    switch (kind) {
      case 'ui-heading': {
        // ### [N] 界面名称
        currentModule = null;
        const m = line.trim().match(/^### \[(\d+)\]\s+(.+)$/);
        const uiName = m ? `[${m[1]}] ${m[2].trim()}` : line.trim();
        // 2 层回退（section B 标题不含括号说明，只需处理有无 [N] 前缀两种情况）：
        // 1. 精确匹配 → 适配用户做了 Step2 的 flat-map（key 含 [N]）
        // 2. 剥 [N] 前缀 → 适配 figma-capture 原始 flat-map（key 为 Figma 帧名）
        const strippedName  = uiName.replace(/^\[\d+\]\s*/, '');
        const componentName = frameMap[uiName] ?? frameMap[strippedName] ?? uiName;
        const componentKey = componentKeys[componentName] || undefined;
        const bubbles = bubbleMap[uiName] ?? undefined;
        currentUI = { uiName, componentName, ...(componentKey ? { componentKey } : {}), ...(bubbles ? { bubbles } : {}), modules: [] };
        uis.push(currentUI);
        break;
      }

      case 'module-heading': {
        // #### N. 模块标题
        if (!currentUI) break;
        const m = line.trim().match(/^#### (\d+)[.．]\s+(.+)$/);
        const moduleNum    = m ? parseInt(m[1]) : (currentUI.modules.length + 1);
        const moduleTitle  = m ? m[2].trim() : line.replace(/^#+\s*/, '').trim();
        currentModule = { moduleNum, moduleTitle, items: [] };
        currentUI.modules.push(currentModule);
        break;
      }

      case 'divider': {
        // --- 后面紧接着是新界面/新章节 → 仅作分隔符，不渲染到 section 里
        const nextKind = peekNextKind(i);
        const isSectionSeparator = ['ui-heading', 'section-divider', 'section-heading'].includes(nextKind);
        if (currentModule && !isSectionSeparator) {
          currentModule.items.push({ type: 'divider' });
        }
        break;
      }

      case 'blockquote': {
        // > 提示/注意/... → mention
        if (!currentModule) break;
        const txt = line.trim().replace(/^>\s*/, '');
        const role = detectRole(txt);
        currentModule.items.push({ type: 'mention', text: txt, ...(role ? { role } : {}) });
        break;
      }

      case 'sub-heading': {
        // ##### 1 问号按钮 → subtitle2 item，填入 小标题1
        if (!currentModule) break;
        const txt = line.trim().replace(/^#+\s*/, '');
        currentModule.items.push({ type: 'subtitle2', text: txt });
        break;
      }

      case 'type-label':
        // **类型：** xxx → 不渲染进 JSON，直接跳过
        break;

      case 'state-label': {
        // **控件状态：** 常态 / 按下态 / 热区 → diagram_states item
        if (!currentModule) break;
        const raw = line.trim().replace(/^\*\*控件状态[：:]\*\*\s*/, '');
        const states = raw.split(/\s*\/\s*/).map(s => s.trim()).filter(Boolean);
        currentModule.items.push({ type: 'diagram_states', states });
        break;
      }

      case 'slide-label': {
        // **滑动热区：** xxx → diagram_slide item
        if (!currentModule) break;
        const txt = line.trim().replace(/^\*\*滑动热区[：:]\*\*\s*/, '');
        currentModule.items.push({ type: 'diagram_slide', text: txt });
        break;
      }

      case 'image-ref': {
        // 【需要通用组件图示：xxx】 → diagram_image item
        if (!currentModule) break;
        const m = line.trim().match(/^【需要通用组件图示[：:](.+?)】$/);
        const txt = m ? m[1].trim() : line.trim();
        currentModule.items.push({ type: 'diagram_image', text: txt });
        break;
      }

      case 'hotspot-ref': {
        // 【需要交互图示，热区 ≥ 80px】 → diagram_hotspot（交互字段下方，多热区时）
        if (!currentModule) break;
        currentModule.items.push({ type: 'diagram_hotspot' });
        break;
      }

      case 'callout-ref': {
        // 【需要图示】 → diagram_callout（显示字段下方，内容较多时）
        if (!currentModule) break;
        currentModule.items.push({ type: 'diagram_callout' });
        break;
      }

      case 'section-divider': {
        // ## B. 方案说明 等 → 不创建新 section（内容已在 body 里），仅 skip
        // 若将来需要多 section 支持，在此处 push 新 section
        break;
      }

      case 'section-heading':
      case 'skip':
        break;

      case 'text': {
        if (!currentModule) break;
        pendingText.push(line);
        break;
      }
    }
  }

  flushText(); // 末尾可能有未 flush 的文本

  // ── 解析 ## A. 需求范围 ──
  // 格式：- [N] 界面名称 或 - [N] 名称
  let scope = undefined;
  const scopeMatch = text.match(/\n## [A-Z]\.\s*需求范围\n([\s\S]*?)(?=\n## [A-Z]\.|\n#{1,2} |$)/);
  if (scopeMatch) {
    const scopeTitleRaw = text.match(/\n(## [A-Z]\.\s*需求范围)/)?.[1]?.trim() ?? '## A. 需求范围';
    const scopeTitle = scopeTitleRaw.replace(/^##\s*/, '');

    // 建立 sections B 的 [N] 编号 → 已解析结果的索引，供 scope 直接继承
    // scope 显示名可随意加括号说明，不影响 frame 匹配
    const sectionsBIndex = {};
    for (const ui of uis) {
      const nm = ui.uiName.match(/^\[(\d+)\]/);
      if (nm) sectionsBIndex[nm[1]] = { componentName: ui.componentName, componentKey: ui.componentKey };
    }

    const scopeLines = scopeMatch[1].split('\n');
    const scopeUIs = [];
    for (const line of scopeLines) {
      const m = line.trim().match(/^[-*]\s*(\[(\d+)\]\s*.+)$/);
      if (!m) continue;
      const uiName    = m[1].trim();
      const nNum      = m[2];                         // 提取 [N] 编号
      const resolved  = sectionsBIndex[nNum];         // 从 sections B 继承
      const componentName = resolved?.componentName ?? uiName;
      const componentKey  = resolved?.componentKey  ?? undefined;
      scopeUIs.push({ uiName, componentName, ...(componentKey ? { componentKey } : {}) });
    }
    if (scopeUIs.length > 0) {
      scope = { title: scopeTitle, uis: scopeUIs };
    }
  }

  /** @type {import('../../../others/figma-plugin-doc/src/shared/g79-types').G79Doc} */
  const doc = {
    doc: {
      title:   meta.title   || '交互文档',
      version: meta.version || '',
      cehua:   meta.cehua   || '',
      uxd:     meta.uxd     || '',
    },
    ...(scope ? { scope } : {}),
    sections: [
      {
        docTitle: sectionBTitle,
        uis,
      },
    ],
  };

  return doc;
}

// ─── 自动分组（>= 5 个 UI 时按关键词分组，赋 subGroup 字段）──────────
/**
 * 从 uiName "[N] 界面名称-状态" 中提取关键词（去掉 [N] 前缀后的第一段）
 * "[1] 主界面"     → "主界面"
 * "[2] 主界面-组队" → "主界面"
 * "[3] 邀请界面"   → "邀请界面"
 */
function extractKeyword(uiName) {
  const cleaned = uiName.replace(/^\[\d+\]\s*/, '');
  return cleaned.split(/[-·\s（(]/)[0].trim();
}

function autoGroupUIs(uis) {
  if (uis.length < 5) return uis;

  // 相邻同前缀关键词归一组
  const groups = [];
  for (const ui of uis) {
    const kw = extractKeyword(ui.uiName);
    const last = groups[groups.length - 1];
    if (last && last.keyword === kw) {
      last.uis.push(ui);
    } else {
      groups.push({ keyword: kw, uis: [ui] });
    }
  }

  // 孤立组（只有 1 个 UI）合并到前一组
  const merged = [];
  for (let i = 0; i < groups.length; i++) {
    const g = groups[i];
    if (g.uis.length === 1 && merged.length > 0) {
      merged[merged.length - 1].uis.push(...g.uis);
    } else {
      merged.push({ ...g });
    }
  }

  // 命名并赋值 subGroup
  return merged.flatMap((g, idx) =>
    g.uis.map(ui => ({ ...ui, subGroup: `${idx + 1}-${g.keyword}相关` }))
  );
}

// ─── 执行 ──────────────────────────────────────────────────────────
const result = parseMd(mdText);

// 自动分组（覆盖 sections 里的 uis）
result.sections = result.sections.map(sec => ({
  ...sec,
  uis: autoGroupUIs(sec.uis),
}));

// 输出摘要
const totalUIs     = result.sections.reduce((s, sec) => s + sec.uis.length, 0);
const totalModules = result.sections.reduce(
  (s, sec) => s + sec.uis.reduce((ss, ui) => ss + ui.modules.length, 0), 0
);
const totalItems = result.sections.reduce(
  (s, sec) => s + sec.uis.reduce(
    (ss, ui) => ss + ui.modules.reduce((sss, m) => sss + m.items.length, 0), 0
  ), 0
);

fs.writeFileSync(outFile, JSON.stringify(result, null, 2), 'utf8');

console.log(`✅ 生成成功：${outFile}`);
console.log(`   标题：${result.doc?.title}`);
console.log(`   策划：${result.doc?.cehua}  设计师：${result.doc?.uxd}`);
console.log(`   共 ${totalUIs} 个界面，${totalModules} 个模块，${totalItems} 个 item`);
const mapLoaded = Object.keys(frameMap).length > 0;
if (!mapLoaded) {
  console.log(`   ⚠️  未找到 flat-map.json / frame-map.json，componentName 使用 uiName 代替`);
}

// 自动用系统默认程序打开生成的 JSON 文件
import { exec } from 'child_process';
const absOut = path.resolve(outFile);
exec(`code "${absOut}"`, err => {
  if (err) console.warn(`   ⚠️  自动打开失败：${err.message}`);
  else console.log(`   📂 已在 VSCode 中打开：${absOut}`);
});
