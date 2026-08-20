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
