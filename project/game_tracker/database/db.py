import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/game_tracker.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Steam 游戏数据
    c.execute("""
        CREATE TABLE IF NOT EXISTS steam_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            app_id TEXT,
            current_players INTEGER,
            peak_players INTEGER,
            positive_reviews INTEGER,
            negative_reviews INTEGER,
            price TEXT,
            tags TEXT,
            rank INTEGER,
            region_code TEXT,
            region TEXT,
            flag TEXT,
            fetched_at TEXT
        )
    """)
    # 兼容旧表：尝试添加新列
    for col in ["rank INTEGER", "region_code TEXT", "region TEXT", "flag TEXT"]:
        try:
            c.execute(f"ALTER TABLE steam_games ADD COLUMN {col}")
        except Exception:
            pass
    # 清除没有 region_code 的旧 steam 数据
    c.execute("DELETE FROM steam_games WHERE region_code IS NULL OR region_code = ''")
    # Twitch 直播数据
    c.execute("""
        CREATE TABLE IF NOT EXISTS twitch_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            game_id TEXT,
            viewer_count INTEGER,
            channel_count INTEGER,
            fetched_at TEXT
        )
    """)
    # 手游排行数据
    c.execute("""
        CREATE TABLE IF NOT EXISTS mobile_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            platform TEXT,
            region TEXT,
            region_code TEXT,
            flag TEXT,
            rank INTEGER,
            category TEXT,
            app_id TEXT,
            artwork TEXT,
            fetched_at TEXT
        )
    """)
    # 兼容旧表：尝试添加新列（忽略已存在错误）
    for col in ["region TEXT", "region_code TEXT", "flag TEXT", "app_id TEXT", "artwork TEXT"]:
        try:
            c.execute(f"ALTER TABLE mobile_games ADD COLUMN {col}")
        except Exception:
            pass
    # 清除没有 region_code 的旧数据，避免干扰分区查询
    c.execute("DELETE FROM mobile_games WHERE region_code IS NULL OR region_code = ''")
    # AI 报告
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_steam(games: list):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    for g in games:
        c.execute("""
            INSERT INTO steam_games
              (name, app_id, current_players, peak_players, positive_reviews, negative_reviews,
               price, tags, rank, region_code, region, flag, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g.get("name"), g.get("app_id"),
            g.get("current_players", 0), g.get("peak_players", 0),
            g.get("positive_reviews", 0), g.get("negative_reviews", 0),
            g.get("price", ""), g.get("tags", ""),
            g.get("rank", 0),
            g.get("region_code", "global"), g.get("region", "全球"), g.get("flag", "🌍"),
            now,
        ))
    conn.commit()
    conn.close()

def insert_twitch(games: list):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    for g in games:
        c.execute("""
            INSERT INTO twitch_games (name, game_id, viewer_count, channel_count, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (g.get("name"), g.get("game_id"), g.get("viewer_count"), g.get("channel_count"), now))
    conn.commit()
    conn.close()

def insert_mobile(games: list):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    for g in games:
        c.execute("""
            INSERT INTO mobile_games
              (name, platform, region, region_code, flag, rank, category, app_id, artwork, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g.get("name"), g.get("platform"),
            g.get("region", ""), g.get("region_code", ""), g.get("flag", ""),
            g.get("rank"), g.get("category"),
            g.get("app_id", ""), g.get("artwork", ""),
            now,
        ))
    conn.commit()
    conn.close()

def save_report(report_type: str, content: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO ai_reports (report_type, content, created_at) VALUES (?, ?, ?)",
              (report_type, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_latest_steam(limit=50):
    """按每个 region_code 分别取最新数据，合并返回"""
    conn = get_conn()
    c = conn.cursor()
    codes = [r[0] for r in c.execute(
        "SELECT DISTINCT region_code FROM steam_games WHERE region_code IS NOT NULL AND region_code != ''"
    ).fetchall()]
    all_rows = []
    for code in codes:
        order = "current_players DESC" if code == "global" else "rank ASC"
        rows = c.execute(f"""
            SELECT * FROM steam_games
            WHERE region_code = ?
              AND fetched_at = (SELECT MAX(fetched_at) FROM steam_games WHERE region_code = ?)
            ORDER BY {order} LIMIT ?
        """, (code, code, limit)).fetchall()
        all_rows.extend([dict(r) for r in rows])
    conn.close()
    return all_rows

def get_latest_steam_by_region(region_code: str, limit=50):
    conn = get_conn()
    c = conn.cursor()
    order = "current_players DESC" if region_code == "global" else "rank ASC"
    rows = c.execute(f"""
        SELECT * FROM steam_games
        WHERE region_code = ?
          AND fetched_at = (SELECT MAX(fetched_at) FROM steam_games WHERE region_code = ?)
        ORDER BY {order} LIMIT ?
    """, (region_code, region_code, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_twitch(limit=20):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("""
        SELECT * FROM twitch_games
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM twitch_games)
        ORDER BY viewer_count DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_mobile(limit=20):
    """按每个 region_code 分别取最新一批数据，合并返回"""
    conn = get_conn()
    c = conn.cursor()
    # 取所有存在的 region_code
    codes = [r[0] for r in c.execute(
        "SELECT DISTINCT region_code FROM mobile_games WHERE region_code IS NOT NULL AND region_code != ''"
    ).fetchall()]
    all_rows = []
    for code in codes:
        rows = c.execute("""
            SELECT * FROM mobile_games
            WHERE region_code = ?
              AND fetched_at = (SELECT MAX(fetched_at) FROM mobile_games WHERE region_code = ?)
            ORDER BY rank ASC LIMIT ?
        """, (code, code, limit)).fetchall()
        all_rows.extend([dict(r) for r in rows])
    conn.close()
    return all_rows

def get_latest_mobile_by_region(region_code: str, limit=20):
    """获取指定区域最新手游数据"""
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("""
        SELECT * FROM mobile_games
        WHERE region_code = ?
          AND fetched_at = (
              SELECT MAX(fetched_at) FROM mobile_games WHERE region_code = ?
          )
        ORDER BY rank ASC LIMIT ?
    """, (region_code, region_code, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_reports(limit=5):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM ai_reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_steam_trend(name: str, limit=14):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("""
        SELECT fetched_at, current_players FROM steam_games
        WHERE name = ? ORDER BY fetched_at DESC LIMIT ?
    """, (name, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
