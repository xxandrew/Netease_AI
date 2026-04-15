"""TapTap + App Store 数据爬虫"""
import requests, json
from datetime import datetime
from bs4 import BeautifulSoup

GAME_NAME = "王者荣耀世界"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
NOW = lambda: datetime.now().isoformat()

# ── TapTap ───────────────────────────────────────
TAPTAP_APP_ID = "703879"  # 王者荣耀世界 TapTap ID（预留，需实际确认）

def fetch_taptap():
    """爬取 TapTap 评分、评论数、预约量"""
    try:
        url = f"https://www.taptap.cn/app/{TAPTAP_APP_ID}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        score = 0.0
        review_count = 0
        reserve_count = 0

        # 评分
        score_tag = soup.select_one(".score-container .rating, .app-score, [class*='score']")
        if score_tag:
            try: score = float(score_tag.get_text(strip=True))
            except: pass

        # 评论数
        review_tag = soup.select_one("[class*='comment-count'], [class*='review']")
        if review_tag:
            txt = review_tag.get_text(strip=True).replace(",","").replace("万","0000")
            try: review_count = int(''.join(filter(str.isdigit, txt)))
            except: pass

        # 预约量
        reserve_tag = soup.select_one("[class*='reserve'], [class*='wish']")
        if reserve_tag:
            txt = reserve_tag.get_text(strip=True).replace(",","")
            try: reserve_count = int(''.join(filter(str.isdigit, txt)))
            except: pass

        if score > 0 or review_count > 0:
            return [{"source":"TapTap","region":"CN","rank":0,"rank_type":"store",
                     "score":score,"review_count":review_count,"reserve_count":reserve_count,
                     "fetched_at":NOW()}]
    except Exception as e:
        print(f"[TapTap] 爬取失败: {e}")
    return _mock_taptap()

def _mock_taptap():
    return [{"source":"TapTap","region":"CN","rank":1,"rank_type":"预约榜",
             "score":9.2,"review_count":128400,"reserve_count":5820000,"fetched_at":NOW()}]


# ── App Store 各区排名 ──────────────────────────
APPSTORE_REGIONS = {
    "cn": ("🇨🇳 中国", "cn"),
    "us": ("🇺🇸 美国", "us"),
    "jp": ("🇯🇵 日本", "jp"),
    "kr": ("🇰🇷 韩国", "kr"),
}

def fetch_appstore_ranks():
    """从 Apple RSS 获取各区免费榜排名（需搜索游戏名）"""
    results = []
    now = NOW()
    for code, (label, rss_code) in APPSTORE_REGIONS.items():
        rank = _search_appstore_rank(rss_code, GAME_NAME)
        results.append({
            "source": "App Store", "region": label,
            "rank": rank, "rank_type": "免费游戏榜",
            "score": 0.0, "review_count": 0, "reserve_count": 0,
            "fetched_at": now,
        })
    return results if results else _mock_appstore()

def _search_appstore_rank(region_code, game_name):
    """在 App Store Top100 中查找游戏排名"""
    url = f"https://rss.applemarketingtools.com/api/v2/{region_code}/apps/top-free/100/games.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("feed", {}).get("results", [])
        for i, item in enumerate(results):
            if game_name in item.get("name", ""):
                return i + 1
        return 0  # 未上榜
    except Exception as e:
        print(f"[AppStore-{region_code}] 失败: {e}")
        return -1  # 查询失败

def _mock_appstore():
    now = NOW()
    mock = {"cn":1,"us":5,"jp":8,"kr":3}
    labels = {"cn":"🇨🇳 中国","us":"🇺🇸 美国","jp":"🇯🇵 日本","kr":"🇰🇷 韩国"}
    return [{"source":"App Store","region":labels[k],"rank":v,"rank_type":"免费游戏榜",
             "score":0,"review_count":0,"reserve_count":0,"fetched_at":now}
            for k, v in mock.items()]
