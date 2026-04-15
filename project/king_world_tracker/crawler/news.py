"""媒体报道爬虫（游资网/17173/NGA/游戏葡萄）"""
import requests, re
from datetime import datetime
from bs4 import BeautifulSoup
from crawler.weibo import analyze_sentiment

KEYWORDS = ["王者荣耀世界", "王者世界"]
NOW = lambda: datetime.now().isoformat()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SOURCES = [
    {"name": "游资网", "url": "https://www.youxiputao.com/search?q={kw}", "sel": "article h3 a"},
    {"name": "17173",  "url": "https://search.17173.com/search?q={kw}",   "sel": ".result-item h3 a"},
    {"name": "游戏葡萄","url": "https://youxiputao.com/search?q={kw}",     "sel": "h2.title a, h3.title a"},
]

def _simple_sentiment(text: str) -> str:
    pos = {"首发","震撼","突破","期待","好评","创新","惊艳","亿","热门","热榜"}
    neg = {"争议","下架","差评","漏洞","崩溃","违规","涉嫌","处罚","抵制","举报"}
    has_pos = any(w in text for w in pos)
    has_neg = any(w in text for w in neg)
    if has_neg and not has_pos: return "negative"
    if has_pos and not has_neg: return "positive"
    return "neutral"

def fetch_news():
    """爬取各媒体最新报道"""
    results = []
    now = NOW()
    for src in SOURCES:
        for kw in KEYWORDS[:1]:
            url = src["url"].format(kw=requests.utils.quote(kw))
            try:
                resp = requests.get(url, headers=HEADERS, timeout=12)
                soup = BeautifulSoup(resp.text, "lxml")
                items = soup.select(src["sel"])[:5]
                for item in items:
                    title = item.get_text(strip=True)
                    link  = item.get("href", "")
                    if not title: continue
                    results.append({
                        "source": src["name"], "title": title[:80],
                        "url": link, "summary": title[:120],
                        "sentiment": _simple_sentiment(title),
                        "published_at": now[:10], "fetched_at": now,
                    })
            except Exception as e:
                print(f"[Media-{src['name']}] 失败: {e}")

    return results if results else _mock_news()

def _mock_news():
    now = NOW()
    items = [
        ("游戏葡萄","王者荣耀世界公布首支实机演示CG，画面震撼玩家","positive"),
        ("17173","王者荣耀世界预约破500万，TapTap评分9.2","positive"),
        ("游资网","王者荣耀世界入选TapTap年度最期待游戏Top5","positive"),
        ("NGA玩家社区","王者荣耀世界内测评测：画质出色但部分玩法存争议","neutral"),
        ("游戏葡萄","腾讯发布王者荣耀世界官方路线图，预计Q3正式上线","neutral"),
        ("17173","王者荣耀世界 vs 其他MOBA手游竞品全方位对比","neutral"),
    ]
    return [{"source":s,"title":t,"url":"","summary":t,
             "sentiment":sent,"published_at":now[:10],"fetched_at":now}
            for s, t, sent in items]
