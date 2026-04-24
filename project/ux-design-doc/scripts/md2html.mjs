#!/usr/bin/env node
/**
 * md2html.mjs - 交互说明文档 Markdown → HTML 转换脚本 (v1.5)
 * 用法: node md2html.mjs <interaction-spec.md>
 * 输出: 同目录下 interaction-spec.html
 *
 * 文档结构：文档头 → ## A. 需求范围 → ## B. 方案说明
 *   界面块：### [N] 界面名称
 *   模块：  #### N. 名称
 *   子模块：##### N 名称
 */
import { readFileSync, writeFileSync, existsSync, statSync } from 'fs';
import { resolve, dirname, relative } from 'path';

const mdPath = process.argv[2];
if (!mdPath) { console.error('用法: node md2html.mjs <interaction-spec.md>'); process.exit(1); }
const fullPath = resolve(mdPath);
const baseDir  = dirname(fullPath);
const md = readFileSync(fullPath, 'utf-8');
const outPath = resolve(baseDir, 'interaction-spec.html');
const lines = md.split('\n');

// ── 文档头 ──
const head = { icon: '', version: '', title: '', planner: '', uxd: '' };
// 需求范围
const scopeItems = [];
// 界面块列表
const ifaces = [];
// 需求缺漏
const gaps = [];

let phase = 'head'; // head | scope | spec | gaps
let curIface = null, curMod = null, curSub = null;
let curField = null;
let curGapLevel = 'P2', curGap = null;

// ── flush helpers ──
function flushField() {
  if (!curField) return;
  const target = curSub || curMod;
  if (target) target.fields.push(curField);
  curField = null;
}
function flushSub() {
  flushField();
  if (curSub && curMod) { curMod.subs.push(curSub); curSub = null; }
}
function flushMod() {
  flushSub();
  flushField();
  if (curMod && curIface) { curIface.mods.push(curMod); curMod = null; }
}
function flushIface() {
  flushMod();
  if (curIface) { ifaces.push(curIface); curIface = null; }
}
function flushGap() {
  if (curGap) { gaps.push(curGap); curGap = null; }
}

const HEAD_KEYS = new Set(['icon','version','title','planner','uxd']);
// bold 形式的字段名（**xxx：**）
const KNOWN_BOLD_FIELDS = ['控件状态','滑动热区','空态','触发','子控件'];
// 数字列表形式的字段名（N. xxx：）
const KNOWN_LIST_FIELDS = ['显示','交互说明','交互反馈','交互'];

for (let i = 0; i < lines.length; i++) {
  const raw = lines[i];
  const t   = raw.trim();

  // ── 文档头：key: value ──
  if (phase === 'head') {
    const kv = t.match(/^(\w+)\s*:\s*(.+)/);
    if (kv && HEAD_KEYS.has(kv[1])) { head[kv[1]] = kv[2].trim(); continue; }
    if (t.startsWith('## A.')) { phase = 'scope'; continue; }
    if (t.startsWith('## B.')) { phase = 'spec'; continue; }
    // 跳过其他头部杂项
    continue;
  }

  // ── 需求范围 ──
  if (phase === 'scope') {
    if (t.startsWith('## B.')) { phase = 'spec'; continue; }
    if (t.startsWith('- ')) { scopeItems.push(t.slice(2).trim()); continue; }
    continue;
  }

  // ── 需求缺漏 ──
  if (phase === 'gaps') {
    const pm = t.match(/^### (P[012])/);
    if (pm) { flushGap(); curGapLevel = pm[1]; continue; }
    const gm = t.match(/^- \*\*(.+?)\*\*/);
    if (gm) { flushGap(); curGap = { level: curGapLevel, title: gm[1], desc: '' }; continue; }
    if (curGap && t) { curGap.desc += (curGap.desc ? ' ' : '') + t; }
    else if (curGap && !t) { flushGap(); }
    continue;
  }

  // ── 方案说明 ──

  // 切换到需求缺漏
  if (t === '## 需求缺漏' || t.startsWith('## 需求缺漏')) { flushIface(); phase = 'gaps'; continue; }

  // 忽略 ## 修改记录 及其后
  if (t.startsWith('## 修改记录')) break;

  // 忽略分隔线
  if (/^---+$/.test(t)) continue;

  // ── 界面块 ### [N] 名称 ──
  const ifaceM = t.match(/^### \[(\d+)\]\s+(.+)/);
  if (ifaceM) {
    flushIface();
    curIface = { num: ifaceM[1], name: ifaceM[2], design: '', mods: [] };
    continue;
  }

  // design: 路径（紧接界面块标题）
  if (curIface && !curMod) {
    const dm = t.match(/^design:\s*(.+)/);
    if (dm) { curIface.design = dm[1].trim(); continue; }
  }

  // ── 模块 #### N. 名称 ──
  const modM = t.match(/^#### (\d+)\.\s+(.+)/);
  if (modM) {
    flushMod();
    curMod = { num: modM[1], name: modM[2], type: '', fields: [], subs: [], mentions: [] };
    continue;
  }

  // ── 子模块 ##### N 名称（纯数字，无点） ──
  const subM = t.match(/^##### (\d+)\s+(.+)/);
  if (subM) {
    flushSub();
    curSub = { num: subM[1], name: subM[2], type: '', fields: [], mentions: [] };
    continue;
  }

  // ── 在模块/子模块内解析字段 ──
  if (!curMod && !curIface) continue;

  // 类型
  const typeM = t.match(/^\*\*类型：\*\*\s*(.+)/);
  if (typeM) {
    flushField();
    const target = curSub || curMod;
    if (target) target.type = typeM[1].trim();
    continue;
  }

  // @职能 — 存入 fields 保持顺序（kind: 'mention'）
  const mentM = t.match(/^\*\*(@\S+?)\*\*\s*(.+)/);
  if (mentM) {
    flushField();
    const target = curSub || curMod;
    if (target) target.fields.push({ kind: 'mention', tag: mentM[1], text: mentM[2] });
    continue;
  }

  // **控件状态：** value 等 bold 字段（同行值）
  const kvM = t.match(/^\*\*(.+?)：\*\*\s*(.+)/);
  if (kvM) {
    const label = kvM[1], value = kvM[2];
    const isKnown = KNOWN_BOLD_FIELDS.some(f => label.startsWith(f));
    flushField();
    if (isKnown) curField = { label, content: [value] };
    continue;
  }

  // **Label：**（值在下一行）bold 字段
  const fM = t.match(/^\*\*(.+?)：\*\*\s*$/);
  if (fM) {
    flushField();
    const isKnown = KNOWN_BOLD_FIELDS.some(f => fM[1].startsWith(f));
    if (isKnown) curField = { label: fM[1], content: [] };
    continue;
  }

  // N. 显示：/ N. 交互说明：/ N. 交互反馈：（数字列表字段头，规范格式；交互反馈为兼容旧格式）
  const listFieldM = t.match(/^(\d+)\.\s*(显示|交互说明|交互反馈|交互)：\s*$/);
  if (listFieldM) {
    flushField();
    const target = curSub || curMod;
    if (target) curField = { label: listFieldM[2], content: [] };
    continue;
  }

  // N. 文本（子模块内简写，如 "1. 有折扣：显示…" 或普通列表行）
  // 若当前有打开的 curField，当列表行收进去
  if (curField) {
    if (t) {
      // 遇到新字段起始行时先 flush 再 fall through
      if (/^\*\*(.+?)：\*\*/.test(t) || /^\*\*@\S+?\*\*\s/.test(t) || /^\d+\.\s*(显示|交互说明|交互反馈|交互)：\s*$/.test(t)) {
        flushField(); /* fall through */
      } else {
        curField.content.push(raw); continue; // 保留原始行（含缩进）
      }
    } else {
      flushField(); continue;
    }
  }

  // curField 为 null 时，遇到 `N. xxx` 普通列表行 → 作为无标题列表字段收集
  // （用于子模块简写场景，如 ##### 1 折扣标签 下的 "1. 有折扣：…"）
  if (/^\d+\.\s/.test(t) || /^\s+[a-zA-Z]\.\s/.test(raw) || /^\s+·/.test(raw)) {
    const target = curSub || curMod;
    if (target) {
      // 若没有打开字段，起一个匿名字段
      curField = { label: '', content: [raw] };
    }
    continue;
  }

  // 【需要图示】/ 【需要交互图示】单独一行（不在 curField 内时挂到当前 mod/sub）
  if (/^【需要/.test(t)) {
    const target = curSub || curMod;
    if (target) target.fields.push({ label: '__diagram__', content: [t] });
    continue;
  }
}
flushGap();
flushIface();

// ─────────────────────────────────────────
// HTML 生成工具
// ─────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmt(s) {
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/→/g, '<span class="arrow">→</span>');
  return s;
}

function atTagClass(tag) {
  if (tag.includes('策划')) return 'role-plan';
  if (tag.includes('GUI') || tag.includes('VX') || tag.includes('视觉')) return 'role-gui';
  if (tag.includes('程序') || tag.toLowerCase().includes('dev')) return 'role-dev';
  return 'role-plan';
}

function renderStates(rawText) {
  const parts = rawText.split(/\s*\/\s*/).filter(p => p.trim());
  const groups = {}, others = [];
  for (const p of parts) {
    const m = p.trim().match(/^(.+?)[-](.+)$/);
    if (m) {
      const gn = m[1].trim();
      if (!groups[gn]) groups[gn] = [];
      groups[gn].push(m[2].trim());
    } else {
      others.push(p.trim());
    }
  }
  let h = '';
  for (const [gn, sts] of Object.entries(groups)) {
    h += `<div class="state-row widget-state-group">`;
    h += `<span class="state-widget-name">${esc(gn)}</span>`;
    for (const s of sts) h += `<span class="state-tag">${esc(s)}</span>`;
    h += `</div>\n`;
  }
  if (others.length) {
    h += `<div class="state-row">`;
    for (const s of others) {
      const cls = /热区/.test(s) ? 'state-tag-hotzone' : 'state-tag';
      h += `<span class="${cls}">${esc(s)}</span>`;
    }
    h += `</div>\n`;
  }
  return h;
}

// ── 图示类型判断 ──
function diagramClass(text) {
  if (/热区/.test(text))         return 'diagram-tag-hotzone';
  if (/控件状态图示/.test(text)) return 'diagram-tag-state';
  if (/通用组件图示|通用界面图示|通用弹窗图示/.test(text)) return 'diagram-tag-generic';
  return 'diagram-tag-spec';
}

// ── 层级列表渲染 ──
// 把原始行（保留缩进）的数组转成嵌套 HTML 列表
function renderListItems(lines) {
  // 统计行缩进级别
  // level 0: `1. ` / `2. ` …    （数字列表，顶层段落）
  // level 1: `   a. ` / `   b. ` （字母，3+ 空格缩进）
  // level 2: `      · ` / `      - ` （6+ 空格缩进，bullet）
  // 也兼容 trim() 后直接是 a. 或 · 的行（旧格式）

  function getLevel(raw) {
    const spaces = raw.match(/^(\s*)/)[1].length;
    const t = raw.trim();
    if (/^\d+\./.test(t)) return 0;
    if (/^[a-zA-Z]\./.test(t)) return spaces >= 2 ? 1 : 0;
    if (/^·/.test(t) || /^-\s/.test(t)) return spaces >= 4 ? 2 : 1;
    return 1; // 默认内容行归 level 1
  }

  function getContent(raw) {
    const t = raw.trim();
    if (/^【需要/.test(t)) return { isDiagram: true, text: t };
    const text = t
      .replace(/^\d+\.\s*/, '')
      .replace(/^[a-zA-Z]\.\s*/, '')
      .replace(/^·\s*/, '')
      .replace(/^-\s+/, '');
    return { isDiagram: false, text };
  }

  // 把扁平行转成树结构
  const items = lines.map(raw => ({ raw, level: getLevel(raw), ...getContent(raw), children: [] }));
  // 构造嵌套
  const root = [];
  const stack = [{ level: -1, children: root }];
  for (const item of items) {
    while (stack.length > 1 && stack[stack.length-1].level >= item.level) stack.pop();
    stack[stack.length-1].children.push(item);
    stack.push(item);
  }

  function renderItems(nodes, depth) {
    if (!nodes.length) return '';
    const tag = depth === 0 ? 'ol' : 'ul';
    const cls = depth === 0 ? ' class="top-list"' : depth === 1 ? ' class="sub-list"' : ' class="deep-list"';
    let h = `<${tag}${cls}>\n`;
    for (const n of nodes) {
      if (n.isDiagram) {
        h += `<li class="diagram-hint-item"><div class="diagram-hint-row"><span class="diagram-hint-tag ${diagramClass(n.text)}">${esc(n.text)}</span></div></li>\n`;
      } else {
        h += `<li>${fmt(esc(n.text))}`;
        if (n.children.length) h += renderItems(n.children, depth + 1);
        h += `</li>\n`;
      }
    }
    h += `</${tag}>\n`;
    return h;
  }
  return renderItems(root, 0);
}

function renderMention(f) {
  return `<div class="mention-row"><span class="at-tag ${atTagClass(f.tag)}">${esc(f.tag)}</span> ${fmt(esc(f.text))}</div>\n`;
}

function renderField(f) {
  if (!f) return '';
  // @职能（inline，按顺序渲染）
  if (f.kind === 'mention') {
    return `<div class="mention-inline">${renderMention(f)}</div>\n`;
  }
  // 图示占位
  if (f.label === '__diagram__') {
    const hint = f.content[0] || '需要图示';
    return `<div class="diagram-hint-row"><span class="diagram-hint-tag ${diagramClass(hint)}">${esc(hint)}</span></div>\n`;
  }
  // 控件状态
  if (f.label && f.label.startsWith('控件状态')) {
    let h = `<div class="field-label">${esc(f.label)}</div>\n`;
    const brackets = f.content.join(' ').match(/\[([^\]]+)\]/g);
    if (brackets) {
      h += `<div class="state-row">`;
      for (const b of brackets) {
        const s = b.slice(1,-1);
        const cls = /热区/.test(s) ? 'state-tag-hotzone' : 'state-tag';
        h += `<span class="${cls}">${esc(s)}</span>`;
      }
      h += `</div>\n`;
    } else {
      h += renderStates(f.content.join(' '));
    }
    return h;
  }
  // 滑动热区
  if (f.label && (f.label.startsWith('滑动热区') || f.label.startsWith('热区'))) {
    let h = `<div class="field-label">${esc(f.label)}</div>\n`;
    if (f.content.length) h += `<div class="field-content">${fmt(esc(f.content.map(l=>l.trim()).join(' ')))}</div>\n`;
    h += `<div class="diagram-hint-row"><span class="diagram-hint-tag diagram-tag-hotzone">【需要热区示意图】</span></div>\n`;
    return h;
  }
  // 子控件清单（弱显示）
  if (f.label && f.label.startsWith('子控件')) {
    const chips = f.content.join(' ').split('/').map(s => s.trim()).filter(Boolean);
    let h = `<div class="subwidget-row"><span class="subwidget-label">子控件</span>`;
    for (const chip of chips) {
      h += `<span class="subwidget-chip">${esc(chip)}</span>`;
    }
    h += `</div>\n`;
    return h;
  }
  // 普通字段（显示/交互反馈/空态/触发 等）
  let h = f.label ? `<div class="field-label">${esc(f.label)}</div>\n` : '';
  const c = f.content;
  if (!c.length) return h;

  // 把图示行（【需要...】）从普通内容中分离出来，单独在列表外渲染
  const listLines = [], diagramLines = [];
  for (const line of c) {
    if (/^\s*【需要/.test(line)) diagramLines.push(line.trim());
    else listLines.push(line);
  }

  // 渲染列表内容
  if (listLines.length) {
    const isList = listLines.some(x => /^\s*[\d]+\./.test(x) || /^\s*[a-zA-Z]\./.test(x) || /^\s*·/.test(x));
    if (!isList && listLines.length === 1) {
      h += `<div class="field-content">${fmt(esc(listLines[0].trim()))}</div>\n`;
    } else {
      h += `<div class="field-content">${renderListItems(listLines)}</div>\n`;
    }
  }

  // 渲染图示占位（在列表外，无缩进）
  for (const d of diagramLines) {
    h += `<div class="diagram-hint-row"><span class="diagram-hint-tag ${diagramClass(d)}">${esc(d)}</span></div>\n`;
  }

  return h;
}

function renderMod(mod, ifaceNum) {
  const id = `iface-${ifaceNum}-m${mod.num}`;

  let h = `<div class="widget-block" id="${id}">\n`;
  h += `<div class="module-header-row">`;
  h += `<span class="module-num">${mod.num}</span>`;
  h += `<span class="module-header-title">${esc(mod.name)}</span>`;
  h += `</div>\n`;
  if (mod.type) h += `<div class="widget-type">${fmt(esc(mod.type))}</div>\n`;

  // mod.fields 包含 fields + mentions + subs（按 MD 顺序）
  // subs 通过单独数组存储，需要按插入顺序混合
  // 当前架构：fields 存 {label/kind}，subs 独立数组，我们按 fields 顺序渲染，subs 在最后
  // 实际 subs 在 MD 里通常都在字段之后，所以先渲染 fields，再渲染 subs
  for (const f of mod.fields) h += renderField(f);

  for (const sub of mod.subs) {
    h += `<div class="sub-mod-sep"></div>\n`;
    h += `<div class="sub-mod-header">`;
    h += `<span class="sub-mod-badge">${sub.num}</span>`;
    h += `<span class="sub-mod-name">${esc(sub.name)}</span>`;
    h += `</div>\n`;
    if (sub.type) h += `<div class="widget-type">${fmt(esc(sub.type))}</div>\n`;
    for (const f of sub.fields) h += renderField(f);
  }

  h += `</div>\n`;
  return h;
}

// ─────────────────────────────────────────
// CSS
// ─────────────────────────────────────────
const CSS = `
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: #111114; color: #c8c8cc; font-size: 16px; line-height: 1.7; }

/* ── 文档头 ── */
.doc-header { background: #0a0a0c; border: 1px solid #1e1e24; border-radius: 8px; padding: 20px 28px 16px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 28px; }
.doc-header-top { display: flex; align-items: center; justify-content: space-between; }
.doc-header-left { display: flex; align-items: center; gap: 14px; }
.doc-icon { width: 48px; height: 48px; border-radius: 10px; background: #1a3a1a; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
.doc-title-group { display: flex; flex-direction: column; gap: 2px; }
.doc-version { font-size: 13px; color: #555; font-family: monospace; }
.doc-title { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: 1px; }
.doc-brand { font-size: 14px; color: #444; font-weight: 700; letter-spacing: 2px; align-self: flex-end; }
.doc-header-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.doc-meta-names { font-size: 14px; color: #666; }
.doc-meta-names span { color: #888; }
.doc-meta-sep { color: #333; }
.doc-legend { display: flex; gap: 14px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 13px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.legend-dot.plan { background: #4a9eff; } .legend-item.plan { color: #4a9eff; }
.legend-dot.gui  { background: #48C75F; } .legend-item.gui  { color: #48C75F; }
.legend-dot.dev  { background: #ff5555; } .legend-item.dev  { color: #ff5555; }

/* ── 布局 ── */
.doc-layout { display: flex; height: 100vh; overflow: hidden; }
#sidebar { width: 240px; flex-shrink: 0; background: #0d0d10; border-right: 1px solid #1e1e22; padding: 24px 0; height: 100vh; overflow-y: auto; }
.doc-main { flex: 1; overflow: hidden; min-width: 0; }
#sidebar .sidebar-title { font-size: 12px; color: #3a3a40; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; padding: 0 18px 10px; border-bottom: 1px solid #1e1e22; margin-bottom: 10px; }
#sidebar .nav-group-label { font-size: 12px; color: #3a3a40; font-weight: 700; letter-spacing: 0.8px; padding: 6px 18px 3px; }
#sidebar .nav-iface-link { display: flex; align-items: center; gap: 8px; padding: 9px 18px; color: #ccc; text-decoration: none; font-size: 15px; font-weight: 600; transition: color 0.15s, background 0.15s; }
#sidebar .nav-iface-link:hover { color: #eee; background: #141418; }
#sidebar .nav-iface-link.active { color: #F5A623; background: #18180e; }
#sidebar .nav-iface-num { font-family: monospace; font-size: 12px; font-weight: 700; color: #888; background: #1e1e22; border: 1px solid #2e2e38; padding: 1px 6px; border-radius: 3px; flex-shrink: 0; }
#sidebar .nav-iface-link.active .nav-iface-num { color: #F5A623; border-color: #F5A62355; background: #241e00; }
#sidebar .nav-sub-link { display: flex; align-items: center; gap: 7px; padding: 6px 14px 6px 48px; color: #999; text-decoration: none; font-size: 14px; border-left: 2px solid transparent; transition: color 0.15s, background 0.15s, border-color 0.15s; }
#sidebar .nav-sub-link:hover { color: #ccc; background: #111116; }
#sidebar .nav-sub-link.active { color: #d4a830; background: #16140a; border-left-color: #F5A623; }
#sidebar .nav-sub-num { font-size: 12px; flex-shrink: 0; color: #666; }
#sidebar .nav-sub-link.active .nav-sub-num { color: #a07820; }
#sidebar .sep { border: none; border-top: 1px solid #1e1e22; margin: 8px 0; }
#sidebar .nav-scope { display: flex; align-items: center; gap: 8px; padding: 8px 18px; color: #555; text-decoration: none; font-size: 13px; transition: color 0.15s, background 0.15s; border-radius: 0; }
#sidebar .nav-scope:hover { color: #888; background: #111116; }
#sidebar .nav-scope.active { color: #aaa; background: #18181e; }

.doc-body { flex: 1; overflow-y: auto; padding: 32px 40px 80px; height: 100%; }
.doc-body-inner { max-width: 960px; margin: 0 auto; }

/* ── 节标题 ── */
.sec-heading { font-size: 14px; font-weight: 700; color: #555; letter-spacing: 1px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #1e1e22; }

/* ── 需求范围网格 ── */
.scope-section { margin-bottom: 40px; }
.scope-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.scope-card { background: #18181c; border: 1px solid #26262e; border-radius: 6px; overflow: hidden; transition: border-color 0.15s, transform 0.1s; cursor: pointer; }
.scope-card:hover { border-color: #F5A623; transform: translateY(-2px); }
.scope-thumb { width: 100%; aspect-ratio: 16/9; background: #1c1c22; display: flex; align-items: center; justify-content: center; color: #2e2e36; font-size: 12px; font-style: italic; overflow: hidden; border-bottom: 1px solid #26262e; }
.scope-thumb img { width: 100%; height: 100%; object-fit: cover; pointer-events: none; }
.scope-name { padding: 8px 12px; font-size: 14px; font-weight: 600; color: #aaa; text-align: center; }

/* ── 界面块 ── */
.iface-block { margin-bottom: 24px; scroll-margin-top: 24px; }
.iface-label { display: flex; align-items: center; gap: 10px; padding: 0 0 10px; margin-bottom: 0; border-bottom: 1px solid #2a2a2a; }
.iface-label-num { font-family: monospace; font-size: 13px; font-weight: 700; color: #888; background: #1e1e22; border: 1px solid #2e2e38; padding: 2px 8px; border-radius: 3px; flex-shrink: 0; }
.iface-label-name { color: #ddd; font-size: 20px; font-weight: 700; }
.iface-body { display: grid; grid-template-columns: 44% 1fr; align-items: start; border-bottom: 1px solid #1e1e22; margin-bottom: 24px; }
.iface-left { background: #0d0d10; border-right: 1px solid #1e1e22; display: flex; align-items: flex-start; justify-content: center; padding: 20px; position: sticky; top: 0; }
.iface-screenshot { width: 100%; max-width: 480px; aspect-ratio: 16/9; background: #181820; border: 1px solid #2a2a30; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #2e2e36; font-size: 12px; font-style: italic; overflow: hidden; cursor: pointer; transition: border-color 0.15s; }
.iface-screenshot:hover { border-color: #F5A62366; }
.iface-screenshot img { width: 100%; height: 100%; object-fit: cover; border-radius: 3px; pointer-events: none; }
.iface-right { padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; background: #111114; overflow-y: auto; }

/* ── 控件卡片 ── */
.widget-block { background: #1c1c21; border-radius: 6px; padding: 14px 18px; border: 1px solid #26262e; }
.module-header-row { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; padding-bottom: 9px; border-bottom: 1px solid #26262e; }
.module-num { background: #F5A623; color: #1a1a1f; width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 900; flex-shrink: 0; }
.module-header-title { font-size: 16px; font-weight: 700; color: #F5A623; }
.widget-type { font-size: 13px; color: #555; font-style: italic; margin-bottom: 8px; }
.widget-generic { padding: 10px 16px; display: flex; align-items: center; gap: 10px; background: #17171b; border: 1px solid #22222a; border-radius: 6px; }
.widget-generic .wg-name { font-size: 15px; font-weight: 600; color: #999; }
.widget-generic .wg-type { font-size: 13px; color: #444; font-style: italic; }

/* ── 子模块 ── */
.sub-mod-sep { border-top: 1px solid #26262e; margin: 14px 0 12px; }
.sub-mod-header { display: inline-flex; align-items: center; gap: 7px; margin-bottom: 8px; }
.sub-mod-badge { background: #F5A623; color: #1a1a1f; padding: 2px 9px; border-radius: 4px; font-size: 12px; font-weight: 900; flex-shrink: 0; }
.sub-mod-name { font-size: 15px; font-weight: 700; color: #ddd; }

/* ── 字段 ── */
.field-label { font-size: 13px; color: #777; font-weight: 600; margin-top: 10px; margin-bottom: 4px; letter-spacing: 0.5px; }
.field-content { font-size: 16px; color: #ddd; line-height: 1.85; }
.field-content ol { padding-left: 16px; }
.field-content ol li { margin-bottom: 4px; }
.arrow { font-weight: 700; color: #fff; }

/* ── 状态标签 ── */
.state-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; background: #0e0e12; border-radius: 6px; padding: 8px 10px; align-items: center; }
.state-row.widget-state-group { margin-bottom: 6px; }
.state-widget-name { font-size: 13px; color: #777; font-weight: 600; margin-right: 6px; padding-right: 8px; border-right: 1px solid #2e2e36; }
.state-tag { background: #26262e; border: 1px solid #32323c; color: #bbb; padding: 4px 12px; border-radius: 5px; font-size: 14px; }
.subwidget-row { display: flex; align-items: center; gap: 6px; margin: 2px 0 8px; opacity: 0.5; }
.subwidget-label { font-size: 11px; color: #888; white-space: nowrap; }
.subwidget-chip { font-size: 11px; background: rgba(255,255,255,0.05); color: #999; border: 1px solid rgba(255,255,255,0.1); border-radius: 3px; padding: 1px 7px; }
.state-tag-hotzone { background: #0a1a2e; border: 1px solid #4a9eff55; color: #4a9eff; padding: 4px 12px; border-radius: 5px; font-size: 14px; }
.diagram-hint-item { list-style: none; margin: 6px 0; padding: 0; }
.diagram-hint-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; background: #0e0e12; border-radius: 6px; padding: 8px 10px; align-items: center; }
.diagram-hint-tag { background: transparent; border: 1px dashed #3a3a50; color: #5a5a70; padding: 4px 12px; border-radius: 5px; font-size: 14px; font-style: normal; display: inline-flex; align-items: center; gap: 5px; }
.diagram-hint-tag::before { content: ""; }
.diagram-hint-tag.diagram-tag-spec::before    { content: ""; width: 8px; height: 8px; background: #48C75F; border-radius: 2px; flex-shrink: 0; }
.diagram-hint-tag.diagram-tag-hotzone::before { content: ""; width: 8px; height: 8px; background: #4a9eff; border-radius: 2px; flex-shrink: 0; }
.diagram-hint-tag.diagram-tag-state::before   { content: ""; width: 8px; height: 8px; background: #a855f7; border-radius: 2px; flex-shrink: 0; }
.diagram-hint-tag.diagram-tag-generic::before { content: ""; width: 8px; height: 8px; background: #F5A623; border-radius: 2px; flex-shrink: 0; }

/* ── @职能 ── */
.mention-block { margin-top: 12px; border-top: 1px solid #26262e; padding-top: 9px; display: flex; flex-direction: column; gap: 5px; }
.mention-row { font-size: 15px; color: #bbb; line-height: 1.8; display: flex; gap: 7px; align-items: flex-start; flex-wrap: wrap; }
.at-tag { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 700; flex-shrink: 0; }
.at-tag.role-plan { background: #1e3a7a; border: 1px solid #4a9eff44; color: #4a9eff; }
.at-tag.role-gui  { background: #1a4a26; border: 1px solid #48C75F44; color: #48C75F; }
.at-tag.role-dev  { background: #5c1a1a; border: 1px solid #ff555544; color: #ff8080; }

/* ── 需求缺漏 ── */
.gap-block { padding: 10px 0; border-bottom: 1px solid #26262e; }
.gap-block:last-child { border-bottom: none; padding-bottom: 0; }
.gap-level { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 3px; font-size: 13px; font-weight: 700; margin-right: 6px; }
.gap-level.p0 { background: #5c1a1a; color: #ff6b6b; }
.gap-level.p1 { background: #3d2c00; color: #F5A623; }
.gap-level.p2 { background: #1a2a1a; color: #48C75F; }
.gap-title { font-size: 15px; color: #fff; font-weight: 600; }
.gap-desc { font-size: 15px; color: #777; margin-top: 4px; line-height: 1.7; }

.doc-footer { text-align: center; color: #2e2e36; font-size: 14px; padding: 32px 0; margin-top: 48px; border-top: 1px solid #1e1e22; }

/* ── mention inline（按 MD 顺序排列） ── */
.mention-inline { margin-top: 10px; }
.mention-inline .mention-row { font-size: 15px; color: #bbb; line-height: 1.8; display: flex; gap: 7px; align-items: flex-start; flex-wrap: wrap; }

/* ── 列表层级 ── */
.field-content .top-list { padding-left: 18px; margin: 4px 0; }
.field-content .top-list > li { margin-bottom: 6px; line-height: 1.85; }
.field-content .sub-list { padding-left: 14px; margin: 4px 0; list-style: none; }
.field-content .sub-list > li { margin-bottom: 4px; color: #c0c0c8; }
.field-content .sub-list > li::before { content: ""; }
.field-content .deep-list { padding-left: 14px; margin: 3px 0; list-style: none; }
.field-content .deep-list > li { margin-bottom: 2px; color: #888; font-size: 13px; }
.field-content .deep-list > li::before { content: "· "; color: #555; }

/* ── 灯箱 ── */
#lightbox { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.88); z-index: 9999; align-items: center; justify-content: center; }
#lightbox.open { display: flex; }
#lightbox img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 6px; box-shadow: 0 8px 48px #000; }
#lightbox-close { position: absolute; top: 20px; right: 28px; color: #888; font-size: 32px; cursor: pointer; line-height: 1; transition: color 0.15s; }
#lightbox-close:hover { color: #fff; }
`;

// ─────────────────────────────────────────
// Scroll-spy JS
// ─────────────────────────────────────────
const JS = `
// ── 灯箱 ──
const lb = document.getElementById('lightbox');
const lbImg = document.getElementById('lightbox-img');
document.getElementById('lightbox-close').addEventListener('click', () => lb.classList.remove('open'));
lb.addEventListener('click', e => { if (e.target === lb) lb.classList.remove('open'); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') lb.classList.remove('open'); });

function openLightbox(src) { lbImg.src = src; lb.classList.add('open'); }

// 界面截图点击放大
document.querySelectorAll('.iface-screenshot img').forEach(img => {
  img.parentElement.addEventListener('click', () => openLightbox(img.src));
});

// scope 卡片点击跳转
document.querySelectorAll('.scope-card[data-iface]').forEach(card => {
  card.addEventListener('click', () => {
    const id = 'iface-' + card.dataset.iface;
    const el = document.getElementById(id);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); activateById(id); }
  });
});

// scope 缩略图点击放大（阻止冒泡避免触发卡片跳转）
document.querySelectorAll('.scope-thumb img').forEach(img => {
  img.addEventListener('click', e => { e.stopPropagation(); openLightbox(img.src); });
});

const allLinks = document.querySelectorAll('#sidebar a');
const clearAll = () => allLinks.forEach(l => l.classList.remove('active'));

const activateById = (id) => {
  clearAll();
  const sub = document.querySelector('#sidebar .nav-sub-link[href="#'+id+'"]');
  if (sub) {
    sub.classList.add('active');
    const ifaceId = id.replace(/-m\\d+$/, '');
    const par = document.querySelector('#sidebar .nav-iface-link[href="#'+ifaceId+'"]');
    if (par) par.classList.add('active');
    return;
  }
  const iface = document.querySelector('#sidebar .nav-iface-link[href="#'+id+'"]');
  if (iface) iface.classList.add('active');
  const scope = document.querySelector('#sidebar .nav-scope[href="#'+id+'"]');
  if (scope) scope.classList.add('active');
};

// 点击跳转时立即激活
allLinks.forEach(l => l.addEventListener('click', () => {
  const id = l.getAttribute('href').slice(1);
  activateById(id);
}));

// Scroll-spy：观察所有锚点，取「已过顶部阈值」中最后一个（top 最大）
const scrollRoot = document.querySelector('.doc-body');
const targets = [...document.querySelectorAll('#scope, .iface-block[id], .widget-block[id]')];
let ticking = false;
scrollRoot.addEventListener('scroll', () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    ticking = false;
    const rootRect = scrollRoot.getBoundingClientRect();
    const line = rootRect.height * 0.25; // 25% 处为判断基准线
    let best = null, bestTop = -Infinity;
    for (const el of targets) {
      const top = el.getBoundingClientRect().top - rootRect.top;
      // 已越过基准线（top <= line），取最靠近基准线的（top 最大）
      if (top <= line && top > bestTop) { bestTop = top; best = el; }
    }
    // fallback：全部在基准线以下时，取距顶部最近的
    if (!best) {
      let minTop = Infinity;
      for (const el of targets) {
        const top = el.getBoundingClientRect().top - rootRect.top;
        if (top < minTop) { minTop = top; best = el; }
      }
    }
    if (best) activateById(best.id);
  });
}, { passive: true });

// 初始激活
if (targets.length) activateById(targets[0].id);
`;

// ─────────────────────────────────────────
// 拼 HTML
// ─────────────────────────────────────────

// 文档头
const headerHtml = `
<header class="doc-header">
  <div class="doc-header-top">
    <div class="doc-header-left">
      <div class="doc-icon">${esc(head.icon)}</div>
      <div class="doc-title-group">
        <span class="doc-version">${esc(head.version)}</span>
        <span class="doc-title">${esc(head.title)}</span>
      </div>
    </div>
    <div class="doc-brand">FIT-ARK &nbsp; DESIGN</div>
  </div>
  <div class="doc-header-meta">
    <div class="doc-meta-names">策划 <span>${esc(head.planner)}</span><span class="doc-meta-sep"> ｜ </span>UXD <span>${esc(head.uxd)}</span></div>
    <div class="doc-legend">
      <span class="legend-item plan"><span class="legend-dot plan"></span>策划注意</span>
      <span class="legend-item gui"><span class="legend-dot gui"></span>GUI/VX注意</span>
      <span class="legend-item dev"><span class="legend-dot dev"></span>程序注意</span>
    </div>
  </div>
</header>`;

// 侧边栏
let sidebarHtml = `<nav id="sidebar">\n<div class="sidebar-title">界面导航</div>\n`;
sidebarHtml += `<a class="nav-scope" href="#scope"><span style="color:#3a3a40;font-size:14px;font-weight:700">A</span> 需求范围</a>\n<hr class="sep">\n`;
for (const iface of ifaces) {
  const ifaceId = `iface-${iface.num}`;
  sidebarHtml += `<a class="nav-iface-link" href="#${ifaceId}"><span class="nav-iface-num">[${iface.num}]</span>${esc(iface.name)}</a>\n`;
  for (const mod of iface.mods) {
    const modId = `iface-${iface.num}-m${mod.num}`;
    const circleNums = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩'];
    const circle = circleNums[parseInt(mod.num)-1] || mod.num;
    sidebarHtml += `<a class="nav-sub-link" href="#${modId}"><span class="nav-sub-num">${circle}</span>${esc(mod.name)}</a>\n`;
  }
}
if (gaps.length) {
  sidebarHtml += `<hr class="sep">\n<a class="nav-scope" href="#gaps"><span style="color:#6b8af0;font-size:14px;font-weight:700">!</span> 需求缺漏</a>\n`;
}
sidebarHtml += `</nav>`;

// 主内容
let bodyHtml = `<div class="doc-body">\n<div class="doc-body-inner">\n`;
bodyHtml += headerHtml + '\n';

// A. 需求范围 — 匹配界面设计图
bodyHtml += `<section class="scope-section" id="scope">\n<div class="sec-heading">A. 需求范围</div>\n<div class="scope-grid">\n`;
for (let si = 0; si < scopeItems.length; si++) {
  const name = scopeItems[si];
  const iface = ifaces[si]; // 顺序对应
  const ifaceNum = iface ? iface.num : (si + 1);
  let thumbHtml = '';
  if (iface && iface.design) {
    const imgPath = resolve(baseDir, iface.design);
    const isFile = existsSync(imgPath) && statSync(imgPath).isFile();
    if (isFile) thumbHtml = `<img src="${esc(iface.design)}" alt="${esc(name)}">`;
  }
  bodyHtml += `<div class="scope-card" data-iface="${ifaceNum}"><div class="scope-thumb">${thumbHtml}</div><div class="scope-name">${esc(name)}</div></div>\n`;
}
bodyHtml += `</div>\n</section>\n\n`;

// B. 方案说明
bodyHtml += `<section class="spec-section">\n<div class="sec-heading">B. 方案说明</div>\n`;
for (const iface of ifaces) {
  const ifaceId = `iface-${iface.num}`;
  bodyHtml += `<div class="iface-block" id="${ifaceId}">\n`;
  bodyHtml += `<div class="iface-label"><span class="iface-label-num">[${iface.num}]</span><span class="iface-label-name">${esc(iface.name)}</span></div>\n`;
  bodyHtml += `<div class="iface-body">\n`;
  // 左：截图
  bodyHtml += `<div class="iface-left">\n<div class="iface-screenshot">`;
  if (iface.design) {
    const imgPath = resolve(baseDir, iface.design);
    const isFile = existsSync(imgPath) && statSync(imgPath).isFile();
    if (isFile) {
      bodyHtml += `<img src="${esc(iface.design)}" alt="${esc(iface.name)}">`;
    }
    // 路径是目录或文件不存在时，留空（CSS 已有暗色占位块）
  }
  bodyHtml += `</div>\n</div>\n`;
  // 右：模块列表
  bodyHtml += `<div class="iface-right">\n`;
  for (let mi = 0; mi < iface.mods.length; mi++) {
    bodyHtml += renderMod(iface.mods[mi], iface.num);
  }
  bodyHtml += `</div>\n`;
  bodyHtml += `</div>\n`; // iface-body
  bodyHtml += `</div>\n`; // iface-block
}
bodyHtml += `</section>\n\n`;

// 需求缺漏
if (gaps.length) {
  bodyHtml += `<section id="gaps">\n<div class="sec-heading">需求缺漏</div>\n`;
  bodyHtml += `<div class="widget-block">\n`;
  bodyHtml += `<div class="module-header-row"><span class="module-num" style="background:#6b8af0;">!</span><span class="module-header-title" style="color:#6b8af0;">需求缺漏识别</span></div>\n`;
  for (const g of gaps) {
    bodyHtml += `<div class="gap-block">\n`;
    bodyHtml += `<span class="gap-level ${g.level.toLowerCase()}">${g.level}</span>`;
    bodyHtml += `<span class="gap-title">${esc(g.title)}</span>\n`;
    if (g.desc) bodyHtml += `<div class="gap-desc">${esc(g.desc)}</div>\n`;
    bodyHtml += `</div>\n`;
  }
  bodyHtml += `</div>\n</section>\n`;
}

bodyHtml += `<div class="doc-footer">FIT-ARK DESIGN &nbsp;·&nbsp; ${esc(head.title)} &nbsp;·&nbsp; ${esc(head.uxd)}</div>\n`;
bodyHtml += `</div>\n</div>\n`;

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(head.title || '交互说明文档')}</title>
<style>${CSS}</style>
</head>
<body>
<div class="doc-layout">
${sidebarHtml}
<div class="doc-main">
${bodyHtml}
</div>
</div>
<div id="lightbox"><span id="lightbox-close">✕</span><img id="lightbox-img" src="" alt=""></div>
<script>${JS}</script>
</body>
</html>`;

writeFileSync(outPath, html, 'utf-8');
console.log(`✅ 生成完成: ${outPath}`);