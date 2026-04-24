"""
从交互规范 HTML 中提取内嵌 base64 截图，
逐界面调用 ui_usability_analyzer 生成易用性报告。

用法：
    python extract_and_analyze.py
    python extract_and_analyze.py --html "路径/to/file.html"
    python extract_and_analyze.py --iface 1 3 5   # 只分析指定界面编号
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("缺少依赖，正在安装 beautifulsoup4 ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
    from bs4 import BeautifulSoup

# ── 路径配置 ──────────────────────────────────────────────────
DEFAULT_HTML = r"C:\Users\xxn4472\Documents\我的POPO\interaction-spec-standalone.html"
SCRIPT_DIR   = Path(__file__).parent
TMP_DIR      = SCRIPT_DIR / "tmp_images"
REPORT_DIR   = SCRIPT_DIR / "reports"
ANALYZER     = SCRIPT_DIR / "analyzer.py"

TMP_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


def parse_args():
    p = argparse.ArgumentParser(description="从交互规范 HTML 批量分析易用性")
    p.add_argument("--html", default=DEFAULT_HTML, help="HTML 文件路径")
    p.add_argument("--platform", default="mobile", choices=["mobile","tablet","pc"])
    p.add_argument("--resolution", default="1920x1080", help="分辨率 WxH")
    p.add_argument("--iface", nargs="*", type=int, help="只处理指定界面编号（不填则处理全部）")
    p.add_argument("--dpi_scale", default="1.0", help="DPI 缩放")
    return p.parse_args()


def extract_interfaces(html_path: str) -> list[dict]:
    """
    解析 HTML，返回界面信息列表，每项：
    {
        "id": 1,
        "name": "主页入口",
        "screenshot_b64": "...",  # base64 字符串（无前缀）
        "widgets": [
            {"name": "活动入口图标", "type": "图标按钮", "has_hotzone": True}
        ]
    }
    """
    print(f"📖 正在解析 HTML: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    interfaces = []

    for block in soup.select("div.iface-block"):
        block_id = block.get("id", "")
        # 只取顶层界面，跳过子模块（iface-1 而非 iface-1-m1）
        m = re.match(r"iface-(\d+)$", block_id)
        if not m:
            continue
        iface_num = int(m.group(1))

        # 界面名
        label_el = block.select_one("span.iface-label-name")
        iface_name = label_el.get_text(strip=True) if label_el else f"界面{iface_num}"

        # 截图（只取第一张，iface-screenshot 里的 img）
        screenshot_b64 = None
        img_el = block.select_one("div.iface-screenshot img")
        if img_el and img_el.get("src", "").startswith("data:image"):
            src = img_el["src"]
            # 去掉 data:image/xxx;base64, 前缀
            b64_data = re.sub(r"^data:image/[^;]+;base64,", "", src)
            screenshot_b64 = b64_data

        # 控件列表
        widgets = []
        for wb in block.select("div.widget-block"):
            w_name_el = wb.select_one("span.module-header-title")
            w_type_el = wb.select_one("div.widget-type")
            hotzone_el = wb.select_one("span.state-tag-hotzone")
            widgets.append({
                "name":        w_name_el.get_text(strip=True) if w_name_el else "未知控件",
                "type":        w_type_el.get_text(strip=True) if w_type_el else "",
                "has_hotzone": hotzone_el is not None,
                "hotzone_txt": hotzone_el.get_text(strip=True) if hotzone_el else "",
            })

        interfaces.append({
            "id":              iface_num,
            "name":            iface_name,
            "screenshot_b64":  screenshot_b64,
            "widgets":         widgets,
        })

    interfaces.sort(key=lambda x: x["id"])
    print(f"✅ 共解析到 {len(interfaces)} 个界面")
    return interfaces


def save_screenshot(iface: dict) -> str | None:
    """把 base64 截图写成 PNG 文件，返回路径"""
    if not iface["screenshot_b64"]:
        return None
    path = TMP_DIR / f"iface_{iface['id']:02d}_{iface['name'][:10]}.png"
    try:
        img_bytes = base64.b64decode(iface["screenshot_b64"])
        path.write_bytes(img_bytes)
        return str(path)
    except Exception as e:
        print(f"  ⚠️ 截图解码失败: {e}")
        return None


def build_buttons_json(iface: dict, img_path: str) -> str | None:
    """
    根据控件列表生成 buttons.json（坐标为估算值，无精确标注时用均匀分布）
    """
    widgets = iface["widgets"]
    if not widgets:
        return None

    buttons = []
    # 估算：假设分辨率 1920x1080，按钮均匀分布在屏幕右下区域
    count = len(widgets)
    for i, w in enumerate(widgets):
        if not w["has_hotzone"]:
            continue
        # 简单估算布局（实际项目应从 Figma/标注系统获取精确坐标）
        x = 1600 + (i % 3) * 100
        y = 800  + (i // 3) * 100
        size = 80  # 默认热区尺寸
        buttons.append({
            "name":   w["name"],
            "x":      x,
            "y":      y,
            "width":  size,
            "height": size,
        })

    if not buttons:
        return None

    btn_path = TMP_DIR / f"buttons_iface_{iface['id']:02d}.json"
    btn_path.write_text(json.dumps(buttons, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(btn_path)


def run_analyzer(img_path: str, btn_path: str | None,
                 platform: str, resolution: str,
                 dpi_scale: str) -> tuple[bool, str]:
    """调用 analyzer.py，返回 (成功, 输出信息)"""
    cmd = [
        sys.executable, str(ANALYZER),
        "--image",      img_path,
        "--platform",   platform,
        "--resolution", resolution,
        "--dpi_scale",  dpi_scale,
        "--output",     str(REPORT_DIR),
    ]
    if btn_path:
        cmd += ["--buttons", btn_path]

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("  ⚠️ 未检测到 OPENAI_API_KEY，GPT 分析将跳过（仅输出基于标注数据的报告）")
        # analyzer 内部判断无 key 时应该 fallback，这里强行传空让它走 fallback
    else:
        cmd += ["--api_key", api_key]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if result.returncode == 0:
        return True, result.stdout
    else:
        return False, result.stderr or result.stdout


def generate_summary_report(interfaces: list[dict], results: list[dict]) -> str:
    """生成汇总 HTML 报告"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_DIR / f"usability_report_限时征兆挑战赛_汇总_{ts}.html"

    rows_html = ""
    for r in results:
        status = "✅ 成功" if r["success"] else "❌ 失败"
        report_link = (f'<a href="{Path(r["report"]).name}" '
                       f'style="color:#4a9eff">{Path(r["report"]).name}</a>'
                       if r.get("report") else "—")
        rows_html += f"""
        <tr>
          <td>{r["id"]}</td>
          <td>{r["name"]}</td>
          <td style="color:{'#48C75F' if r['success'] else '#ff5555'}">{status}</td>
          <td>{r.get('widget_count', 0)} 个控件</td>
          <td>{report_link}</td>
        </tr>"""

    success_count = sum(1 for r in results if r["success"])
    total = len(results)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>限时征兆挑战赛 — 易用性分析汇总</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Microsoft YaHei", sans-serif; background: #111114; color: #c8c8cc; padding: 40px; }}
h1 {{ font-size: 24px; color: #fff; margin-bottom: 8px; }}
.sub {{ color: #555; font-size: 14px; margin-bottom: 32px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #1c1c24; color: #888; font-size: 13px; padding: 10px 14px;
     text-align: left; border-bottom: 1px solid #2a2a36; }}
td {{ padding: 10px 14px; border-bottom: 1px solid #1e1e26; font-size: 14px; color: #bbb; }}
tr:hover td {{ background: #16161e; }}
.stat {{ display:inline-block; background:#1c1c24; border:1px solid #2a2a36;
         border-radius:6px; padding:12px 24px; margin-right:12px; margin-bottom:24px; }}
.stat-num {{ font-size:28px; font-weight:700; color:#fff; }}
.stat-label {{ font-size:13px; color:#555; margin-top:2px; }}
</style>
</head>
<body>
<h1>🎮 限时征兆挑战赛 — 交互规范易用性分析汇总</h1>
<div class="sub">生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} &nbsp;|&nbsp; 分析工具：UIUsabilityAnalyzer</div>

<div>
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">界面总数</div></div>
  <div class="stat"><div class="stat-num" style="color:#48C75F">{success_count}</div><div class="stat-label">分析成功</div></div>
  <div class="stat"><div class="stat-num" style="color:#ff5555">{total - success_count}</div><div class="stat-label">分析失败/跳过</div></div>
</div>

<table>
  <thead>
    <tr>
      <th>#</th><th>界面名称</th><th>状态</th><th>控件数</th><th>报告链接</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<p style="margin-top:32px;color:#555;font-size:13px">
  点击报告链接在同目录下用浏览器打开对应界面的详细易用性报告。<br>
  如需 GPT 视觉分析，请设置环境变量 OPENAI_API_KEY 后重新运行。
</p>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def main():
    args = parse_args()

    # 1. 解析 HTML
    interfaces = extract_interfaces(args.html)

    # 2. 过滤指定界面
    if args.iface:
        interfaces = [i for i in interfaces if i["id"] in args.iface]
        print(f"📌 只处理界面：{[i['id'] for i in interfaces]}")

    if not interfaces:
        print("❌ 没有找到任何界面，退出")
        return

    # 3. 逐界面处理
    results = []
    for idx, iface in enumerate(interfaces):
        print(f"\n{'='*60}")
        print(f"🔍 [{idx+1}/{len(interfaces)}] 界面 [{iface['id']}] {iface['name']}")
        print(f"   控件数: {len(iface['widgets'])}  |  截图: {'有' if iface['screenshot_b64'] else '无'}")

        result = {
            "id":           iface["id"],
            "name":         iface["name"],
            "widget_count": len(iface["widgets"]),
            "success":      False,
            "report":       None,
        }

        # 保存截图
        img_path = save_screenshot(iface)
        if not img_path:
            print("  ⚠️ 无截图，跳过")
            results.append(result)
            continue

        print(f"  💾 截图已保存: {Path(img_path).name}")

        # 生成 buttons.json
        btn_path = build_buttons_json(iface, img_path)
        if btn_path:
            print(f"  📋 热区数据: {Path(btn_path).name}")

        # 调用 analyzer
        print(f"  🚀 开始分析...")
        try:
            ok, msg = run_analyzer(img_path, btn_path,
                                   args.platform, args.resolution, args.dpi_scale)
        except subprocess.TimeoutExpired:
            ok, msg = False, "分析超时（120s）"

        if ok:
            # 找到最新生成的报告文件
            reports = sorted(REPORT_DIR.glob(f"usability_report_iface_*.html"),
                             key=lambda p: p.stat().st_mtime, reverse=True)
            # 更宽泛地搜
            all_reports = sorted(REPORT_DIR.glob("usability_report_*.html"),
                                  key=lambda p: p.stat().st_mtime, reverse=True)
            latest = all_reports[0] if all_reports else None

            result["success"] = True
            result["report"] = str(latest) if latest else None
            print(f"  ✅ 分析完成 → {latest.name if latest else '（未找到报告）'}")
        else:
            print(f"  ❌ 分析失败: {msg[:200]}")

        results.append(result)

    # 4. 生成汇总报告
    print(f"\n{'='*60}")
    summary_path = generate_summary_report(interfaces, results)
    print(f"\n📊 汇总报告已生成: {summary_path}")

    success = sum(1 for r in results if r["success"])
    print(f"\n🎉 完成！{success}/{len(results)} 个界面分析成功")
    print(f"📁 所有报告位于: {REPORT_DIR}")


if __name__ == "__main__":
    main()
