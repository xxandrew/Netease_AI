#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏界面易用性分析器 (UI Usability Analyzer)
============================================
输入游戏截图（可附加按键标注JSON），调用 GPT-4o Vision API
按7个维度输出结构化易用性诊断报告（HTML + JSON）。

用法示例:
    python analyzer.py --image screenshot.png --resolution 1920x1080
    python analyzer.py --image screenshot.png --platform mobile --buttons buttons.json
    python analyzer.py --help
"""

import os
import sys
import json
import base64
import argparse
import math
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# 尝试导入 openai，未安装时给出提示
try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] 请先安装依赖: pip install openai pillow")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("[ERROR] 请先安装依赖: pip install pillow")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────
# 常量：各平台触控标准（单位：dp）
# ──────────────────────────────────────────────────────────────
PLATFORM_STANDARDS = {
    "mobile":  {"min_dp": 44, "gap_ok": 20, "gap_warn": 10},   # Apple HIG / Google Material
    "tablet":  {"min_dp": 32, "gap_ok": 16, "gap_warn": 8},
    "pc":      {"min_dp": 32, "gap_ok": 12, "gap_warn": 6},
}

# 认知负荷：同屏元素数量阈值（米勒定律 7±2）
COGNITIVE_LOAD_OK   = 9
COGNITIVE_LOAD_WARN = 12

# 视野遮挡：单侧 UI 占屏比上限
OCCLUSION_RATIO_OK  = 0.25  # 25%

# 综合评分权重（7个维度）
SCORE_WEIGHTS = {
    "hotzone_size":    0.20,
    "fitts_law":       0.20,
    "gap_risk":        0.15,
    "overlap":         0.15,
    "cognitive_load":  0.15,
    "occlusion":       0.10,
    "thumb_zone":      0.05,
}


# ──────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────
@dataclass
class ButtonInfo:
    """单个按键的标注信息"""
    name:   str
    x:      float   # 左上角 x 坐标（px）
    y:      float   # 左上角 y 坐标（px）
    width:  float   # 宽度（px）
    height: float   # 高度（px）

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass
class DimensionResult:
    """单个分析维度的结果"""
    name:       str
    score:      int               # 0-100
    issues:     list = field(default_factory=list)   # 问题列表
    suggestions: list = field(default_factory=list)  # 优化建议（含开发成本）
    details:    dict = field(default_factory=dict)   # 详细数据


@dataclass
class AnalysisResult:
    """完整分析结果"""
    image_path:   str
    resolution:   tuple
    platform:     str
    timestamp:    str
    dimensions:   list = field(default_factory=list)   # list[DimensionResult]
    total_score:  int  = 0
    report_html:  str  = ""
    data_json:    str  = ""


# ──────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────
def px_to_dp(px: float, dpi_scale: float = 1.0) -> float:
    """
    像素转dp换算。
    1920×1080 截图默认 @1x，即 1px = 1dp。
    如果截图来自 @2x 设备，传入 dpi_scale=2.0。
    """
    return px / dpi_scale


def encode_image_base64(image_path: str) -> str:
    """将本地图片编码为 base64 字符串，用于 Vision API 调用"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime(image_path: str) -> str:
    """根据扩展名返回 MIME 类型"""
    ext = Path(image_path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")


def calc_edge_gap(a: ButtonInfo, b: ButtonInfo) -> float:
    """
    计算两个按键之间的最短边缘间距（px）。
    若存在重叠返回负值。
    """
    # 水平方向间距
    dx = max(0.0, max(a.x, b.x) - min(a.right, b.right))
    # 垂直方向间距
    dy = max(0.0, max(a.y, b.y) - min(a.bottom, b.bottom))
    # 若两轴均有重叠则为负间距（取重叠量的负值）
    overlap_x = min(a.right, b.right) - max(a.x, b.x)
    overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
    if overlap_x > 0 and overlap_y > 0:
        return -min(overlap_x, overlap_y)  # 负值=重叠
    return math.sqrt(dx**2 + dy**2)


def classify_thumb_zone(btn: ButtonInfo, resolution: tuple) -> str:
    """
    判断按键中心落在哪个拇指操作区（竖屏单手操作参考）。
      🟢 舒适区：屏幕下方 1/3
      🟡 可达区：屏幕中间 1/3
      🔴 困难区：屏幕上方 1/3
    """
    _, height = resolution
    cy = btn.center_y
    if cy >= height * 2 / 3:
        return "舒适区"
    elif cy >= height / 3:
        return "可达区"
    else:
        return "困难区"


def status_icon(ok: bool, warn: bool = False) -> str:
    """返回状态图标"""
    if ok:
        return "✅"
    elif warn:
        return "⚠️"
    return "❌"


# ──────────────────────────────────────────────────────────────
# 维度1：热区尺寸核查
# ──────────────────────────────────────────────────────────────
def analyze_hotzone_size(
    buttons: list,
    platform: str,
    dpi_scale: float = 1.0
) -> DimensionResult:
    """
    检测各按键 px 尺寸，换算为 dp，对照平台触控标准。
    移动端 ≥44dp，PC/平板 ≥32dp。
    """
    standard = PLATFORM_STANDARDS.get(platform, PLATFORM_STANDARDS["mobile"])
    min_dp = standard["min_dp"]
    rows = []
    issues = []
    suggestions = []
    fail_count = 0
    warn_count = 0

    for btn in buttons:
        w_dp = px_to_dp(btn.width, dpi_scale)
        h_dp = px_to_dp(btn.height, dpi_scale)
        size_dp = min(w_dp, h_dp)  # 取短边作为有效触控尺寸
        ok = size_dp >= min_dp
        warn = (not ok) and size_dp >= min_dp * 0.7
        icon = status_icon(ok, warn)
        rows.append({
            "name": btn.name,
            "size_px": f"{int(btn.width)}×{int(btn.height)}",
            "size_dp": f"{size_dp:.0f}dp",
            "standard": f"≥{min_dp}dp",
            "status": icon,
        })
        if not ok:
            fail_count += 1
            issues.append(
                f"「{btn.name}」热区 {size_dp:.0f}dp，低于 {min_dp}dp 标准"
            )
            cost = "L（资源替换）" if size_dp >= min_dp * 0.6 else "M（布局重排）"
            suggestions.append(
                f"扩展「{btn.name}」热区至 ≥{min_dp}×{min_dp}dp  |  开发成本：{cost}"
            )
        elif warn:
            warn_count += 1

    total = len(buttons)
    pass_rate = (total - fail_count) / total if total > 0 else 1.0
    score = int(pass_rate * 100) - warn_count * 5
    score = max(0, min(100, score))

    return DimensionResult(
        name="热区尺寸",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"rows": rows, "standard_dp": min_dp},
    )


# ──────────────────────────────────────────────────────────────
# 维度2：费茨定律评估
# ──────────────────────────────────────────────────────────────
def analyze_fitts_law(
    buttons: list,
    resolution: tuple,
    gpt_analysis: dict
) -> DimensionResult:
    """
    评估按键大小与到达距离，判断高频操作是否在拇指热区内。
    GPT 结论作为辅助，标注数据作为主要依据。
    """
    w, h = resolution
    # 拇指热区中心（右下 1/4 区域中心）
    thumb_cx = w * 0.82
    thumb_cy = h * 0.80

    issues = []
    suggestions = []
    fitts_rows = []

    for btn in buttons:
        dist = math.sqrt(
            (btn.center_x - thumb_cx) ** 2 +
            (btn.center_y - thumb_cy) ** 2
        )
        size = min(btn.width, btn.height)
        # 费茨指数 ID = log2(2D/W)，越小操作越容易
        fitts_id = math.log2(2 * dist / size) if size > 0 else 99
        fitts_rows.append({
            "name": btn.name,
            "center": f"({btn.center_x:.0f}, {btn.center_y:.0f})",
            "dist_to_thumb": f"{dist:.0f}px",
            "fitts_id": f"{fitts_id:.2f}",
        })
        if dist > w * 0.5:
            issues.append(
                f"「{btn.name}」距拇指热区 {dist:.0f}px，操作成本较高（ID={fitts_id:.2f}）"
            )
            suggestions.append(
                f"考虑将「{btn.name}」迁移至屏幕右下区域  |  开发成本：M（布局重排）"
            )

    # 融合 GPT 定性分析
    gpt_fitts = gpt_analysis.get("fitts_law", {})
    gpt_issues = gpt_fitts.get("issues", [])
    gpt_suggs  = gpt_fitts.get("suggestions", [])
    issues     += [f"[AI] {i}" for i in gpt_issues]
    suggestions += [f"[AI] {s}" for s in gpt_suggs]

    score = max(0, 100 - len(issues) * 12)
    return DimensionResult(
        name="费茨定律",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"fitts_rows": fitts_rows, "thumb_center": (thumb_cx, thumb_cy)},
    )


# ──────────────────────────────────────────────────────────────
# 维度3：热区间距风险
# ──────────────────────────────────────────────────────────────
def analyze_gap_risk(buttons: list, platform: str) -> DimensionResult:
    """
    检测相邻按键边缘间距（px），防止误触。
    建议 ≥20px（移动端），警告 10–19px，危险 <10px。
    """
    standard = PLATFORM_STANDARDS.get(platform, PLATFORM_STANDARDS["mobile"])
    gap_ok   = standard["gap_ok"]
    gap_warn = standard["gap_warn"]

    issues = []
    suggestions = []
    gap_rows = []
    danger_count = 0

    for i in range(len(buttons)):
        for j in range(i + 1, len(buttons)):
            a, b = buttons[i], buttons[j]
            gap = calc_edge_gap(a, b)
            if gap < 0:
                continue  # 重叠由维度4处理
            ok   = gap >= gap_ok
            warn = (not ok) and gap >= gap_warn
            icon = status_icon(ok, warn)
            gap_rows.append({
                "pair": f"{a.name} ↔ {b.name}",
                "gap_px": f"{gap:.0f}px",
                "status": icon,
            })
            if not ok:
                danger_count += 1
                issues.append(
                    f"「{a.name}」↔「{b.name}」间距 {gap:.0f}px，存在误触风险"
                )
                suggestions.append(
                    f"将「{a.name}」与「{b.name}」间距扩展至 ≥{gap_ok}px"
                    f"  |  开发成本：L（布局调整）"
                )

    score = max(0, 100 - danger_count * 15)
    return DimensionResult(
        name="热区间距",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"gap_rows": gap_rows, "standard_gap": gap_ok},
    )


# ──────────────────────────────────────────────────────────────
# 维度4：热区重叠检测
# ──────────────────────────────────────────────────────────────
def analyze_overlap(buttons: list, gpt_analysis: dict) -> DimensionResult:
    """
    检测负间距/按键边界相交。
    负间距为功能性 Bug 级别（P0）问题。
    """
    issues = []
    suggestions = []
    overlap_rows = []

    for i in range(len(buttons)):
        for j in range(i + 1, len(buttons)):
            a, b = buttons[i], buttons[j]
            gap = calc_edge_gap(a, b)
            if gap < 0:
                depth = abs(gap)
                overlap_rows.append({
                    "pair": f"{a.name} ↔ {b.name}",
                    "overlap_px": f"{depth:.0f}px",
                    "severity": "🔴 P0 功能性Bug",
                })
                issues.append(
                    f"[P0] 「{a.name}」与「{b.name}」存在 {depth:.0f}px 重叠（功能性 Bug）"
                )
                suggestions.append(
                    f"修复「{a.name}」与「{b.name}」坐标，消除重叠"
                    f"  |  开发成本：L（坐标调整）"
                )

    # 融合 GPT 补充发现
    gpt_overlap = gpt_analysis.get("overlap", {})
    for issue in gpt_overlap.get("issues", []):
        issues.append(f"[AI-P0] {issue}")
    for sugg in gpt_overlap.get("suggestions", []):
        suggestions.append(f"[AI] {sugg}  |  开发成本：L（坐标调整）")

    score = 100 if not issues else max(0, 100 - len(issues) * 25)
    return DimensionResult(
        name="热区重叠",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"overlap_rows": overlap_rows},
    )


# ──────────────────────────────────────────────────────────────
# 维度5：认知负荷评估（主要依赖 GPT 分析）
# ──────────────────────────────────────────────────────────────
def analyze_cognitive_load(gpt_analysis: dict) -> DimensionResult:
    """
    评估同屏元素数量、图标辨识度、视觉层级。
    主要依赖 GPT-4o Vision 的定性分析。
    """
    cog = gpt_analysis.get("cognitive_load", {})
    element_count = cog.get("element_count", -1)
    issues = list(cog.get("issues", []))
    suggestions = []

    for sugg in cog.get("suggestions", []):
        cost = "M（交互优化）"
        if "精简" in sugg or "删除" in sugg:
            cost = "H（交互重构）"
        elif "图标" in sugg or "颜色" in sugg:
            cost = "L（资源替换）"
        suggestions.append(f"{sugg}  |  开发成本：{cost}")

    # 根据元素数量给出基础评分
    if element_count < 0:
        score = cog.get("score", 70)
    elif element_count <= COGNITIVE_LOAD_OK:
        score = 95
    elif element_count <= COGNITIVE_LOAD_WARN:
        score = 75
    else:
        score = max(40, 100 - (element_count - COGNITIVE_LOAD_WARN) * 5)

    return DimensionResult(
        name="认知负荷",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"element_count": element_count},
    )


# ──────────────────────────────────────────────────────────────
# 维度6：视野遮挡分析（主要依赖 GPT 分析）
# ──────────────────────────────────────────────────────────────
def analyze_occlusion(gpt_analysis: dict, buttons: list, resolution: tuple) -> DimensionResult:
    """
    评估按键组占屏比与透明度策略。
    若有标注数据则计算实际占屏比；否则依赖 GPT 结论。
    """
    w, h = resolution
    screen_area = w * h
    issues = []
    suggestions = []
    ui_ratio = None

    if buttons:
        # 计算所有按键总覆盖面积（不去重叠区域，简化计算）
        total_ui_area = sum(b.width * b.height for b in buttons)
        ui_ratio = total_ui_area / screen_area
        if ui_ratio > OCCLUSION_RATIO_OK:
            issues.append(
                f"UI 元素总占屏比 {ui_ratio*100:.1f}%，超过建议上限 {OCCLUSION_RATIO_OK*100:.0f}%"
            )
            suggestions.append(
                "考虑收起/隐藏低频 UI 元素，战斗过程中降低遮挡比例"
                "  |  开发成本：M（交互逻辑）"
            )

    # 融合 GPT 分析
    occ = gpt_analysis.get("occlusion", {})
    issues += [i for i in occ.get("issues", [])]
    for sugg in occ.get("suggestions", []):
        suggestions.append(f"{sugg}  |  开发成本：M（动画逻辑）")

    score = occ.get("score", 80) if not issues else max(50, occ.get("score", 70))
    return DimensionResult(
        name="视野遮挡",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={"ui_ratio": f"{ui_ratio*100:.1f}%" if ui_ratio else "N/A（无标注数据）"},
    )


# ──────────────────────────────────────────────────────────────
# 维度7：拇指热区分布
# ──────────────────────────────────────────────────────────────
def analyze_thumb_zone(buttons: list, resolution: tuple, gpt_analysis: dict) -> DimensionResult:
    """
    判断各按键落在舒适区 / 可达区 / 困难区。
    高频操作应 ≥80% 落在舒适区/可达区。
    """
    issues = []
    suggestions = []
    zone_rows = []
    comfort_count = 0
    difficult_count = 0

    for btn in buttons:
        zone = classify_thumb_zone(btn, resolution)
        zone_rows.append({"name": btn.name, "zone": zone})
        if zone == "舒适区":
            comfort_count += 1
        elif zone == "困难区":
            difficult_count += 1
            issues.append(f"「{btn.name}」位于困难区（屏幕上方），若为高频操作建议迁移")
            suggestions.append(
                f"将「{btn.name}」迁移至可达区或舒适区  |  开发成本：M（布局重排）"
            )

    # 融合 GPT 定性分析
    thumb = gpt_analysis.get("thumb_zone", {})
    issues += [f"[AI] {i}" for i in thumb.get("issues", [])]

    total = len(buttons)
    easy_rate = (comfort_count + (total - difficult_count - comfort_count)) / total if total > 0 else 1
    score = int(easy_rate * 100)
    score = max(0, min(100, score))

    return DimensionResult(
        name="拇指热区分布",
        score=score,
        issues=issues,
        suggestions=suggestions,
        details={
            "zone_rows": zone_rows,
            "comfort_count": comfort_count,
            "difficult_count": difficult_count,
        },
    )


# ──────────────────────────────────────────────────────────────
# GPT-4o Vision 调用
# ──────────────────────────────────────────────────────────────
def call_gpt_vision(image_path: str, platform: str, api_key: str) -> dict:
    """
    调用 GPT-4o Vision API，获取截图的定性易用性分析。
    返回结构化 JSON，包含7个维度的 issues / suggestions。
    """
    client = OpenAI(api_key=api_key)
    b64 = encode_image_base64(image_path)
    mime = get_image_mime(image_path)

    # 构造分析提示词
    prompt = f"""你是一位专业的游戏 UI 易用性分析师。请分析这张游戏界面截图，
平台类型：{platform}（mobile=移动端，tablet=平板，pc=电脑）。

请从以下7个维度进行分析，**必须以 JSON 格式返回**，不要添加任何额外说明：

{{
  "fitts_law": {{
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1（不含开发成本，脚本会自动添加）"]
  }},
  "overlap": {{
    "issues": ["重叠/遮挡问题"],
    "suggestions": ["修复建议"]
  }},
  "cognitive_load": {{
    "element_count": 估算的同屏UI元素数量（整数）,
    "score": 认知负荷评分0-100（元素少/层级清晰=高分）,
    "issues": ["认知负荷问题"],
    "suggestions": ["优化建议"]
  }},
  "occlusion": {{
    "score": 视野遮挡评分0-100（遮挡少=高分）,
    "issues": ["遮挡问题"],
    "suggestions": ["优化建议"]
  }},
  "thumb_zone": {{
    "issues": ["拇指操作区问题"],
    "suggestions": ["优化建议"]
  }},
  "overall_summary": "一段话的整体评价（100字以内）"
}}

分析要求：
1. 每条 issue 必须具体描述问题位置和现象
2. 每条 suggestion 说明优化方向（不需要写开发成本）
3. element_count 统计所有可见的独立 UI 元素（按钮/图标/文字标签等）
4. 如果某个维度没有问题，对应 issues 返回空数组
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=2000,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # 提取 JSON（去掉可能存在的 markdown 代码块标记）
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"[WARN] GPT 返回非标准 JSON，使用空白结果。原始内容：\n{raw[:300]}")
        return {}


# ──────────────────────────────────────────────────────────────
# HTML 报告生成器
# ──────────────────────────────────────────────────────────────
def generate_html_report(result: AnalysisResult, gpt_raw: dict) -> str:
    """
    根据 AnalysisResult 生成完整 HTML 报告。
    包含：综合评分、各维度详情、问题列表、优化建议。
    """
    image_name = Path(result.image_path).name
    overall_summary = gpt_raw.get("overall_summary", "（无 GPT 整体评价）")
    w, h = result.resolution

    # 评分颜色
    def score_color(s):
        if s >= 80: return "#27ae60"
        if s >= 60: return "#f39c12"
        return "#e74c3c"

    # 构建维度卡片
    dimension_cards = ""
    for dim in result.dimensions:
        issues_html = "".join(
            f'<li class="issue">⚠ {i}</li>' for i in dim.issues
        ) or '<li class="ok">✅ 无发现问题</li>'
        suggs_html = "".join(
            f'<li class="sugg">→ {s}</li>' for s in dim.suggestions
        ) or '<li class="sugg-empty">暂无优化建议</li>'

        # 维度专属详情表格
        detail_table = ""
        if dim.name == "热区尺寸" and dim.details.get("rows"):
            rows = dim.details["rows"]
            detail_table = """<table class="detail-table">
<tr><th>按键</th><th>尺寸(px)</th><th>尺寸(dp)</th><th>标准</th><th>状态</th></tr>
""" + "".join(
                f'<tr><td>{r["name"]}</td><td>{r["size_px"]}</td>'
                f'<td>{r["size_dp"]}</td><td>{r["standard"]}</td>'
                f'<td>{r["status"]}</td></tr>'
                for r in rows
            ) + "</table>"

        elif dim.name == "热区间距" and dim.details.get("gap_rows"):
            rows = dim.details["gap_rows"]
            detail_table = """<table class="detail-table">
<tr><th>按键对</th><th>间距(px)</th><th>状态</th></tr>
""" + "".join(
                f'<tr><td>{r["pair"]}</td><td>{r["gap_px"]}</td><td>{r["status"]}</td></tr>'
                for r in rows
            ) + "</table>"

        elif dim.name == "热区重叠" and dim.details.get("overlap_rows"):
            rows = dim.details["overlap_rows"]
            detail_table = """<table class="detail-table">
<tr><th>按键对</th><th>重叠深度(px)</th><th>严重程度</th></tr>
""" + "".join(
                f'<tr><td>{r["pair"]}</td><td>{r["overlap_px"]}</td><td>{r["severity"]}</td></tr>'
                for r in rows
            ) + "</table>"

        elif dim.name == "拇指热区分布" and dim.details.get("zone_rows"):
            rows = dim.details["zone_rows"]
            zone_icon = {"舒适区": "🟢", "可达区": "🟡", "困难区": "🔴"}
            detail_table = """<table class="detail-table">
<tr><th>按键</th><th>热区分类</th></tr>
""" + "".join(
                f'<tr><td>{r["name"]}</td>'
                f'<td>{zone_icon.get(r["zone"], "")} {r["zone"]}</td></tr>'
                for r in rows
            ) + "</table>"

        sc = dim.score
        dimension_cards += f"""
<div class="dim-card">
  <div class="dim-header">
    <span class="dim-name">{dim.name}</span>
    <span class="dim-score" style="color:{score_color(sc)}">{sc} 分</span>
  </div>
  {detail_table}
  <div class="issues-section">
    <strong>发现问题：</strong>
    <ul>{issues_html}</ul>
  </div>
  <div class="sugg-section">
    <strong>优化建议：</strong>
    <ul>{suggs_html}</ul>
  </div>
</div>
"""

    # 评分雷达数据（用 emoji 进度条近似）
    score_bars = ""
    for dim in result.dimensions:
        fill = int(dim.score / 10)
        bar = "█" * fill + "░" * (10 - fill)
        score_bars += (
            f'<div class="score-row">'
            f'<span class="score-label">{dim.name}</span>'
            f'<span class="score-bar" style="color:{score_color(dim.score)}">{bar}</span>'
            f'<span class="score-num">{dim.score}</span>'
            f'</div>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>界面易用性分析报告 — {image_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "PingFang SC","Microsoft YaHei",sans-serif; background:#f5f6fa; color:#2d3436; }}
  .header {{ background: linear-gradient(135deg,#2d3436,#636e72); color:#fff; padding:32px 40px; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .meta {{ font-size:13px; opacity:.8; }}
  .container {{ max-width:1080px; margin:0 auto; padding:32px 20px; }}
  .summary-box {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:24px;
                  box-shadow:0 2px 8px rgba(0,0,0,.06); }}
  .total-score {{ font-size:64px; font-weight:bold; text-align:center; padding:16px 0; }}
  .score-label-main {{ text-align:center; color:#636e72; margin-bottom:20px; font-size:14px; }}
  .score-row {{ display:flex; align-items:center; margin:6px 0; font-size:13px; }}
  .score-label {{ width:120px; color:#636e72; }}
  .score-bar {{ font-family:monospace; letter-spacing:1px; flex:1; }}
  .score-num {{ width:40px; text-align:right; font-weight:bold; }}
  .overall-summary {{ background:#f0f8ff; border-left:4px solid #74b9ff;
                       padding:12px 16px; border-radius:4px; font-size:14px; margin-top:16px; }}
  .dim-card {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:20px;
               box-shadow:0 2px 8px rgba(0,0,0,.06); }}
  .dim-header {{ display:flex; justify-content:space-between; align-items:center;
                 margin-bottom:14px; border-bottom:1px solid #f0f0f0; padding-bottom:10px; }}
  .dim-name {{ font-size:18px; font-weight:bold; }}
  .dim-score {{ font-size:28px; font-weight:bold; }}
  .detail-table {{ width:100%; border-collapse:collapse; font-size:13px; margin:12px 0; }}
  .detail-table th {{ background:#f8f9fa; padding:8px 12px; text-align:left;
                      border:1px solid #e9ecef; font-weight:600; }}
  .detail-table td {{ padding:8px 12px; border:1px solid #e9ecef; }}
  .detail-table tr:nth-child(even) td {{ background:#fafafa; }}
  .issues-section, .sugg-section {{ margin-top:12px; }}
  .issues-section ul, .sugg-section ul {{ list-style:none; margin-top:6px; }}
  li.issue  {{ padding:4px 0; color:#e17055; font-size:13px; }}
  li.ok     {{ padding:4px 0; color:#00b894; font-size:13px; }}
  li.sugg   {{ padding:4px 0; color:#2980b9; font-size:13px; }}
  li.sugg-empty {{ padding:4px 0; color:#b2bec3; font-size:13px; }}
  .footer   {{ text-align:center; color:#b2bec3; font-size:12px; padding:24px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🕹️ 游戏界面易用性分析报告</h1>
  <div class="meta">
    文件：{image_name} &nbsp;|&nbsp;
    分辨率：{w}×{h} &nbsp;|&nbsp;
    平台：{result.platform} &nbsp;|&nbsp;
    分析时间：{result.timestamp}
  </div>
</div>

<div class="container">

  <!-- 综合评分 -->
  <div class="summary-box">
    <div class="total-score" style="color:{score_color(result.total_score)}">{result.total_score}</div>
    <div class="score-label-main">综合易用性得分（满分 100）</div>
    {score_bars}
    <div class="overall-summary">📝 AI 整体评价：{overall_summary}</div>
  </div>

  <!-- 各维度详情 -->
  {dimension_cards}

</div>
<div class="footer">由 UIUsabilityAnalyzer 自动生成 | 理论依据：Fitts's Law · ISO 9241-9 · Cognitive Load Theory · Steven Hoober 单手操作研究</div>
</body>
</html>"""
    return html


# ──────────────────────────────────────────────────────────────
# 主分析类
# ──────────────────────────────────────────────────────────────
class UIUsabilityAnalyzer:
    """
    游戏界面易用性分析器主类。
    支持截图输入 + 可选按键标注数据，输出 HTML 报告 + JSON 数据。
    """

    def __init__(
        self,
        image_path:  str,
        resolution:  tuple          = (1920, 1080),
        platform:    str            = "mobile",
        button_data: Optional[list] = None,
        output_dir:  str            = "./reports",
        api_key:     Optional[str]  = None,
        dpi_scale:   float          = 1.0,
    ):
        """
        参数：
          image_path  : 截图本地路径
          resolution  : 屏幕分辨率元组，默认 (1920, 1080)
          platform    : 平台类型 "mobile" | "tablet" | "pc"
          button_data : 按键标注数据列表（JSON格式），含 name/x/y/width/height
          output_dir  : 报告输出目录
          api_key     : OpenAI API Key（优先从环境变量 OPENAI_API_KEY 读取）
          dpi_scale   : DPI 缩放系数，@1x=1.0，@2x=2.0
        """
        self.image_path  = image_path
        self.resolution  = resolution
        self.platform    = platform
        self.output_dir  = output_dir
        self.dpi_scale   = dpi_scale

        # API Key 优先读取环境变量
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "未找到 OpenAI API Key！\n"
                "请设置环境变量 OPENAI_API_KEY 或通过 --api_key 参数传入。"
            )

        # 解析按键标注数据
        self.buttons: list = []
        if button_data:
            for b in button_data:
                self.buttons.append(ButtonInfo(
                    name=b["name"],
                    x=float(b["x"]),
                    y=float(b["y"]),
                    width=float(b["width"]),
                    height=float(b["height"]),
                ))

        # 校验图片是否存在
        if not Path(image_path).exists():
            raise FileNotFoundError(f"截图文件不存在：{image_path}")

    def run(self) -> AnalysisResult:
        """执行完整分析流程，返回 AnalysisResult"""
        print(f"[INFO] 开始分析：{self.image_path}")
        print(f"[INFO] 平台：{self.platform}，分辨率：{self.resolution}，按键数：{len(self.buttons)}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Step 1：调用 GPT-4o Vision 获取定性分析
        print("[INFO] 正在调用 GPT-4o Vision API...")
        gpt_raw = call_gpt_vision(self.image_path, self.platform, self.api_key)
        print("[INFO] GPT 分析完成")

        # Step 2：逐维度分析
        dims = []

        # 维度1：热区尺寸（需要标注数据）
        if self.buttons:
            dims.append(analyze_hotzone_size(self.buttons, self.platform, self.dpi_scale))
        else:
            dims.append(DimensionResult(
                name="热区尺寸",
                score=70,
                issues=["未提供按键标注数据，无法精确计算 dp 尺寸"],
                suggestions=["提供 --buttons 标注 JSON 以获得精确热区评估"],
                details={"note": "依赖标注数据"},
            ))

        # 维度2：费茨定律
        dims.append(analyze_fitts_law(self.buttons, self.resolution, gpt_raw))

        # 维度3：热区间距
        if len(self.buttons) >= 2:
            dims.append(analyze_gap_risk(self.buttons, self.platform))
        else:
            dims.append(DimensionResult(
                name="热区间距",
                score=70,
                issues=["未提供足够的按键标注数据，无法计算间距"],
                suggestions=["提供 --buttons 标注 JSON 以获得精确间距评估"],
                details={},
            ))

        # 维度4：热区重叠
        dims.append(analyze_overlap(self.buttons, gpt_raw))

        # 维度5：认知负荷
        dims.append(analyze_cognitive_load(gpt_raw))

        # 维度6：视野遮挡
        dims.append(analyze_occlusion(gpt_raw, self.buttons, self.resolution))

        # 维度7：拇指热区分布
        dims.append(analyze_thumb_zone(self.buttons, self.resolution, gpt_raw))

        # Step 3：加权综合评分
        dim_map = {
            "热区尺寸":    "hotzone_size",
            "费茨定律":    "fitts_law",
            "热区间距":    "gap_risk",
            "热区重叠":    "overlap",
            "认知负荷":    "cognitive_load",
            "视野遮挡":    "occlusion",
            "拇指热区分布": "thumb_zone",
        }
        total = 0.0
        for dim in dims:
            key = dim_map.get(dim.name, "")
            weight = SCORE_WEIGHTS.get(key, 1 / len(dims))
            total += dim.score * weight
        total_score = int(total)

        result = AnalysisResult(
            image_path=self.image_path,
            resolution=self.resolution,
            platform=self.platform,
            timestamp=timestamp,
            dimensions=dims,
            total_score=total_score,
        )

        # Step 4：生成报告文件
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        base_name = Path(self.image_path).stem
        date_str  = datetime.now().strftime("%Y%m%d_%H%M%S")

        # HTML 报告
        html_path = str(Path(self.output_dir) / f"usability_report_{base_name}_{date_str}.html")
        html_content = generate_html_report(result, gpt_raw)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        result.report_html = html_path
        print(f"[INFO] HTML 报告已生成：{html_path}")

        # JSON 数据
        json_path = str(Path(self.output_dir) / f"usability_data_{base_name}_{date_str}.json")
        json_data = {
            "image_path":  result.image_path,
            "resolution":  list(result.resolution),
            "platform":    result.platform,
            "timestamp":   result.timestamp,
            "total_score": result.total_score,
            "dimensions": [
                {
                    "name":        d.name,
                    "score":       d.score,
                    "issues":      d.issues,
                    "suggestions": d.suggestions,
                    "details":     d.details,
                }
                for d in dims
            ],
            "gpt_raw": gpt_raw,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        result.data_json = json_path
        print(f"[INFO] JSON 数据已生成：{json_path}")
        print(f"[INFO] 综合易用性得分：{total_score} / 100")

        return result


# ──────────────────────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────────────────────
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="🕹️  游戏界面易用性分析器 — UIUsabilityAnalyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 仅截图，使用默认参数
  python analyzer.py --image screenshot.png

  # 指定分辨率和平台
  python analyzer.py --image screenshot.png --resolution 1920x1080 --platform mobile

  # 传入按键标注数据（JSON 文件）
  python analyzer.py --image screenshot.png --buttons buttons.json --output ./my_reports

按键标注 JSON 格式示例：
  [
    {"name": "技能1",  "x": 1720, "y": 900, "width": 88, "height": 88},
    {"name": "普通攻击","x": 1820, "y": 980, "width": 96, "height": 96}
  ]

环境变量：
  OPENAI_API_KEY  — OpenAI API Key（必须设置，或通过 --api_key 参数传入）
        """,
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="游戏界面截图路径（支持 jpg/png/webp）",
    )
    parser.add_argument(
        "--resolution", "-r",
        default="1920x1080",
        help="截图分辨率，格式为 WIDTHxHEIGHT，默认 1920x1080",
    )
    parser.add_argument(
        "--platform", "-p",
        choices=["mobile", "tablet", "pc"],
        default="mobile",
        help="平台类型（影响 dp 标准），默认 mobile",
    )
    parser.add_argument(
        "--buttons", "-b",
        default=None,
        help="按键标注数据 JSON 文件路径（可选）",
    )
    parser.add_argument(
        "--output", "-o",
        default="./reports",
        help="报告输出目录，默认 ./reports",
    )
    parser.add_argument(
        "--dpi_scale",
        type=float,
        default=1.0,
        help="DPI 缩放系数：@1x=1.0（默认），@2x=2.0",
    )
    parser.add_argument(
        "--api_key",
        default=None,
        help="OpenAI API Key（优先级低于环境变量 OPENAI_API_KEY）",
    )
    return parser.parse_args()


def main():
    """命令行主入口"""
    args = parse_args()

    # 解析分辨率
    try:
        w_str, h_str = args.resolution.lower().split("x")
        resolution = (int(w_str), int(h_str))
    except ValueError:
        print(f"[ERROR] 分辨率格式错误：{args.resolution}，请使用 WIDTHxHEIGHT 格式，如 1920x1080")
        sys.exit(1)

    # 加载按键标注数据
    button_data = None
    if args.buttons:
        try:
            with open(args.buttons, "r", encoding="utf-8") as f:
                button_data = json.load(f)
            print(f"[INFO] 已加载按键标注数据：{len(button_data)} 个按键")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[ERROR] 无法读取按键标注 JSON：{e}")
            sys.exit(1)

    # 执行分析
    try:
        analyzer = UIUsabilityAnalyzer(
            image_path=args.image,
            resolution=resolution,
            platform=args.platform,
            button_data=button_data,
            output_dir=args.output,
            api_key=args.api_key,
            dpi_scale=args.dpi_scale,
        )
        result = analyzer.run()
        print("\n" + "=" * 60)
        print(f"  分析完成！综合易用性得分：{result.total_score} / 100")
        print(f"  HTML 报告：{result.report_html}")
        print(f"  JSON 数据：{result.data_json}")
        print("=" * 60)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
