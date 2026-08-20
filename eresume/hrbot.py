"""HR 消息互动：意图分类 + 角色扮演 / 回复草拟。

规则版：本地意图分类 + 组装提示词（LLM 可选增强）。
"""

from __future__ import annotations

import re

from . import llm
from .config import resolve_prompt
from .models import Profile, Preferences, Posting
from .salary import salary_display

INTENTS = [
    "面试邀请", "笔试邀请", "约时间沟通", "加微信", "薪资沟通",
    "简历背景询问", "到岗时间", "拒信", "已读不回跟进", "其他",
]

INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("面试邀请", ["面试", "面谈", "面聊", "interview", "到公司聊", "聊聊"]),
    ("笔试邀请", ["笔试", "测评", "测试链接", "线上测试", "assessment", "codility", "hackerrank"]),
    ("约时间沟通", ["方便", "什么时候有空", "约个时间", "时间方便", "几点", "schedule"]),
    ("加微信", ["加个微信", "微信聊", "加微信", "wechat", "vx"]),
    ("薪资沟通", ["薪资", "薪酬", "期望工资", "待遇", "salary", "package", "报价"]),
    ("简历背景询问", ["空窗", "离职原因", "为什么离开", "背景", "简历里", "项目经验", "gap"]),
    ("到岗时间", ["到岗", "入职时间", "什么时候能来", "onboard", "start date"]),
    ("拒信", ["遗憾", "不合适", "人才库", "感谢你的参与", "未能", "not moving forward"]),
    ("已读不回跟进", ["跟进", "进展", "状态", "process", "update"]),
]


def classify_intent(message: str) -> str:
    text = message.lower()
    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS:
        n = sum(1 for p in patterns if p.lower() in text)
        if n:
            scores[intent] = n
    if not scores:
        return "其他"
    return max(scores, key=scores.get)


def _posting_block(posting: Posting | None) -> str:
    if not posting:
        return "（未关联岗位——请用 `eresume job add` 添加后重试）"
    return (
        f"公司: {posting.company or '未知'} | 岗位: {posting.title or '未知'}\n"
        f"类型: {posting.employment_type or '未知'} | 薪资: {salary_display(posting)}\n"
        f"地点: {posting.location or '未知'}\n"
        f"描述: {(posting.description or '')[:1200]}"
    )


def _resume_block(profile: Profile) -> str:
    lines = [f"姓名: {profile.name or '(未填)'} | 城市: {profile.location or '-'} | 状态: {profile.status or '-'}"]
    if profile.education:
        lines.append("教育: " + "；".join(f"{e.get('degree','')} {e.get('major','')} @ {e.get('school','')}" for e in profile.education))
    if profile.experience:
        for e in profile.experience:
            lines.append(f"经历: {e.get('title','')} @ {e.get('company','')} ({e.get('years','')}) — " + "；".join(e.get("bullets", [])))
    if profile.skills_primary:
        lines.append("核心技能: " + ", ".join(profile.skills_primary))
    if profile.languages:
        lines.append("语言: " + "; ".join(f"{x.get('lang','')}({x.get('level','')})" for x in profile.languages))
    return "\n".join(lines)


def _prefs_block(prefs: Preferences) -> str:
    salary = f"{prefs.salary_monthly_min or '?'}-{prefs.salary_monthly_max or '?'} 元/月 (底线 {prefs.salary_floor or '未设'})"
    types = ", ".join(f"{c.get('type','')}" for c in prefs.company_types) or "未设置"
    return (
        f"期望类型: {prefs.employment_types or '未设置'} | 到岗: {prefs.start_availability or '未填'}\n"
        f"薪资: {salary}\n"
        f"公司类型优先级: {types} | 排除: {prefs.company_excludes or '无'}\n"
        f"加班接受度: {prefs.overtime_tolerance or '未填'} | 出差: {prefs.travel_tolerance or '未填'}"
    )


PROTOCOL = """谈判协议要点:
1. 问期望薪资时先推回（"想了解下这个岗位的预算范围？"）；必须报价时报期望区间上沿并说明依据
2. 收到报价：高于底线可接受→表达感谢，争取 1-2 项弹性项；低于期望但高于底线→给明确还价区间+理由；低于底线→礼貌说明差距
3. 一次只谈一件事；口头承诺要求邮件确认；不虚报其他 offer（可以说有流程在推进，但不编数字）
4. 潜力股/创业公司：期权要问清授予量、行权价、归属期(vesting)、离职处理
5. 到岗时间只承诺真实情况"""

CHANNEL_TONE = {
    "bosszhipin": "口语化、直接、简洁（BOSS直聘直聊风格）",
    "email": "正式、完整（邮件风格）",
    "wechat": "自然、简短（微信风格）",
    "default": "礼貌、专业、简洁",
}


def handle_roleplay(message: str, profile: Profile, prefs: Preferences, posting: Posting | None,
                    channel: str = "default", mode: str = "auto") -> str:
    intent = classify_intent(message)
    prompt = resolve_prompt("hr_roleplay.md").read_text(encoding="utf-8").format(
        company=posting.company if posting else "该公司",
        channel_tone=CHANNEL_TONE.get(channel, CHANNEL_TONE["default"]),
        hr_message=message,
        posting=_posting_block(posting),
        profile_resume=_resume_block(profile),
        preferences=_prefs_block(prefs),
    )
    fallback = llm.prompt_banner("HR 角色扮演") + prompt + "\n\n[意图判定: " + intent + "]"
    return llm.run(prompt, system="你是面试辅导教练，扮演HR角色进行角色扮演练习。", mode=mode, fallback=fallback)


def handle_draft(message: str, profile: Profile, prefs: Preferences, posting: Posting | None,
                 channel: str = "default", mode: str = "auto", n: int = 3) -> str:
    intent = classify_intent(message)
    prompt = resolve_prompt("hr_draft.md").read_text(encoding="utf-8").format(
        n=n, channel=channel, hr_message=message, intent=intent,
        posting=_posting_block(posting),
        profile_resume=_resume_block(profile),
        preferences=_prefs_block(prefs),
        protocol=PROTOCOL,
    )
    fallback = llm.prompt_banner(f"HR 回复草稿（意图: {intent}）") + prompt
    return llm.run(prompt, system="你是求职顾问，帮求职者起草给 HR 的回复。", mode=mode, fallback=fallback)


def analyze_message(message: str) -> str:
    """本地意图分析（无 LLM 也可用）。"""
    intent = classify_intent(message)
    goal = {
        "面试邀请": "确认时间/地点/形式；问清面试官与环节；表达期待",
        "笔试邀请": "确认收到；问截止时间；确认设备/形式要求",
        "约时间沟通": "快速给出 2-3 个可用时段，减少往返",
        "加微信": "同意并备注公司-岗位-姓名；保持礼貌",
        "薪资沟通": "按谈判协议处理：先推回让对方报价",
        "简历背景询问": "诚实、简洁、正面框架回答",
        "到岗时间": "按真实情况回答，不承诺做不到的",
        "拒信": "简短感谢 + 可选一句反馈请求",
        "已读不回跟进": "一次简短跟进，附上关键信息方便对方回忆",
        "其他": "按常识处理，拿不准就询问用户",
    }[intent]
    return f"意图判定：{intent}\n回复目标：{goal}"
