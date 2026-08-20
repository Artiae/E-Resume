"""薪资解析与归一化：把各种薪资写法转成可比较的数字。"""

from __future__ import annotations

import re
from typing import Optional

from .models import Posting

# 常见写法：
#   "15-20K" "15-20k" "15000-20000元/月" "1.5-2万" "300/天" "面议" "200-300元/天"
#   "年薪30-40万" "25k*14" "15k-20k·14薪"


def parse_salary(text: str) -> tuple[Optional[int], Optional[int], str]:
    """返回 (下限, 上限, 周期: 月/年/天/未知)。统一换算为"元"整数。"""
    if not text:
        return None, None, "未知"
    t = text.strip()
    if not t or "面议" in t or "negotiable" in t.lower():
        return None, None, "未知"

    period = "月"
    if "年" in t or "年薪" in t:
        period = "年"
    elif "天" in t or "/日" in t or "日薪" in t:
        period = "天"

    # 提取数字及紧邻单位（k/K/万）
    matches: list[tuple[float, str]] = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)", t):
        after = t[m.end():m.end() + 1]
        unit = after if after in "kK万" else ""
        matches.append((float(m.group(1)), unit))

    if not matches:
        return None, None, period

    # 区间简写单位传播："15-20K" / "1.5-2万" -> 两个数字共享单位
    last_unit = matches[-1][1]
    if last_unit:
        matches = [(v, last_unit if not u else u) for v, u in matches]

    values = []
    for v, u in matches[:2]:
        if u.lower() == "k":
            v *= 1000
        elif u == "万":
            v *= 10000
        values.append(int(v))

    lo = values[0] if values else None
    hi = values[1] if len(values) > 1 else None
    return lo, hi, period


def to_monthly(lo: Optional[int], hi: Optional[int], period: str, days_per_month: int = 21.75) -> tuple[Optional[int], Optional[int]]:
    """统一换算为元/月（用于和偏好比较）。年 -> /12；天 -> *21.75。"""
    if period == "月":
        return lo, hi
    if period == "年":
        return (int(lo / 12) if lo else None), (int(hi / 12) if hi else None)
    if period == "天":
        return (int(lo * days_per_month) if lo else None), (int(hi * days_per_month) if hi else None)
    return lo, hi


def apply_to_posting(posting: Posting) -> None:
    """从 salary_text 解析并回填 salary_min/max/period。"""
    lo, hi, period = parse_salary(posting.salary_text)
    posting.salary_min = lo
    posting.salary_max = hi
    posting.salary_period = period


def salary_display(posting: Posting) -> str:
    if posting.salary_text:
        return posting.salary_text
    if posting.salary_min or posting.salary_max:
        return f"{posting.salary_min or '?'}-{posting.salary_max or '?'}/{posting.salary_period}"
    return "面议"
