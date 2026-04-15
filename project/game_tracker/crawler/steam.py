import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

STEAM_REGIONS = {
    "global": {"label": "全球", "flag": "🌍"},
    "cn":     {"label": "中国", "flag": "🇨🇳"},
    "us":     {"label": "美国", "flag": "🇺🇸"},
    "jp":     {"label": "日本", "flag": "🇯🇵"},
    "kr":     {"label": "韩国", "flag": "🇰🇷"},
}


# ── 全球：SteamSpy Top 50 (含在线人数) ─────────────────────────────

def fetch_steamspy_global(limit=50):
    url = "https://steamspy.com/api.php?request=top100in2weeks"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        games = []
        for i, (app_id, info) in enumerate(data.items()):
            if i >= limit:
                break
            games.append({
                "name": info.get("name", "Unknown"),
                "app_id": app_id,
                "current_players": info.get("ccu", 0),
                "peak_players": info.get("peak_ccu", 0),
                "positive_reviews": info.get("positive", 0),
                "negative_reviews": info.get("negative", 0),
                "price": str(info.get("price", "")),
                "tags": ", ".join(list(info.get("tags", {}).keys())[:5]),
                "rank": i + 1,
                "region_code": "global",
                "region": "全球",
                "flag": "🌍",
            })
        return games
    except Exception as e:
        print(f"[SteamSpy-Global] 爬取失败: {e}")
        return _mock_steam("global", limit)


# ── 各区：Steam 官方 Top Sellers ────────────────────────────────────

def fetch_steam_region(region_code: str, limit=50):
    """爬取 Steam 官方各区 Top Sellers"""
    url = f"https://store.steampowered.com/charts/topselling/?cc={region_code}"
    info = STEAM_REGIONS.get(region_code, {"label": region_code.upper(), "flag": ""})
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("tr.weeklytopsellers_TableRow__3yf6e, tr[class*='TableRow']")
        if not rows:
            # 备用选择器
            rows = soup.select("table tbody tr")
        games = []
        for i, row in enumerate(rows[:limit]):
            cols = row.select("td")
            if len(cols) < 2:
                continue
            name_tag = row.select_one("div[class*='GameName'], .gameLink, td:nth-child(2) a, td:nth-child(2)")
            name = name_tag.get_text(strip=True) if name_tag else f"Game #{i+1}"
            if not name or name.isdigit():
                continue
            games.append({
                "name": name,
                "app_id": "",
                "current_players": 0,
                "peak_players": 0,
                "positive_reviews": 0,
                "negative_reviews": 0,
                "price": "",
                "tags": "",
                "rank": i + 1,
                "region_code": region_code,
                "region": info["label"],
                "flag": info["flag"],
            })
        if len(games) < 5:
            print(f"[Steam-{region_code}] 页面解析不足，使用模拟数据")
            return _mock_steam(region_code, limit)
        return games
    except Exception as e:
        print(f"[Steam-{region_code}] 爬取失败: {e}")
        return _mock_steam(region_code, limit)


def fetch_all_steam_regions(limit=50):
    """爬取全部五个区域（全球 + 四个地区）"""
    all_games = fetch_steamspy_global(limit)
    for code in ["cn", "us", "jp", "kr"]:
        games = fetch_steam_region(code, limit)
        all_games.extend(games)
    return all_games


# ── Mock 数据 ────────────────────────────────────────────────────────

_MOCK_NAMES = {
    "global": [
        "Counter-Strike 2", "Dota 2", "PUBG: BATTLEGROUNDS", "Apex Legends",
        "Rust", "Elden Ring", "Cyberpunk 2077", "GTA V", "Terraria",
        "Team Fortress 2", "Baldur's Gate 3", "Palworld", "Valheim",
        "Red Dead Redemption 2", "Monster Hunter: World", "Destiny 2",
        "Path of Exile", "Warframe", "Rainbow Six Siege", "Hollow Knight",
        "Stardew Valley", "Among Us", "Hades", "Celeste", "Dead by Daylight",
        "The Witcher 3", "Sekiro", "Dark Souls III", "FIFA 23", "NBA 2K24",
        "Rocket League", "Fall Guys", "Forza Horizon 5", "Subnautica",
        "No Man's Sky", "Satisfactory", "Deep Rock Galactic", "Escape from Tarkov",
        "Sea of Thieves", "Horizon Zero Dawn", "Divinity Original Sin 2",
        "Crusader Kings III", "Victoria 3", "Cities Skylines", "Factorio",
        "Portal 2", "Left 4 Dead 2", "Half-Life: Alyx", "Black Mesa", "Garry's Mod",
    ],
    "cn": [
        "绝地求生", "英雄联盟", "原神", "逆水寒", "完美世界",
        "天涯明月刀", "幻塔", "CS2", "Dota 2", "Rust",
        "艾尔登法环", "赛博朋克2077", "黑神话：悟空", "霓虹深渊：无限",
        "重生之门", "Palworld", "鬼谷八荒", "太吾绘卷", "了不起的修仙模拟器",
        "戴森球计划", "雨中冒险2", "杀戮尖塔", "死亡细胞", "哈迪斯",
        "空洞骑士", "星露谷物语", "炉石传说", "暗黑破坏神IV", "魔兽世界",
        "永劫无间", "天命奇御二", "侠客风云传", "烟火", "港诡实录",
        "Terraria", "泰拉瑞亚", "饥荒联机版", "绿色地狱", "森林之子",
        "胡闹厨房2", "双人成行", "It Takes Two", "分手厨房", "仙剑奇侠传七",
        "轩辕剑七", "古剑奇谭三", "三国：全面战争", "骑马与砍杀2", "帝国时代4",
    ],
    "us": [
        "Counter-Strike 2", "Baldur's Gate 3", "Palworld", "Elden Ring",
        "Hogwarts Legacy", "Cyberpunk 2077", "Red Dead Redemption 2",
        "GTA V", "Stardew Valley", "Hades", "Hollow Knight", "Terraria",
        "Rust", "Apex Legends", "PUBG", "Valheim", "Satisfactory",
        "Deep Rock Galactic", "No Man's Sky", "Sea of Thieves",
        "Horizon Zero Dawn", "The Witcher 3", "Sekiro", "Dark Souls III",
        "Divinity Original Sin 2", "Crusader Kings III", "Factorio",
        "Portal 2", "Left 4 Dead 2", "Garry's Mod", "Team Fortress 2",
        "Dota 2", "Path of Exile", "Warframe", "Rainbow Six Siege",
        "Dead by Daylight", "Among Us", "Fall Guys", "Rocket League",
        "Forza Horizon 5", "Celeste", "Subnautica", "Monster Hunter: World",
        "Destiny 2", "Escape from Tarkov", "Victoria 3", "Cities Skylines",
        "Half-Life: Alyx", "Black Mesa", "Disco Elysium",
    ],
    "jp": [
        "モンスターハンターワイルズ", "ファイナルファンタジーXIV", "エルデンリング",
        "ドラゴンズドグマ2", "スト6", "鉄拳8", "SEKIRO", "ダークソウルIII",
        "サイバーパンク2077", "バルダーズゲート3", "デビルメイクライ5",
        "バイオハザードRE:4", "デビルメイクライ5", "ゴーストオブツシマ",
        "テイルズオブアライズ", "ブルプロ", "PSO2NGS", "マビノギ",
        "信長の野望", "三国志14", "Winning Post", "ウマ娘",
        "Among Us", "Stardew Valley", "Terraria", "Rust", "Valheim",
        "Counter-Strike 2", "Dota 2", "Apex Legends", "PUBG",
        "Warframe", "Path of Exile", "Dead by Daylight", "Fall Guys",
        "Rocket League", "Forza Horizon 5", "No Man's Sky", "Satisfactory",
        "Deep Rock Galactic", "Hades", "Hollow Knight", "Celeste",
        "Divinity Original Sin 2", "Factorio", "Cities Skylines",
        "Portal 2", "Left 4 Dead 2", "Half-Life: Alyx", "GTA V",
    ],
    "kr": [
        "배틀그라운드", "리그 오브 레전드", "오버워치2", "디아블로IV",
        "월드 오브 워크래프트", "스타크래프트II", "카트라이더 드리프트",
        "Elden Ring", "사이버펑크2077", "발더스 게이트3",
        "로스트아크", "메이플스토리", "던전앤파이터", "블레이드앤소울",
        "테라", "아키에이지", "리니지2M", "검은사막", "엘리온",
        "Counter-Strike 2", "Dota 2", "Apex Legends", "Rust",
        "Valheim", "Terraria", "Stardew Valley", "Among Us",
        "Fall Guys", "Rocket League", "Dead by Daylight", "PUBG",
        "Warframe", "Path of Exile", "No Man's Sky", "Satisfactory",
        "Deep Rock Galactic", "Hades", "Hollow Knight", "Celeste",
        "Divinity Original Sin 2", "Factorio", "Cities Skylines",
        "Portal 2", "Left 4 Dead 2", "GTA V", "The Witcher 3",
        "Sekiro", "Dark Souls III", "Monster Hunter: World",
    ],
}


def _mock_steam(region_code: str, limit=50):
    info = STEAM_REGIONS.get(region_code, {"label": region_code.upper(), "flag": ""})
    names = _MOCK_NAMES.get(region_code, _MOCK_NAMES["global"])
    return [
        {
            "name": n,
            "app_id": "",
            "current_players": max(0, 500000 - i * 9000) if region_code == "global" else 0,
            "peak_players": max(0, 800000 - i * 14000) if region_code == "global" else 0,
            "positive_reviews": 0,
            "negative_reviews": 0,
            "price": "",
            "tags": "",
            "rank": i + 1,
            "region_code": region_code,
            "region": info["label"],
            "flag": info["flag"],
        }
        for i, n in enumerate(names[:limit])
    ]