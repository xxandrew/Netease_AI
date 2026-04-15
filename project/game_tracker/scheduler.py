import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from apscheduler.schedulers.background import BackgroundScheduler
from crawler.steam import fetch_all_steam_regions
from crawler.twitch import fetch_twitch_top_games
from crawler.mobile import fetch_all_appstore, fetch_taptap_top
from database import db
from report.generator import generate_report

def collect_all():
    print("[Scheduler] 开始采集数据...")
    steam = fetch_all_steam_regions(50)
    if steam:
        db.insert_steam(steam)
        print(f"[Steam] 写入 {len(steam)} 条（五区 Top 50）")

    twitch = fetch_twitch_top_games(20)
    if twitch:
        db.insert_twitch(twitch)
        print(f"[Twitch] 写入 {len(twitch)} 条")

    mobile = fetch_all_appstore(20) + fetch_taptap_top(20)
    if mobile:
        db.insert_mobile(mobile)
        print(f"[Mobile] 写入 {len(mobile)} 条（含四区 App Store + TapTap）")
    print("[Scheduler] 数据采集完成")

def daily_report():
    print("[Scheduler] 生成日报...")
    content = generate_report("daily")
    print(f"[Scheduler] 日报生成完成，长度 {len(content)} 字符")

def weekly_report():
    print("[Scheduler] 生成周报...")
    content = generate_report("weekly")
    print(f"[Scheduler] 周报生成完成，长度 {len(content)} 字符")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    # 每 1 小时采集一次数据
    scheduler.add_job(collect_all, "interval", hours=1, id="collect_all")
    # 每天 08:00 生成日报
    scheduler.add_job(daily_report, "cron", hour=8, minute=0, id="daily_report")
    # 每周一 08:30 生成周报
    scheduler.add_job(weekly_report, "cron", day_of_week="mon", hour=8, minute=30, id="weekly_report")
    scheduler.start()
    print("[Scheduler] 定时任务已启动")
    return scheduler
