"""
数据检测引擎 - 6大类检测
1. 异常检测
2. 趋势分析
3. 跨区域对比
4. Watch List 关注追踪
5. 榜单变动 Diff
6. 数据质量检测
"""
import sqlite3
import os
from datetime import datetime, timedelta
from database.db import get_conn

# ═══════════════════════════════════════════════════════════════
# 1. 异常检测
# ═══════════════════════════════════════════════════════════════

def detect_anomalies(threshold_ratio=2.0, top_n=50):
    """
    检测 Steam 全球在线人数异常（暴涨/暴跌/新进榜/消失）
    threshold_ratio: 超过历史均值 N 倍视为异常
    """
    conn = get_conn()
    c = conn.cursor()

    # 获取所有 global 区最近 14 次采集的时间点
    timestamps = [r[0] for r in c.execute("""
        SELECT DISTINCT fetched_at FROM steam_games
        WHERE region_code='global'
        ORDER BY fetched_at DESC LIMIT 14
    """).fetchall()]

    if len(timestamps) < 2:
        conn.close()
        return {"error": "数据不足（至少需要 2 次采集记录）", "items": []}

    latest_ts = timestamps[0]
    prev_ts = timestamps[1]

    # 当前榜单
    latest = {r["name"]: dict(r) for r in c.execute("""
        SELECT name, current_players, rank FROM steam_games
        WHERE region_code='global' AND fetched_at=?
    """, (latest_ts,)).fetchall()}

    # 上次榜单
    prev = {r["name"]: dict(r) for r in c.execute("""
        SELECT name, current_players, rank FROM steam_games
        WHERE region_code='global' AND fetched_at=?
    """, (prev_ts,)).fetchall()}

    # 历史均值（去掉最新一次）
    hist_rows = c.execute("""
        SELECT name, AVG(current_players) as avg_p FROM steam_games
        WHERE region_code='global' AND fetched_at != ?
        GROUP BY name
    """, (latest_ts,)).fetchall()
    hist_avg = {r["name"]: r["avg_p"] for r in hist_rows}

    conn.close()

    alerts = []

    # 新进榜
    for name in latest:
        if name not in prev:
            alerts.append({
                "type": "new_entry", "level": "info",
                "icon": "🆕", "label": "新进榜",
                "name": name,
                "current": latest[name]["current_players"],
                "prev": 0,
                "detail": f"本次新出现在榜单，当前在线 {latest[name]['current_players']:,}",
            })

    # 消失
    for name in prev:
        if name not in latest:
            alerts.append({
                "type": "disappeared", "level": "warning",
                "icon": "👻", "label": "掉出榜单",
                "name": name,
                "current": 0,
                "prev": prev[name]["current_players"],
                "detail": f"从榜单消失，上次在线 {prev[name]['current_players']:,}",
            })

    # 暴涨/暴跌
    for name, cur in latest.items():
        cur_p = cur["current_players"] or 0
        avg_p = hist_avg.get(name, cur_p) or cur_p
        if avg_p == 0:
            continue
        ratio = cur_p / avg_p
        if ratio >= threshold_ratio:
            alerts.append({
                "type": "surge", "level": "success",
                "icon": "🚀", "label": "暴涨",
                "name": name,
                "current": cur_p,
                "prev": int(avg_p),
                "detail": f"当前在线是历史均值的 {ratio:.1f} 倍（均值 {int(avg_p):,}）",
            })
        elif ratio <= (1 / threshold_ratio) and cur_p < avg_p - 1000:
            alerts.append({
                "type": "crash", "level": "danger",
                "icon": "📉", "label": "暴跌",
                "name": name,
                "current": cur_p,
                "prev": int(avg_p),
                "detail": f"当前在线仅为历史均值的 {ratio:.1%}（均值 {int(avg_p):,}）",
            })

    return {
        "checked_at": latest_ts,
        "total_alerts": len(alerts),
        "items": sorted(alerts, key=lambda x: {"success":0,"warning":1,"danger":2,"info":3}.get(x["level"],4)),
    }


# ═══════════════════════════════════════════════════════════════
# 2. 趋势分析
# ═══════════════════════════════════════════════════════════════

def analyze_trends(top_n=20):
    """分析 Steam 全球游戏趋势：增速排行 / 连续涨跌 / 周环比"""
    conn = get_conn()
    c = conn.cursor()

    timestamps = [r[0] for r in c.execute("""
        SELECT DISTINCT fetched_at FROM steam_games
        WHERE region_code='global' ORDER BY fetched_at DESC LIMIT 14
    """).fetchall()]

    if len(timestamps) < 3:
        conn.close()
        return {"error": "数据不足（至少需要 3 次采集）", "rising":[], "falling":[], "weekly":[]}

    latest_ts = timestamps[0]

    # 获取最新数据
    latest = {r["name"]: r["current_players"] or 0 for r in c.execute("""
        SELECT name, current_players FROM steam_games
        WHERE region_code='global' AND fetched_at=?
    """, (latest_ts,)).fetchall()}

    # 各游戏历史序列（最近14次）
    all_series = {}
    for name in latest:
        rows = c.execute("""
            SELECT fetched_at, current_players FROM steam_games
            WHERE region_code='global' AND name=?
            ORDER BY fetched_at DESC LIMIT 14
        """, (name,)).fetchall()
        all_series[name] = [r["current_players"] or 0 for r in rows]

    conn.close()

    rising, falling, weekly = [], [], []

    for name, series in all_series.items():
        if len(series) < 2:
            continue
        cur = series[0]
        prev = series[1] if len(series) > 1 else cur
        week_ago = series[6] if len(series) > 6 else series[-1]

        # 增速（vs上次）
        if prev > 0:
            change_rate = (cur - prev) / prev * 100
        else:
            change_rate = 0

        # 周环比
        if week_ago > 0:
            weekly_rate = (cur - week_ago) / week_ago * 100
        else:
            weekly_rate = 0

        # 连续涨跌判断
        streak = 0
        direction = None
        for i in range(len(series) - 1):
            if series[i] > series[i+1]:
                d = "up"
            elif series[i] < series[i+1]:
                d = "down"
            else:
                break
            if direction is None:
                direction = d
            if d == direction:
                streak += 1
            else:
                break

        item = {
            "name": name,
            "current": cur,
            "change_rate": round(change_rate, 1),
            "weekly_rate": round(weekly_rate, 1),
            "streak": streak,
            "streak_dir": direction,
        }

        if change_rate > 5:
            rising.append(item)
        elif change_rate < -5:
            falling.append(item)

        weekly.append(item)

    rising.sort(key=lambda x: -x["change_rate"])
    falling.sort(key=lambda x: x["change_rate"])
    weekly.sort(key=lambda x: -x["weekly_rate"])

    return {
        "rising": rising[:top_n],
        "falling": falling[:top_n],
        "weekly": weekly[:top_n],
        "checked_at": latest_ts,
    }


# ═══════════════════════════════════════════════════════════════
# 3. 跨区域对比
# ═══════════════════════════════════════════════════════════════

def cross_region_analysis():
    """分析各区域榜单的重叠度、区域独热、多区同热"""
    conn = get_conn()
    c = conn.cursor()

    regions = ["global", "cn", "us", "jp", "kr"]
    region_labels = {"global":"🌍全球","cn":"🇨🇳中国","us":"🇺🇸美国","jp":"🇯🇵日本","kr":"🇰🇷韩国"}
    region_sets = {}

    for region in regions:
        ts = c.execute("""
            SELECT MAX(fetched_at) FROM steam_games WHERE region_code=?
        """, (region,)).fetchone()[0]
        if not ts:
            continue
        names = {r["name"] for r in c.execute("""
            SELECT name FROM steam_games WHERE region_code=? AND fetched_at=?
        """, (region, ts)).fetchall()}
        region_sets[region] = names

    conn.close()

    if len(region_sets) < 2:
        return {"error": "数据不足"}

    # 多区同时上榜（出现在 3+ 个区）
    all_names = {}
    for region, names in region_sets.items():
        for name in names:
            all_names.setdefault(name, []).append(region)

    multi_region = [
        {"name": n, "regions": [region_labels.get(r, r) for r in rs], "count": len(rs)}
        for n, rs in all_names.items() if len(rs) >= 3
    ]
    multi_region.sort(key=lambda x: -x["count"])

    # 区域独热（只在某一区出现）
    exclusive = {}
    for region in regions:
        if region not in region_sets:
            continue
        others = set()
        for r2, s in region_sets.items():
            if r2 != region:
                others |= s
        only = region_sets[region] - others
        exclusive[region] = {
            "label": region_labels.get(region, region),
            "games": sorted(only)[:20],
            "count": len(only),
        }

    # 重叠率矩阵
    overlap_matrix = []
    region_list = list(region_sets.keys())
    for i, r1 in enumerate(region_list):
        for r2 in region_list[i+1:]:
            s1, s2 = region_sets[r1], region_sets[r2]
            overlap = len(s1 & s2)
            union = len(s1 | s2)
            rate = round(overlap / union * 100, 1) if union else 0
            overlap_matrix.append({
                "r1": region_labels.get(r1, r1),
                "r2": region_labels.get(r2, r2),
                "overlap": overlap,
                "rate": rate,
            })
    overlap_matrix.sort(key=lambda x: -x["rate"])

    return {
        "multi_region": multi_region[:30],
        "exclusive": exclusive,
        "overlap_matrix": overlap_matrix,
    }


# ═══════════════════════════════════════════════════════════════
# 4. Watch List
# ═══════════════════════════════════════════════════════════════

def get_watchlist():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            platform TEXT DEFAULT 'steam',
            added_at TEXT
        )
    """)
    rows = c.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_to_watchlist(name: str, platform: str = "steam"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            platform TEXT DEFAULT 'steam',
            added_at TEXT
        )
    """)
    try:
        c.execute("INSERT INTO watchlist (name, platform, added_at) VALUES (?, ?, ?)",
                  (name, platform, datetime.now().isoformat()))
        conn.commit()
        result = {"ok": True}
    except sqlite3.IntegrityError:
        result = {"ok": False, "error": "已在关注列表中"}
    conn.close()
    return result

def remove_from_watchlist(name: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM watchlist WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return {"ok": True}

def get_watchlist_status():
    """获取关注游戏的最新数据 + 变动情况"""
    items = get_watchlist()
    if not items:
        return []

    conn = get_conn()
    c = conn.cursor()
    result = []

    for item in items:
        name = item["name"]
        # 最近 2 次在全球榜的数据
        rows = c.execute("""
            SELECT current_players, rank, fetched_at FROM steam_games
            WHERE name=? AND region_code='global'
            ORDER BY fetched_at DESC LIMIT 2
        """, (name,)).fetchall()

        if not rows:
            result.append({**item, "status": "未在榜", "current": 0, "prev": 0,
                           "change": 0, "rank": "-", "rank_change": 0, "in_chart": False})
            continue

        cur = dict(rows[0])
        prev = dict(rows[1]) if len(rows) > 1 else cur
        change = (cur["current_players"] or 0) - (prev["current_players"] or 0)
        rank_change = (prev["rank"] or 0) - (cur["rank"] or 0)  # 正数=排名上升
        result.append({
            **item,
            "status": "在榜",
            "current": cur["current_players"] or 0,
            "prev": prev["current_players"] or 0,
            "change": change,
            "rank": cur["rank"],
            "rank_change": rank_change,
            "in_chart": True,
            "fetched_at": cur["fetched_at"],
        })

    conn.close()
    return result


# ═══════════════════════════════════════════════════════════════
# 5. 榜单变动 Diff
# ═══════════════════════════════════════════════════════════════

def compute_diff(region_code="global", platform="steam"):
    """计算最新两次采集之间的榜单变动"""
    conn = get_conn()
    c = conn.cursor()

    if platform == "steam":
        timestamps = [r[0] for r in c.execute("""
            SELECT DISTINCT fetched_at FROM steam_games
            WHERE region_code=? ORDER BY fetched_at DESC LIMIT 2
        """, (region_code,)).fetchall()]

        if len(timestamps) < 2:
            conn.close()
            return {"error": "数据不足，需至少 2 次采集"}

        def get_snapshot(ts):
            rows = c.execute("""
                SELECT name, rank, current_players FROM steam_games
                WHERE region_code=? AND fetched_at=?
                ORDER BY rank ASC
            """, (region_code, ts)).fetchall()
            return {r["name"]: dict(r) for r in rows}

    else:  # mobile
        timestamps = [r[0] for r in c.execute("""
            SELECT DISTINCT fetched_at FROM mobile_games
            WHERE region_code=? ORDER BY fetched_at DESC LIMIT 2
        """, (region_code,)).fetchall()]

        if len(timestamps) < 2:
            conn.close()
            return {"error": "数据不足，需至少 2 次采集"}

        def get_snapshot(ts):
            rows = c.execute("""
                SELECT name, rank FROM mobile_games
                WHERE region_code=? AND fetched_at=?
                ORDER BY rank ASC
            """, (region_code, ts)).fetchall()
            return {r["name"]: dict(r) for r in rows}

    latest = get_snapshot(timestamps[0])
    prev = get_snapshot(timestamps[1])
    conn.close()

    new_entries = []
    disappeared = []
    rank_up = []
    rank_down = []

    for name, cur in latest.items():
        if name not in prev:
            new_entries.append({"name": name, "rank": cur.get("rank"), "current": cur.get("current_players", 0)})
        else:
            r1 = prev[name].get("rank") or 0
            r2 = cur.get("rank") or 0
            if r1 and r2:
                delta = r1 - r2  # 正数=排名上升
                if delta > 0:
                    rank_up.append({"name": name, "rank": r2, "prev_rank": r1, "delta": delta})
                elif delta < 0:
                    rank_down.append({"name": name, "rank": r2, "prev_rank": r1, "delta": delta})

    for name in prev:
        if name not in latest:
            disappeared.append({"name": name, "prev_rank": prev[name].get("rank")})

    rank_up.sort(key=lambda x: -x["delta"])
    rank_down.sort(key=lambda x: x["delta"])

    return {
        "latest_ts": timestamps[0][:16].replace("T", " "),
        "prev_ts": timestamps[1][:16].replace("T", " "),
        "new_entries": new_entries[:20],
        "disappeared": disappeared[:20],
        "rank_up": rank_up[:10],
        "rank_down": rank_down[:10],
        "total_new": len(new_entries),
        "total_gone": len(disappeared),
    }


# ═══════════════════════════════════════════════════════════════
# 6. 数据质量检测
# ═══════════════════════════════════════════════════════════════

def check_data_quality():
    """检查数据新鲜度、完整性、重复率"""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    results = []

    # Steam 各区
    for region_code in ["global", "cn", "us", "jp", "kr"]:
        row = c.execute("""
            SELECT MAX(fetched_at) as last_ts, COUNT(*) as total,
                   SUM(CASE WHEN name IS NULL OR name='' THEN 1 ELSE 0 END) as missing_name,
                   SUM(CASE WHEN rank IS NULL THEN 1 ELSE 0 END) as missing_rank
            FROM steam_games WHERE region_code=?
        """, (region_code,)).fetchone()

        last_ts = row["last_ts"]
        freshness_minutes = None
        freshness_status = "no_data"
        if last_ts:
            try:
                dt = datetime.fromisoformat(last_ts)
                freshness_minutes = int((now - dt).total_seconds() / 60)
                freshness_status = "fresh" if freshness_minutes < 90 else "stale" if freshness_minutes < 360 else "old"
            except Exception:
                pass

        # 最新一批的重复检测
        dup_count = 0
        if last_ts:
            dup_row = c.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT name) as dups FROM steam_games
                WHERE region_code=? AND fetched_at=?
            """, (region_code, last_ts)).fetchone()
            dup_count = dup_row[0] if dup_row else 0

        region_labels = {"global":"🌍全球","cn":"🇨🇳中国","us":"🇺🇸美国","jp":"🇯🇵日本","kr":"🇰🇷韩国"}
        results.append({
            "source": f"Steam {region_labels.get(region_code,region_code)}",
            "last_ts": last_ts[:16].replace("T"," ") if last_ts else "从未采集",
            "freshness_minutes": freshness_minutes,
            "freshness_status": freshness_status,
            "total_records": row["total"],
            "missing_name": row["missing_name"],
            "missing_rank": row["missing_rank"],
            "duplicates": dup_count,
        })

    # 手游各区
    for region_code in ["cn", "us", "jp", "kr"]:
        row = c.execute("""
            SELECT MAX(fetched_at) as last_ts, COUNT(*) as total,
                   SUM(CASE WHEN name IS NULL OR name='' THEN 1 ELSE 0 END) as missing_name,
                   SUM(CASE WHEN rank IS NULL THEN 1 ELSE 0 END) as missing_rank
            FROM mobile_games WHERE region_code=?
        """, (region_code,)).fetchone()

        last_ts = row["last_ts"]
        freshness_minutes = None
        freshness_status = "no_data"
        if last_ts:
            try:
                dt = datetime.fromisoformat(last_ts)
                freshness_minutes = int((now - dt).total_seconds() / 60)
                freshness_status = "fresh" if freshness_minutes < 90 else "stale" if freshness_minutes < 360 else "old"
            except Exception:
                pass

        dup_count = 0
        if last_ts:
            dup_row = c.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT name) as dups FROM mobile_games
                WHERE region_code=? AND fetched_at=?
            """, (region_code, last_ts)).fetchone()
            dup_count = dup_row[0] if dup_row else 0

        mobile_labels = {"cn":"🇨🇳中国","us":"🇺🇸美国","jp":"🇯🇵日本","kr":"🇰🇷韩国"}
        results.append({
            "source": f"手游 {mobile_labels.get(region_code,region_code)}",
            "last_ts": last_ts[:16].replace("T"," ") if last_ts else "从未采集",
            "freshness_minutes": freshness_minutes,
            "freshness_status": freshness_status,
            "total_records": row["total"],
            "missing_name": row["missing_name"],
            "missing_rank": row["missing_rank"],
            "duplicates": dup_count,
        })

    conn.close()
    return {"checked_at": now.isoformat()[:16], "sources": results}
