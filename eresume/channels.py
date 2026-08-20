"""投递渠道：目录 + 速查 + 组合计划。"""

from __future__ import annotations

import json

from .config import resolve_channels_data
from .models import Preferences
from .storage import list_applications

CHANNEL_ALIAS = {
    "bosszhipin": "bosszhipin", "boss": "bosszhipin", "直聘": "bosszhipin",
    "zhilian": "zhilian", "智联": "zhilian",
    "51job": "51job", "前程无忧": "51job",
    "lagou": "lagou", "拉勾": "lagou",
    "liepin": "liepin", "猎聘": "liepin",
    "shixiseng": "shixiseng", "实习僧": "shixiseng",
    "nowcoder": "nowcoder", "牛客": "nowcoder", "牛客职": "nowcoder",
    "referral": "referral", "内推": "referral",
    "niche": "niche-direct", "官网直投": "niche-direct", "小众": "niche-direct",
    "soe": "soe", "国企": "soe", "央企": "soe", "国聘": "soe",
    "outsourcing": "outsourcing", "外包": "outsourcing",
    "mnc": "mnc-careers", "外企官网": "mnc-careers", "外企": "mnc-careers",
    "careers": "careers-page", "官网": "careers-page",
    "campus": "campus-event", "宣讲会": "campus-event",
    "linkedin": "linkedin",
    "headhunter": "headhunter", "猎头": "headhunter",
    "tech": "tech-community", "社区": "tech-community",
}


def load_channels() -> dict:
    with open(resolve_channels_data(), encoding="utf-8") as f:
        return json.load(f)


def all_channels() -> list[dict]:
    return load_channels()["channels"]


def find_channel(name: str) -> dict | None:
    key = CHANNEL_ALIAS.get(name.strip().lower(), name.strip().lower())
    for c in all_channels():
        if c["id"] == key or name.strip() in (c["name"], c["id"]):
            return c
    return None


def cheat_sheet() -> str:
    lines = ["\n═══ 投递渠道速查 ═══", ""]
    lines.append(f"{'渠道':<10}{'适合':<28}{'优势'}")
    for c in all_channels():
        lines.append(f"{c['name']:<12}{c['best_for'][:26]:<30}{'、'.join(c['pros'][:2])}")
    lines.append("\n详细攻略: `eresume channels <渠道名>`，如 `eresume channels 内推`")
    return "\n".join(lines)


def detail(name: str) -> str:
    c = find_channel(name)
    if not c:
        return f"未找到渠道「{name}」。可用: {', '.join(x['name'] for x in all_channels())}"
    lines = [
        f"\n═══ {c['name']} ═══",
        f"官方入口: {c.get('url') or c.get('campus_url') or c.get('app_url') or '（见 tips）'}",
        f"适合: {c['best_for']}",
        f"优势: {'、'.join(c['pros'])}",
        f"劣势/风险: {'、'.join(c['cons'])}" if c["cons"] else "",
        f"要点: {'；'.join(c['tips'])}",
    ]
    if c.get("risk"):
        lines.append(f"注意: {c['risk']}")
    return "\n".join(x for x in lines if x)


def recommend(prefs: Preferences) -> str:
    """按求职者状态推荐渠道组合。"""
    mix = load_channels()["mix"]
    stage = prefs.career_stage or ""
    status = prefs.status or ""
    scenario = "应届生校招" if ("应届" in status or "校招" in stage) else "社招技术岗"
    if "实习" in prefs.employment_types:
        scenario = "实习"
    elif prefs.career_stage == "成熟期" or "管理" in "".join(prefs.growth_priorities):
        scenario = "中高端/管理"
    elif "外企" in [c.get("type") for c in prefs.company_types]:
        scenario = "外企"
    elif "国企" in [c.get("type") for c in prefs.company_types] or "国企央企" in [c.get("type") for c in prefs.company_types]:
        scenario = "国企/央企"
    elif "潜力股" in [c.get("type") for c in prefs.company_types]:
        scenario = "潜力股/创业公司"
    elif "小而美" in [c.get("type") for c in prefs.company_types]:
        scenario = "小而美/细分行业"

    row = next((r for r in mix if r["scenario"] == scenario), mix[1])
    lines = [f"\n═══ 渠道组合建议（{scenario}）═══", "推荐组合: " + " > ".join(row["mix"])]

    # 结合真实转化数据
    apps = list_applications()
    if apps:
        from collections import Counter
        cnt = Counter(a.channel for a in apps if a.channel)
        if cnt:
            lines.append("你的历史渠道分布: " + ", ".join(f"{k}×{v}" for k, v in cnt.most_common()))
            best = cnt.most_common(1)[0][0]
            lines.append(f"提示: 「{best}」是你转化记录最多的渠道，保持为主渠道。")
    return "\n".join(lines)


def weekly_plan(prefs: Preferences) -> str:
    """生成本周投递计划模板。"""
    rec = recommend(prefs)
    lines = [
        rec,
        "",
        "═══ 本周投递计划（模板）═══",
        "| 渠道 | 本周动作 | 数量 | 验收标准 |",
        "|------|----------|------|----------|",
        "| BOSS直聘 | 完善在线简历，直聊目标公司HR | 5家/天 | 3次以上对话 |",
        "| 内推 | 脉脉联系2位校友 + 牛客找3个内推帖 | 5 | 2个内推回复 |",
        "| 官网 | 投递3家目标公司官网岗位 | 3 | 3封已投递 |",
        "",
        "跟进规则: 已读不回 2-3 个工作日后跟进一次（最多一次）；面试后 24h 内发感谢信。",
    ]
    return "\n".join(lines)
