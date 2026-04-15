import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from apscheduler.schedulers.background import BackgroundScheduler
from crawler.app_store import fetch_taptap, fetch_appstore_ranks
from crawler.weibo import fetch_weibo
from crawler.bilibili import fetch_bilibili
from crawler.news import fetch_news
from database import db
from monitor.sentiment import compute_snapshot

def collect_all():
    print("[Scheduler] 开始采集王者荣耀世界数据...")
    now = __import__('datetime').datetime.now().isoformat()

    # 应用商店
    taptap = fetch_taptap()
    appstore = fetch_appstore_ranks()
    db.insert_app_store(taptap + appstore)
    # 榜单历史
    rank_rows = [{"platform":r["source"],"region":r["region"],"rank_type":r["rank_type"],
                  "rank":r["rank"],"fetched_at":now} for r in appstore if r.get("rank",0) > 0]
    db.insert_rank(rank_rows)
    print(f"  [AppStore] 写入 {len(taptap+appstore)} 条")

    # 微博
    weibo = fetch_weibo()
    db.insert_weibo(weibo)
    print(f"  [Weibo] 写入 {len(weibo)} 条")

    # B站
    bili = fetch_bilibili()
    db.insert_bilibili(bili)
    print(f"  [Bilibili] 写入 {len(bili)} 条")

    # 新闻
    news = fetch_news()
    db.insert_news(news)
    print(f"  [News] 写入 {len(news)} 条")

    # 舆情快照
    snapshot = compute_snapshot()
    db.insert_snapshot(snapshot)
    print(f"  [Snapshot] 舆情评分={snapshot['overall_score']}, 热度={snapshot['heat_score']}")
    print("[Scheduler] 采集完成")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(collect_all, "interval", hours=1, id="collect_all")
    scheduler.add_job(collect_all, "cron", hour=8, minute=0, id="daily_collect")
    scheduler.start()
    print("[Scheduler] 定时任务已启动（每小时采集）")
    return scheduler
