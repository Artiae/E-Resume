"""岗位文本解析：从粘贴的 JD / URL 提取结构化字段（启发式，尽力而为）。"""

from __future__ import annotations

import re
from typing import Optional

from .models import Posting
from .salary import parse_salary

TYPE_PATTERNS = [
    ("实习", ["实习"]),
    ("兼职", ["兼职", "part-time"]),
    ("合同工", ["合同", "contract"]),
    ("远程", ["远程", "remote"]),
    ("全职", ["全职", "full-time"]),
]

FIELD_PATTERNS = {
    "company": [r"公司[:：]\s*([^\n，。；]+)", r"company[:：]\s*([^\n,;]+)"],
    "location": [r"(?:城市|地点|工作地点)[:：]\s*([^\n，。；]+)", r"(?:city|location)[:：]\s*([^\n,;]+)"],
    "industry": [r"行业[:：]\s*([^\n，。；]+)", r"industry[:：]\s*([^\n,;]+)"],
    "scale": [r"(?:规模|公司规模)[:：]\s*([^\n，。；]+)"],
    "funding": [r"(?:融资|轮次)[:：]\s*([^\n，。；]+)"],
}


def _first(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def parse_posting_text(text: str, source: str = "text") -> Posting:
    text = (text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    p = Posting()
    p.source = source
    p.description = text

    # 标题：第一行（若像是标题）
    if lines:
        first = lines[0]
        if len(first) <= 60 and not re.match(r"^(https?://|【|#)", first):
            p.title = first
        else:
            p.title = ""

    # 雇佣类型
    for label, kws in TYPE_PATTERNS:
        if any(k in text for k in kws):
            p.employment_type = label
            break

    # 薪资（任意含薪资关键词的行）
    for ln in lines:
        if re.search(r"(薪|工资|salary|k\b|K\b|万|元/|k\*|\d+[kK])", ln) and re.search(r"\d", ln):
            p.salary_text = ln
            lo, hi, period = parse_salary(ln)
            p.salary_min, p.salary_max, p.salary_period = lo, hi, period
            break

    # 字段
    for field, pats in FIELD_PATTERNS.items():
        for pat in pats:
            v = _first(pat, text)
            if v:
                setattr(p, field, v)
                break

    # 链接
    m = re.search(r"https?://[^\s，。；]+", text)
    if m:
        p.url = m.group(0)

    # 截止时间
    dm = re.search(r"(?:截止|deadline)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", text)
    if dm:
        p.deadline = dm.group(1)

    return p
