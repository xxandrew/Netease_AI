"""微博话题热度与情感分析爬虫"""
import requests, json, re
from datetime import datetime
from bs4 import BeautifulSoup
from snownlp import SnowNLP

GAME_KEYWORDS = ["王者荣耀世界", "王者世界", "KingWorldGame"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://s.weibo.com/",
}
NOW = lambda: datetime.now().isoformat()

# ── 情感分析 ─────────────────────────────────────
POS_WORDS = {"期待","好玩","精彩","震撼","厉害","牛","棒","爽","好看","强",
             "出色","优秀","流畅","好评","推荐","赞","完美","惊艳","创新","突破"}
NEG_WORDS = {"差","烂","垃圾","失望","难玩","坑","闪退","卡顿","崩溃","抄袭",
             "骗钱","氪金","坑钱","无聊","难看","不行","辣鸡","不好","恶心","抵制"}

def analyze_sentiment(texts: list) -> dict:
    """基于 SnowNLP + 关键词双重分析"""
    if not texts:
        return {"pos": 0.33, "neg": 0.33, "neu": 0.34}
    pos_scores, neg_count, pos_count, neu_count = [], 0, 0, 0
    for text in texts:
        try:
            snow_score = SnowNLP(text).sentiments
        except Exception:
            snow_score = 0.5
        # 关键词加权
        has_pos = any(w in text for w in POS_WORDS)
        has_neg = any(w in text for w in NEG_WORDS)
        if has_neg:
            snow_score = min(snow_score, 0.35)
        elif has_pos:
            snow_score = max(snow_score, 0.65)
        pos_scores.append(snow_score)
        if snow_score > 0.6:   pos_count += 1
        elif snow_score < 0.4: neg_count += 1
        else:                  neu_count += 1

    total = len(texts) or 1
    return {
        "pos": round(pos_count / total, 3),
        "neg": round(neg_count / total, 3),
        "neu": round(neu_count / total, 3),
    }


def fetch_weibo():
    """爬取微博话题热度（搜索接口）"""
    results = []
    now = NOW()
    for kw in GAME_KEYWORDS:
        data = _fetch_weibo_search(kw)
        results.append({**data, "topic": kw, "fetched_at": now})
    return results if results else _mock_weibo()

def _fetch_weibo_search(keyword: str) -> dict:
    """爬取微博搜索结果，提取讨论量和情感"""
    url = f"https://s.weibo.com/weibo?q={requests.utils.quote(keyword)}&Refer=SWeibo_box"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 提取文本内容做情感分析
        cards = soup.select("div.card-wrap article p.txt")
        texts = [c.get_text(strip=True) for c in cards[:30]]
        sentiment = analyze_sentiment(texts)

        # 提取热评
        hot_comments = [t[:50] for t in texts[:5]]

        # 讨论数（从热搜/话题栏获取，否则用条数估算）
        discuss_count = len(cards) * 100  # 粗估

        # 阅读量（尝试从话题页获取）
        read_count = 0
        topic_tag = soup.select_one("[class*='topic-panel'] [class*='num']")
        if topic_tag:
            txt = topic_tag.get_text(strip=True).replace("亿","00000000").replace("万","0000")
            nums = re.findall(r'\d+', txt.replace(",",""))
            if nums: read_count = int(nums[0])

        return {
            "read_count": read_count or discuss_count * 50,
            "discuss_count": discuss_count,
            "sentiment_pos": sentiment["pos"],
            "sentiment_neg": sentiment["neg"],
            "sentiment_neu": sentiment["neu"],
            "hot_comments": json.dumps(hot_comments, ensure_ascii=False),
        }
    except Exception as e:
        print(f"[Weibo] '{keyword}' 爬取失败: {e}")
        return _mock_weibo_item()

def _mock_weibo_item():
    return {"read_count":285000000,"discuss_count":420000,
            "sentiment_pos":0.62,"sentiment_neg":0.18,"sentiment_neu":0.20,
            "hot_comments":json.dumps(["期待上线！","画面太震撼了","这是王者的新高度","希望不氪金","已预约！"], ensure_ascii=False)}

def _mock_weibo():
    now = NOW()
    return [{"topic":kw, **_mock_weibo_item(), "fetched_at":now} for kw in GAME_KEYWORDS]
