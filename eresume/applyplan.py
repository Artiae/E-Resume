"""投递助手：一键打开各渠道搜索页（预填关键词/城市）+ 粘贴即用的话术。

为什么不做全自动投递？
- 国内主流平台（BOSS直聘/智联/51job 等）有登录墙、验证码与强反爬，
  自动化操作违反平台条款且极易封号
- 自动替用户回复 HR 有说错话/泄露信息的风险
因此这里采用安全可靠的半自动方案：
  打开已预填好的搜索页 → 复制话术 → 人工确认投递 → 记录到 tracker
"""

from __future__ import annotations

import urllib.parse

from .models import Profile, Preferences

# 主要城市 -> BOSS直聘 city code（用于预填；未知城市时省略该参数）
ZHIPIN_CITY_CODES = {
    "北京": "101010100", "上海": "101020100", "广州": "101280100", "深圳": "101280600",
    "杭州": "101210100", "成都": "101270100", "南京": "101190100", "武汉": "101200100",
    "西安": "101110100", "苏州": "101190400", "天津": "101030100", "重庆": "101040100",
    "长沙": "101250100", "郑州": "101180100", "青岛": "101120200", "厦门": "101230200",
    "合肥": "101220100", "济南": "101120100", "大连": "101070200", "东莞": "101281600",
}


def _q(keyword: str) -> str:
    return urllib.parse.quote(keyword.strip())


def _c(city: str) -> str:
    return urllib.parse.quote(city.strip())


def build_url(channel_id: str, keyword: str, city: str = "") -> str:
    """为某渠道构造预填搜索 URL。"""
    kw = _q(keyword)
    c = _c(city)
    if channel_id == "bosszhipin":
        code = ZHIPIN_CITY_CODES.get(city.strip(), "")
        city_part = f"&city={code}" if code else ""
        return f"https://www.zhipin.com/web/geek/job?query={kw}{city_part}"
    if channel_id == "zhilian":
        jl = f"&jl={c}" if c else ""
        return f"https://sou.zhaopin.com/?kw={kw}{jl}"
    if channel_id == "51job":
        return f"https://we.51job.com/pc/search?keyword={kw}&searchType=2&sortType=0"
    if channel_id == "lagou":
        return f"https://www.lagou.com/zhaopin/{kw}/"
    if channel_id == "liepin":
        return f"https://www.liepin.com/zhaopin/?key={kw}"
    if channel_id == "shixiseng":
        city_part = f"&city={c}" if c else ""
        return f"https://www.shixiseng.com/interns?keyword={kw}{city_part}"
    if channel_id == "nowcoder":
        return f"https://www.nowcoder.com/job/center?query={kw}"
    if channel_id == "soe":
        return f"https://www.iguopin.com/"
    if channel_id == "linkedin":
        return f"https://www.linkedin.com/jobs/search/?keywords={kw}"
    if channel_id == "liepin-x":
        return f"https://www.liepin.com/zhaopin/?key={kw}"
    raise ValueError(f"未知渠道: {channel_id}")


# 各渠道的打招呼/投递话术模板（{} 填充: 姓名/技能/岗位）
GREETINGS: dict[str, str] = {
    "bosszhipin": "您好！我是{name}，{status}，擅长{skills}。看到贵司在招「{role}」，我的背景与岗位匹配度较高，方便进一步沟通吗？",
    "zhilian": "您好，我是{name}，{status}，主要技能：{skills}。对贵司「{role}」岗位很感兴趣，已投递简历，期待与您沟通。",
    "51job": "尊敬的HR您好，我是{name}，{status}，擅长{skills}。应聘「{role}」岗位，简历已投递，期待面试机会。",
    "lagou": "您好！我是{name}，{status}，技能：{skills}。看到「{role}」岗位，与我的经历很契合，希望进一步沟通。",
    "liepin": "您好，我是{name}，{status}，关注「{role}」方向，技能：{skills}。期待有机会交流。",
    "shixiseng": "您好，我是{name}，{status}，擅长{skills}。对「{role}」实习岗位很感兴趣，每周可到岗{days}天，期待沟通！",
    "nowcoder": "您好，我是{name}，{status}，技能：{skills}。投递「{role}」，感谢关注！",
    "referral": "学长/学姐您好！我是{name}（{school}），正在找{role}方向的工作，擅长{skills}。方便的话能否内推一下？简历可以发您，非常感谢！",
    "soe": "尊敬的老师您好，我是{name}，{status}，应聘「{role}」岗位。简历已投递，期待有机会加入贵单位。",
}


def build_greeting(profile: Profile, role: str, channel_id: str = "bosszhipin") -> str:
    tpl = GREETINGS.get(channel_id, GREETINGS["bosszhipin"])
    name = profile.name or "【姓名】"
    status = profile.status or "求职者"
    skills = "、".join(profile.skills_primary[:3]) or "【核心技能】"
    school = profile.education[0].get("school", "") if profile.education else ""
    days = f"，每周可到岗{profile.internship_days_per_week}天" if getattr(profile, "internship_days_per_week", 0) else ""
    greeting = tpl.format(name=name, status=status, skills=skills, role=role, school=school, days=days)
    # 清理未填充的残留占位（如「每周可到岗天」）
    return greeting.replace("每周可到岗天", "")


def pick_channels(prefs: Preferences) -> list[str]:
    """按偏好选投递渠道（与 channels 推荐一致）。"""
    types = [c.get("type", "") for c in prefs.company_types]
    channels = ["bosszhipin"]
    if "实习" in prefs.employment_types:
        channels = ["shixiseng", "nowcoder"]
    elif "国企" in types or "国企央企" in types:
        channels = ["soe", "zhilian"]
    elif "外企" in types:
        channels = ["linkedin", "bosszhipin"]
    elif "小而美" in types or "潜力股" in types:
        channels = ["bosszhipin", "liepin"]
    else:
        channels = ["bosszhipin", "zhilian"]
    return channels


def build_plan(profile: Profile, prefs: Preferences) -> str:
    """生成今日投递计划：渠道 -> 预填 URL -> 话术。"""
    roles = profile.target_roles or ["【目标岗位】"]
    city = prefs.cities[0] if prefs.cities else ""
    channels = pick_channels(prefs)

    lines = ["\n═══ 今日投递计划（半自动） ═══", ""]
    lines.append("用法：复制下面的链接到浏览器打开（或运行 `eresume apply --open` 自动打开），")
    lines.append("复制话术粘贴到平台聊天框，确认后投递，最后 `eresume apps add` 记录。\n")

    for ch in channels:
        url = build_url(ch, roles[0], city)
        lines.append(f"▶ {ch}  |  {url}")
    lines.append("")
    lines.append("【粘贴即用话术】")
    for ch in channels:
        greeting = build_greeting(profile, roles[0], ch)
        lines.append(f"  [{ch}] {greeting}")
    lines.append("")
    lines.append("投递后记录: `eresume apps add <公司> \"<岗位>\" --channel <渠道> --score <匹配分>`")
    lines.append("进度体检:   `eresume next`")
    return "\n".join(lines)


def open_urls(urls: list[str]) -> None:
    """打开默认浏览器（Windows 为 Edge）。"""
    import webbrowser
    for u in urls:
        try:
            webbrowser.open(u)
        except Exception:
            pass
