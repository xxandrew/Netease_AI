import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from flask import Flask, jsonify, render_template, request
from database import db
from scheduler import start_scheduler, collect_all
from report.generator import generate_report
from report.ppt_generator import generate_ppt
from monitor import engine as monitor

app = Flask(__name__)

# 初始化数据库
db.init_db()

# 首次启动时采集一次数据（异步后台）
import threading
threading.Thread(target=collect_all, daemon=True).start()

# 启动定时任务
start_scheduler()

# ─────────────────────────── 页面路由 ───────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─────────────────────────── API 路由 ───────────────────────────

@app.route("/api/steam")
def api_steam():
    """返回所有区域数据，按 region_code 分组"""
    all_data = db.get_latest_steam(50)
    grouped = {}
    for g in all_data:
        key = g.get("region_code") or "global"
        grouped.setdefault(key, []).append(g)
    return jsonify(grouped)

@app.route("/api/steam/region/<region_code>")
def api_steam_region(region_code):
    data = db.get_latest_steam_by_region(region_code, 50)
    return jsonify(data)

@app.route("/api/twitch")
def api_twitch():
    data = db.get_latest_twitch(20)
    return jsonify(data)

@app.route("/api/mobile")
def api_mobile():
    """返回所有区域数据，按 region_code 分组"""
    all_data = db.get_latest_mobile(20)
    # 按 region_code 分组返回
    grouped = {}
    for g in all_data:
        key = g.get("region_code") or "other"
        grouped.setdefault(key, []).append(g)
    return jsonify(grouped)

@app.route("/api/mobile/region/<region_code>")
def api_mobile_region(region_code):
    data = db.get_latest_mobile_by_region(region_code, 20)
    return jsonify(data)

@app.route("/api/reports")
def api_reports():
    data = db.get_latest_reports(10)
    return jsonify(data)

@app.route("/api/report/generate", methods=["POST"])
def api_generate_report():
    report_type = request.json.get("type", "daily")
    content = generate_report(report_type)
    return jsonify({"content": content})

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=collect_all, daemon=True).start()
    return jsonify({"status": "ok", "message": "数据采集已在后台启动"})

@app.route("/api/steam/trend")
def api_steam_trend():
    name = request.args.get("name", "")
    data = db.get_steam_trend(name, 14)
    return jsonify(data)

# ─────────────────────────── 检测 API ───────────────────────────

@app.route("/api/monitor/anomalies")
def api_anomalies():
    threshold = float(request.args.get("threshold", 2.0))
    return jsonify(monitor.detect_anomalies(threshold_ratio=threshold))

@app.route("/api/monitor/trends")
def api_trends():
    return jsonify(monitor.analyze_trends())

@app.route("/api/monitor/cross_region")
def api_cross_region():
    return jsonify(monitor.cross_region_analysis())

@app.route("/api/monitor/watchlist", methods=["GET"])
def api_watchlist_get():
    return jsonify(monitor.get_watchlist_status())

@app.route("/api/monitor/watchlist", methods=["POST"])
def api_watchlist_add():
    data = request.json or {}
    name = data.get("name", "").strip()
    platform = data.get("platform", "steam")
    if not name:
        return jsonify({"ok": False, "error": "游戏名称不能为空"}), 400
    return jsonify(monitor.add_to_watchlist(name, platform))

@app.route("/api/monitor/watchlist/<path:name>", methods=["DELETE"])
def api_watchlist_remove(name):
    return jsonify(monitor.remove_from_watchlist(name))

@app.route("/api/monitor/diff")
def api_diff():
    region_code = request.args.get("region", "global")
    platform = request.args.get("platform", "steam")
    return jsonify(monitor.compute_diff(region_code, platform))

@app.route("/api/monitor/quality")
def api_quality():
    return jsonify(monitor.check_data_quality())

# ─────────────────────────── PPT 生成 ───────────────────────────

@app.route("/api/ppt/generate")
def api_ppt_generate():
    from flask import send_file
    name = request.args.get("name", "").strip()
    days = int(request.args.get("days", 30))
    if not name:
        return jsonify({"error": "游戏名称不能为空"}), 400
    try:
        buf = generate_ppt(name, days)
        safe_name = name.replace("/","_").replace("\\","_")
        filename = f"{safe_name}_数据分析报告_{datetime.now().strftime('%Y%m%d')}.pptx"
        return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                         as_attachment=True, download_name=filename)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)