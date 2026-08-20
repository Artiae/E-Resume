"""求职策略建议：定位、期望校准、渠道组合、行动计划。"""

from __future__ import annotations

from . import llm
from .config import resolve_prompt
from .models import Profile, Preferences
from .storage import list_applications
from .channels import recommend, weekly_plan


def _profile_block(profile: Profile) -> str:
    lines = [
        f"姓名: {profile.name or '(未填)'} | 城市: {profile.location or '-'} | 状态: {profile.status or '-'}",
        f"目标岗位: {', '.join(profile.target_roles) or '未设置'}",
        f"核心技能: {', '.join(profile.skills_primary) or '-'}",
        f"次要技能: {', '.join(profile.skills_secondary) or '-'}",
        f"职业目标: {', '.join(profile.career_goals) or '-'}",
    ]
    for e in profile.experience:
        lines.append(f"经历: {e.get('title','')} @ {e.get('company','')} ({e.get('years','')})")
    for p in profile.projects:
        lines.append(f"项目: {p}")
    return "\n".join(lines)


def _apps_block() -> str:
    apps = list_applications()
    if not apps:
        return "（暂无投递记录）"
    lines = []
    for a in apps:
        lines.append(f"{a.date} | {a.company} | {a.role} | 渠道:{a.channel or '-'} | 状态:{a.status} | 评分:{a.fit_score or '-'}")
        for n in a.notes:
            lines.append(f"    - {n}")
    return "\n".join(lines)


def run_advice(profile: Profile, prefs: Preferences, section: str = "", mode: str = "auto") -> str:
    prompt = resolve_prompt("advice.md").read_text(encoding="utf-8").format(
        profile=_profile_block(profile),
        preferences=prefs.to_dict(),
        applications=_apps_block(),
        channels="、".join(c["name"] for c in __import__("eresume.channels", fromlist=["all_channels"]).all_channels()),
    )
    if section:
        prompt += f"\n\n本次只输出第 {section} 部分（定位分析/期望校准/渠道组合/行动计划/技能差距）。"
    fallback = llm.prompt_banner("求职策略建议") + prompt
    return llm.run(prompt, system="你是资深的求职顾问，建议要诚实、具体、可执行。", mode=mode, fallback=fallback)


def quick_checks(profile: Profile, prefs: Preferences) -> str:
    """无 LLM 也能用的本地检查项。"""
    lines = ["\n═══ 本地快速体检 ═══"]
    if not profile.name:
        lines.append("  ⚠ 档案未填写姓名——运行 `eresume profile` 建档")
    if not prefs.employment_types:
        lines.append("  ⚠ 未设置期望雇佣类型——`eresume prefs --section employment`")
    if not prefs.salary_floor and not prefs.salary_monthly_min:
        lines.append("  ⚠ 未设置薪资底线——`eresume prefs --section salary`")
    if not prefs.company_types:
        lines.append("  ⚠ 未设置公司类型偏好——`eresume prefs --section company`")
    if not lines[1:]:
        lines.append("  ✅ 档案与偏好已齐备")
    lines.append("")
    return "\n".join(lines)


def next_steps(profile: Profile, prefs: Preferences) -> str:
    """进度体检 + 下一步建议（回答"我该干什么"）。"""
    from .storage import list_postings, list_applications

    postings = list_postings()
    apps = list_applications()
    lines = ["\n═══ 你的求职进度 ═══", ""]

    # 档案
    profile_done = bool(profile.name and profile.skills_primary)
    lines.append("【1. 简历档案】" + ("✅ 已完成" if profile_done else "⚠️ 未完成"))
    if not profile_done:
        lines.append("    下一步: `eresume profile`（有简历选 A 粘贴，没有选 B）")

    # 偏好
    prefs_done = bool(prefs.employment_types and (prefs.salary_floor or prefs.salary_monthly_min) and prefs.company_types)
    lines.append("【2. 求职偏好】" + ("✅ 已完成" if prefs_done else "⚠️ 未完成"))
    if not prefs_done:
        missing = []
        if not prefs.employment_types:
            missing.append("雇佣类型")
        if not prefs.salary_floor and not prefs.salary_monthly_min:
            missing.append("薪资")
        if not prefs.company_types:
            missing.append("公司类型")
        lines.append(f"    还差: {'、'.join(missing)} → `eresume prefs --section <对应项>` 或 `eresume prefs` 补全")

    # 岗位
    lines.append(f"【3. 岗位库】{'✅' if postings else '⚠️'} 当前 {len(postings)} 个岗位")
    if not postings:
        lines.append("    下一步: 搜实习 `eresume job scrape -k python --city 北京 --save`")
        lines.append("           或粘贴 JD `eresume job add \"<职位描述>\"`")

    # 投递
    lines.append(f"【4. 投递记录】{'✅' if apps else '⚠️'} 当前 {len(apps)} 条")
    if not apps:
        lines.append("    下一步: 投递后用 `eresume apps add 公司 \"岗位\" --channel bosszhipin` 记录")

    # 明确的下一个动作
    lines.append("")
    if not profile_done:
        lines.append("👉 你现在该做: `eresume profile`")
    elif not prefs_done:
        lines.append("👉 你现在该做: `eresume prefs`（把筛选条件补全，含薪资/公司类型）")
    elif not postings:
        lines.append("👉 你现在该做: `eresume job scrape -k <关键词> --city <城市> --save` 或 `eresume job add \"<JD>\"`")
    elif not apps:
        p0 = postings[0]
        lines.append(f"👉 你现在该做: `eresume match {p0.id}` 评估岗位，然后 `eresume cover {p0.company or '公司'} \"{p0.title or '岗位'}\"` 生成求职信")
    else:
        lines.append("👉 你现在该做: 继续投递（`eresume job scrape`）→ 匹配 → 生成材料；")
        lines.append("   收到 HR 消息用 `eresume hr \"<消息>\"`，面试用 `eresume interview <公司>`")

    lines.append("")
    lines.append("更多命令见 `eresume --help`，完整教程见 docs/USAGE_CN.md")
    return "\n".join(lines)
