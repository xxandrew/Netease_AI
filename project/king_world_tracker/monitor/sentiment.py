"""综合舆情快照计算"""
from datetime import datetime
from database import db

GAME = "王者荣耀世界"

def compute_snapshot():
    """综合所有来源，计算当前舆情综合评分"""
    weibo  = db.get_latest_weibo()
    bili   = db.get_latest_bilibili()
    news   = db.get_latest_news()

    # 情感综合（微博为主，B站次之）
    pos, neg, neu = 0.33, 0.33, 0.34
    if weibo:
        pos = sum(w["sentiment_pos"] for w in weibo) / len(weibo)
        neg = sum(w["sentiment_neg"] for w in weibo) / len(weibo)
        neu = 1 - pos - neg

    bili_score = 0.5
    if bili:
        bili_score = sum(b.get("sentiment_score", 0.5) for b in bili) / len(bili)

    # 混合情感
    mix_pos = pos * 0.6 + bili_score * 0.4
    mix_neg = neg * 0.6 + (1 - bili_score) * 0.2

    # 热度评分（基于微博讨论量 + B站播放量归一化）
    weibo_discuss = sum(w.get("discuss_count", 0) for w in weibo) if weibo else 0
    bili_view = sum(b.get("total_view", 0) for b in bili) if bili else 0
    news_count = len([n for n in news if n.get("sentiment") == "positive"]) if news else 0

    heat_score = min(100, (
        min(weibo_discuss / 10000, 50) +
        min(bili_view / 1000000, 30) +
        min(news_count * 5, 20)
    ))

    # 综合舆情评分（0-100）
    overall = round(mix_pos * 100 * 0.7 + heat_score * 0.3, 1)

    return {
        "overall_score": overall,
        "pos_ratio": round(mix_pos, 3),
        "neg_ratio": round(mix_neg, 3),
        "neu_ratio": round(max(0, 1 - mix_pos - mix_neg), 3),
        "heat_score": round(heat_score, 1),
        "weibo_discuss": weibo_discuss,
        "bili_view": bili_view,
        "news_count": len(news),
        "fetched_at": datetime.now().isoformat(),
    }
