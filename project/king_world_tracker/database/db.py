import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/king_world.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # TapTap / AppStore 应用数据
    c.execute("""CREATE TABLE IF NOT EXISTS app_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, region TEXT, rank INTEGER, rank_type TEXT,
        score REAL, review_count INTEGER, reserve_count INTEGER,
        fetched_at TEXT)""")

    # 榜单排名历史
    c.execute("""CREATE TABLE IF NOT EXISTS rank_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT, region TEXT, rank_type TEXT,
        rank INTEGER, fetched_at TEXT)""")

    # 微博舆论
    c.execute("""CREATE TABLE IF NOT EXISTS weibo_buzz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT, read_count INTEGER, discuss_count INTEGER,
        sentiment_pos REAL, sentiment_neg REAL, sentiment_neu REAL,
        hot_comments TEXT, fetched_at TEXT)""")

    # B站数据
    c.execute("""CREATE TABLE IF NOT EXISTS bilibili_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT, video_count INTEGER, total_view INTEGER,
        total_like INTEGER, total_coin INTEGER, total_danmaku INTEGER,
        top_videos TEXT, sentiment_score REAL, fetched_at TEXT)""")

    # 百度/搜索指数
    c.execute("""CREATE TABLE IF NOT EXISTS search_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT, keyword TEXT, index_value INTEGER,
        fetched_at TEXT)""")

    # 媒体报道
    c.execute("""CREATE TABLE IF NOT EXISTS media_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, title TEXT, url TEXT, summary TEXT,
        sentiment TEXT, published_at TEXT, fetched_at TEXT)""")

    # 舆情快照（每次采集的综合评分）
    c.execute("""CREATE TABLE IF NOT EXISTS sentiment_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        overall_score REAL, pos_ratio REAL, neg_ratio REAL,
        neu_ratio REAL, heat_score REAL, data_json TEXT,
        fetched_at TEXT)""")

    conn.commit(); conn.close()

# ── 写入 ─────────────────────────────────────────
def insert_app_store(rows): _bulk(rows, "app_store",
    ["source","region","rank","rank_type","score","review_count","reserve_count","fetched_at"])

def insert_rank(rows): _bulk(rows, "rank_history",
    ["platform","region","rank_type","rank","fetched_at"])

def insert_weibo(rows): _bulk(rows, "weibo_buzz",
    ["topic","read_count","discuss_count","sentiment_pos","sentiment_neg","sentiment_neu","hot_comments","fetched_at"])

def insert_bilibili(rows): _bulk(rows, "bilibili_data",
    ["keyword","video_count","total_view","total_like","total_coin","total_danmaku","top_videos","sentiment_score","fetched_at"])

def insert_search(rows): _bulk(rows, "search_index",
    ["platform","keyword","index_value","fetched_at"])

def insert_news(rows): _bulk(rows, "media_news",
    ["source","title","url","summary","sentiment","published_at","fetched_at"])

def insert_snapshot(data: dict):
    conn = get_conn(); c = conn.cursor()
    import json
    c.execute("""INSERT INTO sentiment_snapshot
        (overall_score,pos_ratio,neg_ratio,neu_ratio,heat_score,data_json,fetched_at)
        VALUES(?,?,?,?,?,?,?)""",
        (data.get("overall_score"), data.get("pos_ratio"), data.get("neg_ratio"),
         data.get("neu_ratio"), data.get("heat_score"),
         json.dumps(data, ensure_ascii=False), datetime.now().isoformat()))
    conn.commit(); conn.close()

def _bulk(rows, table, fields):
    if not rows: return
    conn = get_conn(); c = conn.cursor()
    ph = ",".join(["?"]*len(fields))
    sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES({ph})"
    for r in rows:
        c.execute(sql, [r.get(f) for f in fields])
    conn.commit(); conn.close()

# ── 查询 ─────────────────────────────────────────
def _latest(table, time_col="fetched_at", limit=50):
    conn = get_conn(); c = conn.cursor()
    ts = c.execute(f"SELECT MAX({time_col}) FROM {table}").fetchone()[0]
    if not ts: conn.close(); return []
    rows = c.execute(f"SELECT * FROM {table} WHERE {time_col}=? LIMIT ?", (ts, limit)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def _history(table, time_col="fetched_at", limit=30):
    conn = get_conn(); c = conn.cursor()
    rows = c.execute(f"SELECT * FROM {table} ORDER BY {time_col} DESC LIMIT ?", (limit,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_latest_app()       : return _latest("app_store")
def get_latest_weibo()     : return _latest("weibo_buzz")
def get_latest_bilibili()  : return _latest("bilibili_data")
def get_latest_search()    : return _latest("search_index")
def get_latest_news()      : return _history("media_news", limit=20)
def get_rank_history(limit=30): return _history("rank_history", limit=limit)
def get_snapshots(limit=30): return _history("sentiment_snapshot", limit=limit)
