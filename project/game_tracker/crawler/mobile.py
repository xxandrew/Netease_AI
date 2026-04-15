import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

# App Store 各区 RSS 配置
APPSTORE_REGIONS = {
    "cn": {"code": "cn", "label": "中国", "flag": "🇨🇳"},
    "us": {"code": "us", "label": "美国", "flag": "🇺🇸"},
    "jp": {"code": "jp", "label": "日本", "flag": "🇯🇵"},
    "kr": {"code": "kr", "label": "韩国", "flag": "🇰🇷"},
}


def fetch_appstore_region(region_code: str, limit: int = 20) -> list:
    """爬取指定区域 App Store 免费游戏榜"""
    url = f"https://rss.applemarketingtools.com/api/v2/{region_code}/apps/top-free/{limit}/games.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("feed", {}).get("results", [])
        region_info = APPSTORE_REGIONS.get(region_code, {"label": region_code.upper(), "flag": ""})
        games = []
        for i, item in enumerate(results[:limit]):
            genres = item.get("genres", [])
            category = genres[0].get("name", "") if genres else ""
            games.append({
                "name": item.get("name", "Unknown"),
                "platform": "App Store",
                "region": region_info["label"],
                "region_code": region_code,
                "flag": region_info["flag"],
                "rank": i + 1,
                "category": category,
                "app_id": item.get("id", ""),
                "artwork": item.get("artworkUrl100", ""),
            })
        return games
    except Exception as e:
        print(f"[AppStore-{region_code}] 爬取失败: {e}")
        return _mock_appstore(region_code, limit)


def fetch_all_appstore(limit: int = 20) -> list:
    """爬取全部四个区域 App Store 数据"""
    all_games = []
    for code in APPSTORE_REGIONS:
        games = fetch_appstore_region(code, limit)
        all_games.extend(games)
    return all_games


def fetch_taptap_top(limit: int = 20) -> list:
    """爬取 TapTap 热门游戏榜（国内安卓）"""
    url = "https://www.taptap.cn/app-center/ranking/hot"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("div.app-list-item, div.rank-list-item, li.rank-item")
        games = []
        for i, item in enumerate(items[:limit]):
            name_tag = item.select_one(
                "span.app-name, div.app-name, .title, h3, p.name"
            )
            name = name_tag.get_text(strip=True) if name_tag else f"TapTap 游戏 #{i+1}"
            games.append({
                "name": name,
                "platform": "TapTap",
                "region": "中国",
                "region_code": "cn",
                "flag": "🇨🇳",
                "rank": i + 1,
                "category": "Game",
                "app_id": "",
                "artwork": "",
            })
        if not games:
            return _mock_taptap(limit)
        return games
    except Exception as e:
        print(f"[TapTap] 爬取失败: {e}")
        return _mock_taptap(limit)


# ── Mock 数据（备用） ──────────────────────────────────────────────

def _mock_appstore(region_code: str, limit: int = 10) -> list:
    region_info = APPSTORE_REGIONS.get(region_code, {"label": region_code.upper(), "flag": ""})
    data = {
        "cn": ["王者荣耀", "和平精英", "原神", "部落冲突", "明日方舟",
               "金铲铲之战", "蛋仔派对", "逆水寒手游", "航海王热血航线", "三国志战略版"],
        "us": ["Roblox", "PUBG Mobile", "Genshin Impact", "Clash of Clans",
               "Candy Crush Saga", "Pokémon GO", "Subway Surfers",
               "Among Us", "Call of Duty Mobile", "Garena Free Fire"],
        "jp": ["モンスターストライク", "プロスピA", "ウマ娘", "パズル&ドラゴンズ",
               "ドラゴンクエストウォーク", "グランブルーファンタジー",
               "アークナイツ", "FGO", "荒野行動", "ポケモンGO"],
        "kr": ["리니지M", "오딘: 발할라 라이징", "바람의나라: 연", "카트라이더 러쉬플러스",
               "검은사막 모바일", "뮤 아크엔젤", "리니지W", "세븐나이츠2",
               "쿠키런: 킹덤", "브롤스타즈"],
    }
    names = data.get(region_code, [f"Game #{i+1}" for i in range(10)])
    return [
        {"name": n, "platform": "App Store", "region": region_info["label"],
         "region_code": region_code, "flag": region_info["flag"],
         "rank": i + 1, "category": "Game", "app_id": "", "artwork": ""}
        for i, n in enumerate(names[:limit])
    ]


def _mock_taptap(limit: int = 10) -> list:
    names = ["原神", "王者荣耀", "和平精英", "明日方舟", "蛋仔派对",
             "金铲铲之战", "逆水寒手游", "崩坏：星穹铁道", "英雄联盟手游", "三国志战略版"]
    return [
        {"name": n, "platform": "TapTap", "region": "中国", "region_code": "cn",
         "flag": "🇨🇳", "rank": i + 1, "category": "Game", "app_id": "", "artwork": ""}
        for i, n in enumerate(names[:limit])
    ]