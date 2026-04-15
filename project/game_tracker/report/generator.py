import os
from openai import OpenAI
from database import db

def _build_summary(steam, twitch, mobile):
    steam_top5 = "\n".join(
        f"  {i+1}. {g['name']} - 在线:{g['current_players']:,} 峰值:{g['peak_players']:,}"
        for i, g in enumerate(steam[:5])
    )
    twitch_top5 = "\n".join(
        f"  {i+1}. {g['name']} - 观看:{g['viewer_count']:,} 频道:{g['channel_count']}"
        for i, g in enumerate(twitch[:5])
    )
    mobile_top5 = "\n".join(
        f"  {g['rank']}. [{g['platform']}] {g['name']}"
        for g in mobile[:5]
    )
    return f"""【Steam 热门游戏（实时在线）】\n{steam_top5}\n\n【Twitch 热门游戏（直播热度）】\n{twitch_top5}\n\n【手游榜单 Top5】\n{mobile_top5}"""

def generate_report(report_type: str = "daily") -> str:
    steam = db.get_latest_steam(10)
    twitch = db.get_latest_twitch(10)
    mobile = db.get_latest_mobile(10)

    summary = _build_summary(steam, twitch, mobile)

    period = "今日" if report_type == "daily" else "本周"
    prompt = f"""你是一名专业的游戏行业数据分析师，请根据以下{period}多平台游戏数据，生成一份{period}游戏数据报告。

数据如下：
{summary}

报告要求：
1. 简明扼要总结各平台热门趋势
2. 指出值得关注的异常或亮点（如某游戏热度暴涨/暴跌）
3. 给出 2~3 条对游戏运营或选品的参考建议
4. 报告风格专业简洁，使用 Markdown 格式输出
"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # 无 API Key 时返回简单汇总
        content = f"## {period}游戏数据汇总（未配置 OpenAI Key，仅展示原始数据）\n\n```\n{summary}\n```"
        db.save_report(report_type, content)
        return content

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        db.save_report(report_type, content)
        return content
    except Exception as e:
        fallback = f"## AI 报告生成失败\n\n错误：{e}\n\n原始数据：\n```\n{summary}\n```"
        db.save_report(report_type, fallback)
        return fallback
