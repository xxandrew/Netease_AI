#!/usr/bin/env node
/**
 * interaction-spec MD 格式检查脚本
 * 版本: v1.5 | 支持三段式结构（文档头 + A.需求范围 + B.方案说明）
 * 用法: node validate.mjs <interaction-spec.md>
 *
 * 结构层级：
 *   文档头：  key: value（icon/version/title/planner/uxd）
 *   界面块：  ### [N] 名称
 *   模块：    #### N. 名称
 *   子模块：  ##### N 名称
 */

import fs from 'fs';
import path from 'path';

// ── 逐行格式规则 ──
const LINE_CHECKS = [
  {
    name: '控件状态格式检查',
    test: (line) => /\*\*控件状态：\*\*/.test(line) && /[\-\*]\s/.test(line.split('**控件状态：**')[1] || ''),
    message: '控件状态不能用列表格式。正确：**控件状态：** 常态 / 按下态',
    severity: 'error'
  },
  {
    name: 'Toast 格式检查',
    test: (line) => /toast[^<\n]*[""'"']/i.test(line),
    message: 'Toast 内容应使用尖括号：<内容>',
    severity: 'warning'
  },
  {
    name: '箭头使用检查',
    test: (line) => /(?:状态|态)\s*[:：]\s*[^\n]*→/.test(line),
    message: '→ 只用于「交互行为 → 结果反馈」，状态描述改用冒号',
    severity: 'warning'
  },
  {
    name: '旧式界面块语法',
    test: (line) => /^##\s+\d+[\.\s]/.test(line) && !/^## [AB]\./.test(line),
    message: '旧格式：## N. 名称 → 请改为 v1.5 格式：### [N] 名称',
    severity: 'warning'
  },
  {
    name: '旧式模块语法',
    test: (line) => /^###\s+\d+\.\s+/.test(line) && !/^\#{4}/.test(line),
    message: '旧格式：### N. 名称 → 请改为 v1.5 格式：#### N. 名称',
    severity: 'warning'
  }
];

// ── 文档头检查 ──
const HEAD_KEYS = ['icon', 'version', 'title', 'planner', 'uxd'];

function checkHead(lines) {
  const issues = [];
  const found = new Set();

  for (const line of lines) {
    const t = line.trim();
    if (t.startsWith('## ')) break; // 文档头结束
    const kv = t.match(/^(\w+)\s*:\s*(.+)/);
    if (kv && HEAD_KEYS.includes(kv[1])) {
      found.add(kv[1]);
    }
  }

  for (const key of HEAD_KEYS) {
    if (!found.has(key)) {
      issues.push({
        line: 1,
        check: '文档头字段检查',
        message: `文档头缺少必填字段：${key}`,
        severity: 'error',
        content: `缺少：${key}: ...`
      });
    }
  }
  return issues;
}

// ── 结构检查 ──
function checkStructure(lines) {
  const issues = [];

  let hasA = false, hasB = false;
  let ifaceNums = [];
  let curIface = null;
  let modNums = [];
  let curMod = null;
  let modHasContent = false;

  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    const lineNum = i + 1;

    // 需求范围
    if (t.startsWith('## A.')) { hasA = true; continue; }
    if (t.startsWith('## B.')) { hasB = true; curIface = null; modNums = []; continue; }

    if (!hasB) continue; // B 节之前不校验结构

    // 界面块 ### [N]
    const ifaceMatch = t.match(/^###\s+\[(\d+)\]\s+(.+)/);
    if (ifaceMatch) {
      // 检查上一个模块是否有内容
      if (curMod && !modHasContent) {
        issues.push({
          line: curMod.line,
          check: '模块内容检查',
          message: `模块 "${curMod.name}" 缺少字段内容（**类型：**、**显示：** 等）`,
          severity: 'error',
          content: lines[curMod.line - 1].substring(0, 80)
        });
      }
      const num = parseInt(ifaceMatch[1]);
      // 检查界面编号连续性
      if (ifaceNums.length > 0 && num !== ifaceNums[ifaceNums.length - 1] + 1) {
        issues.push({
          line: lineNum,
          check: '界面编号连续性',
          message: `界面编号不连续：期望 [${ifaceNums[ifaceNums.length - 1] + 1}]，实际 [${num}]`,
          severity: 'warning',
          content: t.substring(0, 80)
        });
      }
      ifaceNums.push(num);
      curIface = { num, name: ifaceMatch[2], line: lineNum };
      modNums = [];
      curMod = null;
      modHasContent = false;
      continue;
    }

    // 模块 #### N.
    const modMatch = t.match(/^####\s+(\d+)\.\s+(.+)/);
    if (modMatch) {
      // 检查上一个模块
      if (curMod && !modHasContent) {
        issues.push({
          line: curMod.line,
          check: '模块内容检查',
          message: `模块 "${curMod.name}" 缺少字段内容`,
          severity: 'error',
          content: lines[curMod.line - 1].substring(0, 80)
        });
      }
      if (!curIface) {
        issues.push({
          line: lineNum,
          check: '模块归属检查',
          message: `模块 "${modMatch[2]}" 不在任何界面块（### [N]）内`,
          severity: 'error',
          content: t.substring(0, 80)
        });
      }
      const num = parseInt(modMatch[1]);
      // 检查模块编号连续性
      if (modNums.length > 0 && num !== modNums[modNums.length - 1] + 1) {
        issues.push({
          line: lineNum,
          check: '模块编号连续性',
          message: `模块编号不连续：期望 ${modNums[modNums.length - 1] + 1}.，实际 ${num}.`,
          severity: 'warning',
          content: t.substring(0, 80)
        });
      }
      modNums.push(num);
      curMod = { num, name: modMatch[2], line: lineNum };
      modHasContent = false;
      continue;
    }

    // 子模块 ##### N（允许，不额外校验编号）
    // 检测模块是否有字段内容
    // bold 字段（类型/控件状态/滑动热区/空态/子控件/交互反馈）算有内容
    if (curMod && /^\*\*(?:类型|控件状态|滑动热区|空态|子控件|交互反馈)：\*\*/.test(t)) {
      modHasContent = true;
    }
    // 列表字段头（1. 显示：/ 2. 交互说明：等）算有内容
    if (curMod && /^\d+\.\s*(?:显示|交互说明|交互反馈|交互)：/.test(t)) {
      modHasContent = true;
    }
    // 普通列表行也算有内容
    if (curMod && /^[1-9a-z]\.\s/.test(t)) {
      modHasContent = true;
    }
  }

  // 收尾：检查最后一个模块
  if (curMod && !modHasContent) {
    issues.push({
      line: curMod.line,
      check: '模块内容检查',
      message: `模块 "${curMod.name}" 缺少字段内容`,
      severity: 'error',
      content: lines[curMod.line - 1].substring(0, 80)
    });
  }

  if (!hasA) issues.push({ line: 1, check: '文档结构检查', message: '缺少 ## A. 需求范围 章节', severity: 'error', content: '' });
  if (!hasB) issues.push({ line: 1, check: '文档结构检查', message: '缺少 ## B. 方案说明 章节', severity: 'error', content: '' });

  return issues;
}

// ── 控件必须说明项映射表（来源：widget-templates.md 各控件「必须说明」章节）──
// 新增控件规则：在此数组中追加条目即可，无需修改检查逻辑
const WIDGET_TEMPLATE_RULES = [
  {
    name: '按钮 Button',
    typeMatch: /按钮|button/i,
    typeExclude: /通用控件|图标按钮|付费按钮/,
    checks: [
      {
        checkName: '按钮-控件状态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*/.test(l.text)),
        message: (n) => `按钮类控件 "${n}" 缺少 **控件状态：** 字段`
      },
      {
        checkName: '按钮-按下态缺失',
        skipIf: (lines) => !lines.some(l => /^\*\*控件状态：\*\*/.test(l.text)),
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*按下态/.test(l.text)),
        message: (n) => `按钮类控件 "${n}" 的控件状态缺少「按下态」`
      }
    ]
  },
  {
    name: '图标按钮 Icon Button',
    typeMatch: /图标按钮/,
    checks: [
      {
        checkName: '图标按钮-显示字段缺失',
        test: (lines) => lines.some(l => /^1\.\s*显示/.test(l.text)),
        message: (n) => `图标按钮 "${n}" 缺少「显示」字段（必须注明图标内容）`
      },
      {
        checkName: '图标按钮-按下态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*按下态/.test(l.text)),
        message: (n) => `图标按钮 "${n}" 的控件状态缺少「按下态」`
      }
    ]
  },
  {
    name: '页签 Tab',
    typeMatch: /页签|[Tt]ab/,
    checks: [
      {
        checkName: '页签-选中态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*选中态/.test(l.text)),
        message: (n) => `页签 Tab "${n}" 的控件状态缺少「选中态」`
      },
      {
        checkName: '页签-交互说明缺少切换',
        test: (lines) => lines.some(l => /切换/.test(l.text)),
        message: (n) => `页签 Tab "${n}" 的交互说明缺少「点击 → 切换」`
      }
    ]
  },
  {
    name: '开关 Toggle',
    typeMatch: /开关|[Tt]oggle/,
    checks: [
      {
        checkName: '开关-状态缺少开关值',
        test: (lines) => {
          const s = lines.find(l => /^\*\*控件状态：\*\*/.test(l.text));
          return s && (/开启/.test(s.text) || /关闭/.test(s.text) || /开\s*\//.test(s.text));
        },
        message: (n) => `开关 Toggle "${n}" 的控件状态缺少「开启/关闭」状态`
      }
    ]
  },
  {
    name: '单选框 Radio',
    typeMatch: /单选框|[Rr]adio/,
    checks: [
      {
        checkName: '单选框-选中态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*选中态/.test(l.text)),
        message: (n) => `单选框 "${n}" 的控件状态缺少「选中态」`
      },
      {
        checkName: '单选框-热区缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*热区/.test(l.text)),
        message: (n) => `单选框 "${n}" 的控件状态缺少「点击热区(≥80px)」（热区须覆盖图标+文本）`
      }
    ]
  },
  {
    name: '复选框 Checkbox',
    typeMatch: /复选框|[Cc]heckbox/,
    checks: [
      {
        checkName: '复选框-选中态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*选中态/.test(l.text)),
        message: (n) => `复选框 "${n}" 的控件状态缺少「选中态」`
      }
    ]
  },
  {
    name: '输入框 Textfield',
    typeMatch: /输入框|[Tt]extfield/,
    checks: [
      {
        checkName: '输入框-唤起键盘缺失',
        test: (lines) => lines.some(l => /唤起键盘/.test(l.text)),
        message: (n) => `输入框 "${n}" 的交互说明缺少「点击 → 唤起键盘（带输入框）」`
      }
    ]
  },
  {
    name: '搜索框 Search',
    typeMatch: /搜索框|[Ss]earch/,
    checks: [
      {
        checkName: '搜索框-唤起键盘缺失',
        test: (lines) => lines.some(l => /唤起键盘/.test(l.text)),
        message: (n) => `搜索框 "${n}" 的交互说明缺少「点击 → 唤起键盘（带输入框）」`
      }
    ]
  },
  {
    name: '滑动条 Slider',
    typeMatch: /滑动条|[Ss]lider/,
    checks: [
      {
        checkName: '滑动条-显示字段缺失',
        test: (lines) => lines.some(l => /^1\.\s*显示/.test(l.text)),
        message: (n) => `滑动条 "${n}" 缺少「显示」字段（须注明最小值、最大值、当前值）`
      },
      {
        checkName: '滑动条-交互说明缺少滑动',
        test: (lines) => lines.some(l => /滑动/.test(l.text)),
        message: (n) => `滑动条 "${n}" 的交互说明缺少「横向滑动 → 调整数值」`
      }
    ]
  },
  {
    name: '列表 List',
    typeMatch: /列表|清单|滚动列表/,
    checks: [
      {
        checkName: '列表-滑动热区缺失',
        test: (lines) => lines.some(l => /^\*\*滑动热区：\*\*/.test(l.text)),
        message: (n) => `列表类控件 "${n}" 缺少 **滑动热区：** 字段`
      }
    ]
  },
  {
    name: '更多操作按钮 More Button',
    typeMatch: /更多操作按钮/,
    checks: [
      {
        checkName: '更多操作按钮-浮层关闭缺失',
        test: (lines) => lines.some(l => /浮层外.*关闭|关闭浮层/.test(l.text)),
        message: (n) => `更多操作按钮 "${n}" 的交互说明缺少「点击浮层外任意位置 → 关闭浮层」`
      },
      {
        checkName: '更多操作按钮-热区缺失',
        test: (lines) => lines.some(l =>
          /^\*\*控件状态：\*\*.*热区/.test(l.text) ||
          /^\*\*点击热区：\*\*/.test(l.text)
        ),
        message: (n) => `更多操作按钮 "${n}" 的控件状态缺少「点击热区(≥80px)」`
      }
    ]
  },
  {
    name: '下拉框 Droplist',
    typeMatch: /下拉框|[Dd]roplist/,
    checks: [
      {
        checkName: '下拉框-展开态缺失',
        test: (lines) => lines.some(l => /^\*\*控件状态：\*\*.*展开/.test(l.text)),
        message: (n) => `下拉框 "${n}" 的控件状态缺少「展开」态`
      }
    ]
  },
];

// ── 控件规范检查 ──
/**
 * 解析每个 #### 模块的内容，按控件类型执行规范检查
 * 检查点：
 *   1. 每个模块必须有 **类型：**
 *   2. 按 WIDGET_TEMPLATE_RULES 检查各控件必须说明项（统一映射，可扩展）
 *   3. 提到「通用弹窗 / 通用组件」→ 必须有「【需要通用组件图示：」
 */
function checkWidgetRules(lines) {
  const issues = [];

  // 将文档解析为模块单元（#### 级别）
  const modules = [];
  let cur = null;
  let inB = false;

  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    const lineNum = i + 1;

    if (t.startsWith('## B.')) { inB = true; continue; }
    if (!inB) continue;

    const modMatch = t.match(/^####\s+\d+\.\s+(.+)/);
    if (modMatch) {
      if (cur) modules.push(cur);
      cur = { name: modMatch[1], line: lineNum, contentLines: [] };
      continue;
    }

    if (cur) cur.contentLines.push({ text: t, lineNum });
  }
  if (cur) modules.push(cur);

  for (const mod of modules) {
    const lines_ = mod.contentLines;

    // ── 规则 1：必须有 **类型：** ──
    const typeLine = lines_.find(l => /^\*\*类型：\*\*/.test(l.text));
    if (!typeLine) {
      issues.push({
        line: mod.line,
        check: '控件类型缺失',
        message: `模块 "${mod.name}" 缺少 **类型：** 字段（必填）`,
        severity: 'error',
        content: `#### ${mod.name}`
      });
      continue; // 没有类型无法做后续检查
    }

    const typeVal = typeLine.text.replace(/^\*\*类型：\*\*\s*/, '').trim();

    // ── 规则 2：按 WIDGET_TEMPLATE_RULES 统一检查各控件必须说明项 ──
    for (const widgetRule of WIDGET_TEMPLATE_RULES) {
      if (!widgetRule.typeMatch.test(typeVal)) continue;
      if (widgetRule.typeExclude && widgetRule.typeExclude.test(typeVal)) continue;
      for (const chk of widgetRule.checks) {
        if (chk.skipIf && chk.skipIf(lines_)) continue;
        if (!chk.test(lines_)) {
          issues.push({
            line: typeLine.lineNum,
            check: chk.checkName,
            message: chk.message(mod.name),
            severity: 'warning',
            content: `类型：${typeVal}`
          });
        }
      }
    }

    // ── 规则 2.5：**子控件：** 显式声明 → 对每个声明类型运行 WIDGET_TEMPLATE_RULES ──
    const subWidgetLine = lines_.find(l => /^\*\*子控件：\*\*/.test(l.text));
    if (subWidgetLine) {
      const subVal = subWidgetLine.text.replace(/^\*\*子控件：\*\*\s*/, '');
      const subTypes = subVal.split('/').map(s => s.trim()).filter(Boolean);
      for (const subType of subTypes) {
        for (const widgetRule of WIDGET_TEMPLATE_RULES) {
          if (!widgetRule.typeMatch.test(subType)) continue;
          if (widgetRule.typeExclude && widgetRule.typeExclude.test(subType)) continue;
          for (const chk of widgetRule.checks) {
            if (chk.skipIf && chk.skipIf(lines_)) continue;
            if (!chk.test(lines_)) {
              issues.push({
                line: subWidgetLine.lineNum,
                check: `子控件声明-${chk.checkName}`,
                message: `模块 "${mod.name}" 声明了子控件【${subType}】，但模块内缺少「${chk.message(subType).replace(/.*缺少/, '').trim()}」规范`,
                severity: 'warning',
                content: `子控件：${subType}`
              });
            }
          }
        }
      }
    }


    // ── 规则 4b：子内容中识别到需展开的控件 → 必须就地写控件规范 ──
    /**
     * 「子控件简写检测」规则（基于 widget-templates.md v2.0）：
     * 当一个模块的「显示」内容里出现以下控件关键词，
     * 但模块内没有对应的 **类型：** 声明（独立或 ##### 子模块），则报 warning。
     *
     * 排除：弹窗、列表（滚动区）、返回按钮——这三类允许不展开。
     * 气泡/标签/Tips：模板规定在关联控件中描述，不单独列，故不检测。
     * 奖励道具框：模板允许就近描述（不必拆子模块），但交互行必须写。
     *
     * 检测范围：仅扫显示区（1.显示:）内容行，避免交互说明误触发。
     */
    const SUB_WIDGET_RULES = [
      // Part A 常规控件（排除按钮/付费按钮/图标按钮——这三类通常已作为独立 #### 模块）
      {
        name: '页签',
        // 在显示描述中提到「页签」「Tab」时，该模块内必须有 **类型：** 页签
        detect: /页签|Tab\s*组|横向\s*Tab|纵向\s*Tab/,
        verify: /^\*\*类型：\*\*.*(页签|Tab)/i,
      },
      {
        name: '开关',
        detect: /开关(?!控件说明)|Toggle/,
        verify: /^\*\*类型：\*\*.*(开关|Toggle)/i,
      },
      {
        name: '单选框',
        detect: /单选框|Radio/i,
        verify: /^\*\*类型：\*\*.*(单选框|Radio)/i,
      },
      {
        name: '复选框',
        // 「复选框」「checkbox」均可触发；「勾选控件」是自造词不检测
        detect: /复选框|[Cc]heckbox/,
        verify: /^\*\*类型：\*\*.*复选框/,
      },
      {
        name: '输入框',
        // 「输入框」「Textfield」触发；模板说含粘贴/清除按钮时不单独拆子控件，所以验证放宽到模块内有 **类型：** 输入框 即可
        detect: /输入框|[Tt]extfield/,
        verify: /^\*\*类型：\*\*.*输入框/,
      },
      {
        name: '滑动条',
        detect: /滑动条|[Ss]lider/,
        verify: /^\*\*类型：\*\*.*滑动条/,
      },
      // Part B 复合控件
      {
        name: '下拉框',
        detect: /下拉框|[Dd]roplist/,
        verify: /^\*\*类型：\*\*.*下拉框/,
      },
      {
        name: '搜索框',
        // 注意搜索框是独立控件，与输入框区分
        detect: /搜索框|[Ss]earch\s*[Bb]ox/,
        verify: /^\*\*类型：\*\*.*搜索框/,
      },
      // Part C 高复用控件
      {
        name: '奖励道具框',
        // 识别标准来自模板：icon + 背景底板 + 右下角数量 = 奖励道具框
        // 模板允许就近描述，不必拆子模块，但必须写交互「点击 → 打开通用道具说明 tips」
        detect: /奖励\s*icon|道具\s*icon|品级底板|奖励道具框/,
        verify: /^\*\*类型：\*\*.*奖励道具框|点击.{0,10}奖励道具框.{0,20}(tips|Tips|道具说明)|通用\s*Item\s*Tips/i,
      },
      {
        name: '问号按钮',
        detect: /问号\s*按钮|「\?」|「？」|\?\s*帮助按钮/,
        verify: /^\*\*类型：\*\*.*问号按钮/,
      },
      {
        name: '更多操作按钮',
        detect: /「…」|「\.{3}」|更多操作按钮|菜单按钮|「···」/,
        verify: /^\*\*类型：\*\*.*更多操作按钮/,
      },
      {
        name: '货币栏',
        detect: /货币栏|货币\s*图标.{0,10}充值|钻石.{0,10}充值入口/,
        verify: /^\*\*类型：\*\*.*货币栏/,
      },
      {
        name: '模组卡片',
        detect: /模组\s*卡片|[Mm]od\s*[Cc]ard/,
        verify: /^\*\*类型：\*\*.*模组卡片/,
      },
      // 按钮类（之前排除，Option C 重新加入：用紧 regex 只检测明确描述的子按钮，非泛泛提及）
      {
        name: '按钮',
        detect: /「[^」]{1,20}按钮」|(?:含|包含|右侧|左侧|卡片内)[^。\n，]{0,20}按钮(?!控件)/,
        verify: /^\*\*类型：\*\*.*(按钮|button)/i,
      },
      {
        name: '图标按钮',
        detect: /图标按钮/,
        verify: /^\*\*类型：\*\*.*图标按钮/,
      },
    ];

    // 提取「显示」区域的内容行（1. 显示: 之后，2. 交互/下一字段之前）
    const displayLines = (() => {
      let inDisplay = false;
      const result = [];
      for (const l of lines_) {
        if (/^1\.\s*显示/.test(l.text)) { inDisplay = true; continue; }
        if (/^2\./.test(l.text) || /^\*\*/.test(l.text) || /^#####/.test(l.text)) { inDisplay = false; }
        if (inDisplay) result.push(l);
      }
      return result;
    })();

    for (const rule of SUB_WIDGET_RULES) {
      const hitLine = displayLines.find(l => rule.detect.test(l.text));
      if (!hitLine) continue;

      // 合并写法：若 **子控件：** 已声明该控件类型，视为合规（内容已并入父模块字段）
      const declaredInSubwidget = lines_.some(l =>
        /^\*\*子控件：\*\*/.test(l.text) && rule.detect.test(l.text)
      );
      const hasExpanded = lines_.some(l => rule.verify.test(l.text));
      if (!hasExpanded && !declaredInSubwidget) {
        issues.push({
          line: hitLine.lineNum,
          check: '子控件未规范展开',
          message: `模块 "${mod.name}" 的显示内容中识别到【${rule.name}】，请就地补写控件规范（需包含 **类型：** 和 **控件状态：** 字段）`,
          severity: 'warning',
          content: hitLine.text.substring(0, 80)
        });
      }
      // ── Option C：始终对检测到的子控件运行必要字段检查（复用 WIDGET_TEMPLATE_RULES）──
      // 无论是否已写 **类型：**，均检查
      for (const widgetRule of WIDGET_TEMPLATE_RULES) {
        if (!widgetRule.typeMatch.test(rule.name)) continue;
        if (widgetRule.typeExclude && widgetRule.typeExclude.test(rule.name)) continue;
        for (const chk of widgetRule.checks) {
          if (chk.skipIf && chk.skipIf(lines_)) continue;
          if (!chk.test(lines_)) {
            issues.push({
              line: hitLine.lineNum,
              check: `子控件-${chk.checkName}`,
              message: `模块 "${mod.name}" 检测到【${rule.name}】，请就地补写：${chk.message(rule.name)}`,
              severity: 'warning',
              content: hitLine.text.substring(0, 80)
            });
          }
        }
      }
    }

    // ── 规则 4：提到通用弹窗/通用组件 → 必须有通用组件图示占位 ──
    const genericMentionLine = lines_.find(l =>
      /通用.{0,8}弹窗|通用.{0,8}组件|通用.{0,8}说明/.test(l.text) &&
      !l.text.includes('【需要通用组件图示：')
    );
    const hasGenericImage = lines_.some(l => l.text.includes('【需要通用组件图示：'));
    if (genericMentionLine && !hasGenericImage) {
      issues.push({
        line: genericMentionLine.lineNum,
        check: '通用组件图示缺失',
        message: `模块 "${mod.name}" 提到通用弹窗/组件，但缺少 【需要通用组件图示：xxx】 占位`,
        severity: 'warning',
        content: genericMentionLine.text.substring(0, 80)
      });
    }
  }

  return issues;
}

// ── 主函数 ──
function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const issues = [];

  // 文档头检查
  issues.push(...checkHead(lines));

  // 逐行检查
  for (let i = 0; i < lines.length; i++) {
    for (const check of LINE_CHECKS) {
      if (check.test(lines[i])) {
        issues.push({
          line: i + 1,
          check: check.name,
          message: check.message,
          severity: check.severity,
          content: lines[i].substring(0, 80)
        });
      }
    }
  }

  // 结构检查
  issues.push(...checkStructure(lines));

  // 控件规范检查
  issues.push(...checkWidgetRules(lines));

  return issues;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log('用法: node validate.mjs <interaction-spec.md>');
    console.log('\nv1.5 结构规范:');
    console.log('  文档头：  icon/version/title/planner/uxd');
    console.log('  需求范围：## A. 需求范围');
    console.log('  方案说明：## B. 方案说明');
    console.log('  界面块：  ### [N] 名称');
    console.log('  模块：    #### N. 名称');
    console.log('  子模块：  ##### N 名称');
    process.exit(1);
  }

  const filePath = args[0];
  if (!fs.existsSync(filePath)) {
    console.error(`❌ 文件不存在: ${filePath}`);
    process.exit(1);
  }

  console.log(`🔍 检查文件: ${path.basename(filePath)}\n`);

  const issues = checkFile(filePath);

  if (issues.length === 0) {
    console.log('✅ 未发现问题！');
    process.exit(0);
  }

  const errors = issues.filter(i => i.severity === 'error');
  const warnings = issues.filter(i => i.severity === 'warning');

  if (errors.length > 0) {
    console.log(`❌ 发现 ${errors.length} 个错误:\n`);
    for (const issue of errors) {
      console.log(`  第 ${issue.line} 行: [${issue.check}]`);
      console.log(`  ${issue.message}`);
      if (issue.content) console.log(`  内容: ${issue.content}`);
      console.log();
    }
  }

  if (warnings.length > 0) {
    console.log(`⚠️  发现 ${warnings.length} 个警告:\n`);
    for (const issue of warnings) {
      console.log(`  第 ${issue.line} 行: [${issue.check}]`);
      console.log(`  ${issue.message}`);
      if (issue.content) console.log(`  内容: ${issue.content}`);
      console.log();
    }
  }

  console.log(`总计: ${errors.length} 个错误, ${warnings.length} 个警告`);
  process.exit(errors.length > 0 ? 1 : 0);
}

main();