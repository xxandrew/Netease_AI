import os
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_twitch_top_games(limit=20):
    """通过 Twitch Helix API 获取热门游戏直播数据"""
    client_id = os.getenv("TWITCH_CLIENT_ID", "")
    access_token = os.getenv("TWITCH_ACCESS_TOKEN", "")
    if not client_id or not access_token:
        print("[Twitch] 未配置 TWITCH_CLIENT_ID / TWITCH_ACCESS_TOKEN，跳过")
        return _mock_twitch_data(limit)
    headers = {
        "Client-Id": client_id,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        resp = requests.get(
            "https://api.twitch.tv/helix/games/top",
            headers=headers,
            params={"first": limit},
            timeout=15,
        )
        resp.raise_for_status()
        games_data = resp.json().get("data", [])
        results = []
        for g in games_data:
            # 查询该游戏当前频道数和总观看量
            stream_resp = requests.get(
                "https://api.twitch.tv/helix/streams",
                headers=headers,
                params={"game_id": g["id"], "first": 100},
                timeout=10,
            )
            streams = stream_resp.json().get("data", []) if stream_resp.ok else []
            viewer_count = sum(s.get("viewer_count", 0) for s in streams)
            results.append({
                "name": g.get("name"),
                "game_id": g.get("id"),
                "viewer_count": viewer_count,
                "channel_count": len(streams),
            })
        return results
    except Exception as e:
        print(f"[Twitch] 爬取失败: {e}")
        return _mock_twitch_data(limit)

def _mock_twitch_data(limit=20):
    mock = [
        {"name": "League of Legends", "game_id": "21779", "viewer_count": 250000, "channel_count": 3200},
        {"name": "VALORANT", "game_id": "516575", "viewer_count": 180000, "channel_count": 2100},
        {"name": "Minecraft", "game_id": "27471", "viewer_count": 150000, "channel_count": 4500},
        {"name": "Fortnite", "game_id": "33214", "viewer_count": 120000, "channel_count": 1800},
        {"name": "Counter-Strike 2", "game_id": "32399", "viewer_count": 110000, "channel_count": 1500},
        {"name": "Apex Legends", "game_id": "511224", "viewer_count": 95000, "channel_count": 1200},
        {"name": "Dota 2", "game_id": "29595", "viewer_count": 85000, "channel_count": 900},
        {"name": "World of Warcraft", "game_id": "18122", "viewer_count": 70000, "channel_count": 750},
        {"name": "Overwatch 2", "game_id": "515025", "viewer_count": 60000, "channel_count": 700},
        {"name": "Hearthstone", "game_id": "138585", "viewer_count": 45000, "channel_count": 500},
    ]
    return mock[:limit]
