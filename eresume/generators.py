"""求职材料生成：Markdown 简历 + 求职信（LLM 增强，模板回退）。"""

from __future__ import annotations

import datetime

from . import llm
from .config import resolve_prompt, resolve_template
from .models import Profile, Preferences, Posting
from .salary import salary_display


# ---------------- 简历（模板生成，无需 LLM） ----------------

def resume_markdown(profile: Profile, target: str = "") -> str:
    """从档案生成 Markdown 简历（中文）。"""
    lines = [f"# {profile.name or '(姓名)'}"]
    meta = []
    if profile.location:
        meta.append(profile.location)
    if profile.languages:
        meta.append("语言: " + "; ".join(f"{x.get('lang','')}({x.get('level','')})" for x in profile.languages))
    if meta:
        lines.append(" | ".join(meta))
    lines.append("")

    if target:
        lines += ["## 求职意向", f"- 目标岗位：{target}", ""]

    if profile.education:
        lines.append("## 教育背景")
        for e in profile.education:
            head = f"- **{e.get('degree','')} · {e.get('major','')}** — {e.get('school','')} ({e.get('years','')})"
            lines.append(head)
            if e.get("note"):
                lines.append(f"  - {e['note']}")
        lines.append("")

    if profile.experience:
        lines.append("## 工作/实习经历")
        for e in profile.experience:
            lines.append(f"- **{e.get('title','')}** @ {e.get('company','')} ({e.get('years','')})")
            for b in e.get("bullets", []):
                lines.append(f"  - {b}")
        lines.append("")

    if profile.projects:
        lines.append("## 项目/竞赛")
        for p in profile.projects:
            lines.append(f"- {p}")
        lines.append("")

    if profile.skills_primary or profile.skills_secondary:
        lines.append("## 技能")
        if profile.skills_primary:
            lines.append(f"- 核心：{', '.join(profile.skills_primary)}")
        if profile.skills_secondary:
            lines.append(f"- 其他：{', '.join(profile.skills_secondary)}")
        lines.append("")

    if profile.certifications:
        lines.append("## 证书")
        for c in profile.certifications:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


# ---------------- 求职信 ----------------

def cover_letter(profile: Profile, prefs: Preferences, posting: Posting | None,
                 company: str, role: str, channel: str = "", mode: str = "auto") -> str:
    if posting:
        company = posting.company or company
        role = posting.title or role

    prompt = resolve_prompt("cover_letter.md").read_text(encoding="utf-8").format(
        company=company, role=role, language="中文",
        posting=(
            f"公司: {posting.company} | 岗位: {posting.title}\n类型: {posting.employment_type or '未知'}\n"
            f"薪资: {salary_display(posting)}\n描述: {(posting.description or '')[:2000]}"
            if posting else f"公司: {company}\n岗位: {role}\n（未添加岗位详情，请补充）"
        ),
        profile_resume=resume_markdown(profile),
        preferences=prefs.to_dict(),
    )
    fallback = llm.prompt_banner(f"求职信: {company} · {role}") + prompt
    return llm.run(prompt, system="你是求职信写作专家，内容必须基于简历事实。", mode=mode, fallback=fallback)


def cover_letter_template(profile: Profile, company: str, role: str, channel: str = "") -> str:
    """无 LLM 的模板回退：结构化中文求职信骨架。"""
    today = datetime.date.today().strftime("%Y年%m月%d日")
    name = profile.name or "【姓名】"
    phone = "【电话】"
    email = "【邮箱】"
    skills = "、".join(profile.skills_primary[:3]) or "【核心技能】"
    exp_line = ""
    if profile.experience:
        e = profile.experience[0]
        exp_line = f"{e.get('title','')}（{e.get('company','')}，{e.get('years','')}）"
    source = {"bosszhipin": "BOSS直聘", "zhilian": "智联招聘", "51job": "前程无忧", "shixiseng": "实习僧",
              "referral": "内推渠道", "linkedin": "LinkedIn", "careers-page": "贵公司官网"}.get(channel, "招聘平台")
    return f"""# 求职信

**{name}** · {phone} · {email}
申请岗位：{role} @ {company}

尊敬的招聘负责人：

您好！我是{name}，{exp_line or '应届毕业生'}，具备{skills}等方面的能力。从{source}了解到贵公司正在招聘{role}，对这个岗位非常感兴趣。

我的背景与岗位的匹配点主要有：

- **【匹配点1】**：{exp_line and '在相关经历中，' or ''}【用真实成果替换：量化优先，如"主导XX项目，实现XX%提升"】
- **【匹配点2】**：【对应经历或技能】
- **【匹配点3】**：【如存在能力差距，诚实说明学习路径】

【可选：一段关于文化契合或职业目标的说明，与你的真实想法一致】

随信附上我的简历，期待与您进一步交流。如需补充材料请随时联系我。

此致
敬礼！

{name}
{today}
"""
