import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv; load_dotenv()

from flask import Flask, jsonify, render_template, request
from database import db
from scheduler import start_scheduler, collect_all
import threading

app = Flask(__name__)
db.init_db()

# 启动时采集一次
threading.Thread(target=collect_all, daemon=True).start()
start_scheduler()

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/snapshot")
def api_snapshot(): return jsonify(db.get_snapshots(30))

@app.route("/api/weibo")
def api_weibo(): return jsonify(db.get_latest_weibo())

@app.route("/api/bilibili")
def api_bilibili(): return jsonify(db.get_latest_bilibili())

@app.route("/api/news")
def api_news(): return jsonify(db.get_latest_news())

@app.route("/api/appstore")
def api_appstore(): return jsonify(db.get_latest_app())

@app.route("/api/rank_history")
def api_rank_history(): return jsonify(db.get_rank_history(60))

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=collect_all, daemon=True).start()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5001, use_reloader=False)
