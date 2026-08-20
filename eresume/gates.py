"""偏好门：雇佣类型 / 薪资 / 公司类型 / 行业 / 地点 / 语言。

每个门返回 GateResult(verdict=PASS|FAIL|FLAG, detail)。
FAIL = 硬性拒绝（不评分、不投递）；FLAG = 提醒但不拦截；PASS = 通过。
"""

from __future__ import annotations

from .models import Preferences, Posting, GateResult
from .company import classify
from .salary import to_monthly


def employment_gate(posting: Posting, prefs: Preferences) -> GateResult:
    wanted = prefs.employment_types
    ptype = posting.employment_type or "未知"
    if not wanted:
        return GateResult("雇佣类型", "FLAG", "尚未设置期望类型，跳过此门")
    if ptype in ("未知", ""):
        return GateResult("雇佣类型", "FLAG", f"岗位未标明类型，按期望 {wanted} 继续")
    if ptype in wanted:
        return GateResult("雇佣类型", "PASS", f"岗位类型 {ptype} 符合期望 {wanted}")
    return GateResult("雇佣类型", "FAIL", f"岗位类型为「{ptype}」，期望为 {wanted}——硬性不匹配")


def salary_gate(posting: Posting, prefs: Preferences) -> GateResult:
    floor = prefs.salary_floor
    # 实习岗位的日薪与全职月薪底线不可直接比较——交给求职者判断
    if posting.employment_type == "实习" and posting.salary_period == "天":
        return GateResult("薪资", "FLAG",
                          f"实习日薪 {posting.salary_text}（约合 {int((posting.salary_max or 0) * 21.75)} 元/月）——实习薪资与全职底线不同口径，请自行判断")
    if not floor:
        return GateResult("薪资", "FLAG", "未设置薪资底线，跳过硬性薪资门")
    if posting.salary_min is None and posting.salary_max is None:
        return GateResult("薪资", "FLAG", f"岗位薪资「{posting.salary_text or '未标明/面议'}」——不自动拒绝，面试阶段再谈")
    lo_m, hi_m = to_monthly(posting.salary_min, posting.salary_max, posting.salary_period)
    # 岗位区间整体低于底线 -> 硬拒
    if hi_m is not None and hi_m < floor:
        return GateResult("薪资", "FAIL", f"岗位上限 {hi_m} 元/月 < 底线 {floor} 元/月——硬性不匹配")
    if lo_m is not None and lo_m < floor <= (hi_m or lo_m):
        return GateResult("薪资", "FLAG", f"岗位下限 {lo_m} 元/月 触及底线 {floor} 元/月，区间内有可谈空间")
    return GateResult("薪资", "PASS", f"岗位薪资 {lo_m}-{hi_m} 元/月 不低于底线 {floor} 元/月")


def company_gate(posting: Posting, prefs: Preferences) -> GateResult:
    excludes = prefs.company_excludes
    label, evidence = classify(posting)
    if label == "未知":
        return GateResult("公司类型", "FLAG", "无法从岗位信息判断公司类型——投递前请用企查查/天眼查核实")
    if label in excludes:
        return GateResult("公司类型", "FAIL", f"公司类型判定为「{label}」，在排除列表 {excludes} 中——硬性不匹配")
    return GateResult("公司类型", "PASS", f"公司类型判定为「{label}」（{('、'.join(evidence[:3])) if evidence else '关键词'}）")


def industry_gate(posting: Posting, prefs: Preferences) -> GateResult:
    if not prefs.industry_excludes or not posting.industry:
        return GateResult("行业", "PASS", "")
    for ex in prefs.industry_excludes:
        if ex in (posting.industry or ""):
            return GateResult("行业", "FAIL", f"行业「{posting.industry}」在排除列表 {prefs.industry_excludes} 中")
    return GateResult("行业", "PASS", "")


def language_gate(posting: Posting, profile_languages: list) -> GateResult:
    """语言门：要求未声明语言 -> FAIL；声明但等级可能不足 -> FLAG。"""
    if not profile_languages:
        return GateResult("语言", "FLAG", "未设置语言信息")
    declared = [x.get("lang", "") for x in profile_languages if x.get("lang")]
    text = f"{posting.title} {posting.description}".lower()
    # 常见要求语言信号
    import re
    reqs = set()
    for pat, name in [
        (r"英语.{0,6}(流利|熟练|working proficiency)", "英语"),
        (r"english.{0,10}(fluent|proficient)", "英语"),
        (r"日语.{0,6}(流利|熟练)", "日语"),
        (r"japanese.{0,10}fluent", "日语"),
        (r"韩语", "韩语"),
        (r"德语", "德语"),
        (r"法语", "法语"),
    ]:
        if re.search(pat, text, re.I):
            reqs.add(name)
    problems = [r for r in reqs if r not in declared]
    if problems:
        return GateResult("语言", "FAIL", f"岗位要求 {problems}，但你的语言档案未声明——硬性不匹配")
    return GateResult("语言", "PASS", "")


def location_gate(posting: Posting, prefs: Preferences) -> GateResult:
    if not prefs.cities or not posting.location:
        return GateResult("地点", "PASS", "")
    if posting.location in prefs.cities:
        return GateResult("地点", "PASS", f"{posting.location} 在期望城市内")
    # 宽松匹配：城市名包含
    for c in prefs.cities:
        if c in posting.location or posting.location in c:
            return GateResult("地点", "PASS", f"{posting.location} 匹配期望城市 {c}")
    return GateResult("地点", "FLAG", f"{posting.location} 不在期望城市 {prefs.cities}——需确认是否接受")


def run_all_gates(posting: Posting, prefs: Preferences, profile_languages: list) -> list[GateResult]:
    return [
        employment_gate(posting, prefs),
        salary_gate(posting, prefs),
        company_gate(posting, prefs),
        industry_gate(posting, prefs),
        location_gate(posting, prefs),
        language_gate(posting, profile_languages),
    ]


def any_hard_fail(gates: list[GateResult]) -> list[str]:
    return [g.name for g in gates if g.verdict == "FAIL"]
