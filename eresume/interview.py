"""面试准备：准备包生成（LLM 增强，提示词模式回退）。"""

from __future__ import annotations

from . import llm
from .config import resolve_prompt
from .models import Profile, Preferences, Posting
from .salary import salary_display


def _posting_block(posting: Posting | None) -> str:
    if not posting:
        return "（未关联岗位——用 `eresume job add` 添加）"
    return (
        f"公司: {posting.company or '未知'} | 岗位: {posting.title or '未知'}\n"
        f"类型: {posting.employment_type or '未知'} | 薪资: {salary_display(posting)}\n"
        f"地点: {posting.location or '未知'}\n"
        f"描述: {(posting.description or '')[:2000]}"
    )


def _profile_block(profile: Profile) -> str:
    lines = [f"姓名: {profile.name or '(未填)'}"]
    for e in profile.education:
        lines.append(f"教育: {e.get('degree','')} {e.get('major','')} @ {e.get('school','')} ({e.get('years','')})")
    for e in profile.experience:
        lines.append(f"经历: {e.get('title','')} @ {e.get('company','')} ({e.get('years','')}) — " + "；".join(e.get("bullets", [])))
    for p in profile.projects:
        lines.append(f"项目: {p}")
    lines.append(f"核心技能: {', '.join(profile.skills_primary) or '-'}")
    lines.append(f"优势特质: {', '.join(profile.strengths) or '-'}")
    return "\n".join(lines)


def build_prep(company: str, role: str, stage: str, profile: Profile, prefs: Preferences,
               posting: Posting | None, feedback: str = "", mode: str = "auto") -> str:
    prompt = resolve_prompt("interview_prep.md").read_text(encoding="utf-8").format(
        company=company, role=role, stage=stage,
        posting=_posting_block(posting),
        profile_resume=_profile_block(profile),
        behavioral="、".join(profile.strengths) or "（未填写行为特质）",
        feedback=feedback or "（无历史反馈）",
    )
    fallback = llm.prompt_banner(f"面试准备包: {company} · {role}") + prompt
    return llm.run(prompt, system="你是面试教练，准备包必须与已提交材料一致，不得虚构经历。", mode=mode, fallback=fallback)
