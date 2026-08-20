"""已有简历导入：从粘贴的简历文本中启发式提取结构化信息。

设计原则：只提取高置信度内容，标注来源；拿不准的留给向导补问。
不面向特定行业——技术岗的技能/语言、非技术岗的案例/证书都按关键词识别。
"""

from __future__ import annotations

import re
from typing import Optional

# 各分节的中文/英文关键词（按行判断，短行且含关键词视为分节标题）
SECTION_HINTS: dict[str, list[str]] = {
    "contact": ["联系方式", "电话", "手机", "邮箱", "email", "phone", "微信", "联系"],
    "education": ["教育背景", "教育经历", "学历", "学校", "大学", "学院", "education", "university", "degree"],
    "experience": ["工作经历", "实习经历", "工作/实习", "经历", "experience", "工作"],
    "skills": ["专业技能", "技能", "擅长", "掌握", "技术栈", "skills", "专长"],
    "projects": ["项目经历", "项目经验", "项目", "projects", "作品"],
    "certifications": ["证书", "认证", "资格", "certification", "license"],
    "languages": ["语言能力", "语言", "language", "英语水平"],
    "summary": ["个人简介", "自我评价", "自我介绍", "summary", "profile", "关于我"],
}


def _split_sections(text: str) -> dict[str, list[str]]:
    """把简历文本按分节标题切分（启发式）。返回 {section: [行,...]}。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sections: dict[str, list[str]] = {"_head": []}
    current = "_head"
    for ln in lines:
        # 分节标题：短行、无标点、无数字（避免把含"大学/学院"的数据行误判为标题）
        is_header_candidate = (
            2 <= len(ln) <= 15
            and not re.search(r"[。；;，,：:（）()]|\d", ln)
        )
        if is_header_candidate:
            hit = None
            for sec, hints in SECTION_HINTS.items():
                if any(h in ln for h in hints):
                    hit = sec
                    break
            if hit:
                current = hit
                sections.setdefault(current, [])
                continue
        sections.setdefault(current, []).append(ln)
    return sections


def _extract_name(text: str) -> str:
    m = re.search(r"姓名[:：]?\s*([\u4e00-\u9fa5A-Za-z·]{2,12})", text)
    if m:
        return m.group(1).strip()
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    first = first.strip()
    # 第一行是姓名（中文 2-4 字 / 英文名），不是标题/网址
    if 2 <= len(first) <= 12 and not re.search(r"[，。；:：()（）/#《》]", first) and not first.startswith("http"):
        return first
    return ""


def _extract_contact(text: str) -> str:
    phone = re.search(r"(1[3-9]\d{9})", text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    parts = []
    if phone:
        parts.append(phone.group(1))
    if email:
        parts.append(email.group(0))
    return " / ".join(parts)


def _extract_languages(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    for ln in lines:
        for lang in ("英语", "日语", "韩语", "法语", "德语", "西班牙语", "英语"):
            if lang in ln:
                level = ""
                for lv in ("母语", "流利", "熟练", "商务", "CET-6", "CET-4", "六级", "四级", "IELTS", "TOEFL", "专八", "专四", "N1", "N2"):
                    if lv in ln:
                        level = lv
                        break
                out.append({"lang": lang, "level": level})
                break
    return out


def _extract_education(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    for ln in lines:
        m = re.search(r"((?:本科|硕士|博士|大专|学士|研究生)[^\s，。;；]*)?\s*([\u4e00-\u9fa5A-Za-z]+)\s*[·|]?\s*([\u4e00-\u9fa5A-Za-z]+(?:大学|学院|学校|学院|University|College|Institute))", ln)
        school = re.search(r"([\u4e00-\u9fa5A-Za-z]+(?:大学|学院|学校|University|College|Institute))", ln)
        degree = re.search(r"(本科|硕士|博士|大专|学士|研究生)", ln)
        years = re.search(r"(20\d{2})\s*[-–~至]\s*(20\d{2}|至今|现在)", ln)
        if school:
            out.append({
                "degree": degree.group(1) if degree else "",
                "major": m.group(2) if m else "",
                "school": school.group(1),
                "years": years.group(0) if years else "",
                "note": "",
            })
    return out


def _extract_experience(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    current: dict | None = None
    for ln in lines:
        org = re.search(r"([\u4e00-\u9fa5A-Za-z0-9（）()·]+(?:公司|科技|集团|有限|事务所|银行|研究院|中心|机构))", ln)
        role = re.search(r"((?:担任|职位|岗位|职务)[:：]?\s*)?([\u4e00-\u9fa5A-Za-z]+(?:工程师|开发|设计|运营|产品|经理|专员|助理|实习生|主管|顾问|实习生|intern))", ln)
        years = re.search(r"(20\d{2}[-/.]\d{0,2})\s*[-–~至]\s*(20\d{2}[-/.]\d{0,2}|至今|现在)", ln)
        if org or (role and years):
            if current:
                out.append(current)
            current = {
                "title": role.group(2) if role else "",
                "company": org.group(1) if org else "",
                "years": years.group(0) if years else "",
                "bullets": [],
            }
            continue
        if current and (ln.startswith(("•", "-", "·", "●", "*")) or re.match(r"^[\d一二三四五六七八九十]+[、.．]", ln)):
            current["bullets"].append(re.sub(r"^[•\-·●*]+\s*", "", ln))
    if current:
        out.append(current)
    return out


def _extract_skills(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        # 逗号/顿号/竖线分隔的技能列表
        parts = re.split(r"[，,、|;；/]", ln)
        for p in parts:
            p = p.strip().lstrip("•-·* ")
            # 过滤纯描述句（含句号或超过 8 个中文字符的句子）
            if 1 <= len(p) <= 24 and not re.search(r"[。；;]", p) and not re.search(r"[\u4e00-\u9fa5]{10,}", p):
                if re.search(r"[\u4e00-\u9fa5A-Za-z0-9+#.]", p):
                    out.append(p)
    # 去重保序
    seen: set[str] = set()
    dedup = []
    for s in out:
        if s not in seen:
            seen.add(s)
            dedup.append(s)
    return dedup


def _extract_projects(lines: list[str]) -> list[str]:
    out = []
    for ln in lines:
        ln = ln.strip().lstrip("•-·* ")
        if ln and len(ln) <= 60 and not ln.endswith(("。", "；")):
            out.append(ln)
    return out[:8]


def parse_resume_text(text: str) -> dict:
    """解析简历文本，返回 {name, contact, education, experience, skills, projects, certifications, languages}。"""
    sections = _split_sections(text)
    langs = _extract_languages(sections.get("languages", []) or (sections.get("skills", []) + sections.get("_head", [])))
    return {
        "name": _extract_name(text),
        "contact": _extract_contact(text),
        "education": _extract_education(sections.get("education", []) + sections.get("_head", [])),
        "experience": _extract_experience(sections.get("experience", []) + sections.get("projects", [])),
        "skills": _extract_skills(sections.get("skills", [])),
        "projects": _extract_projects(sections.get("projects", [])),
        "certifications": _extract_skills(sections.get("certifications", [])),
        "languages": langs,
    }
