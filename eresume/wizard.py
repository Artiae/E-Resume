"""交互式向导：建档 (profile) 与求职偏好 (prefs)。

纯 stdin/stdout 交互，无第三方依赖。所有输入都落盘到本地 JSON。
"""

from __future__ import annotations

from typing import Callable, Optional

from .models import Profile, Preferences
from .storage import load_profile, save_profile, load_preferences, save_preferences


def ask(prompt: str, default: str = "", validate: Optional[Callable[[str], Optional[str]]] = None) -> str:
    """问一个问题，返回答案；空输入用默认值。"""
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            raw = input(f"{prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(0)
        value = raw or default
        if validate:
            err = validate(value)
            if err:
                print(f"  ⚠ {err}")
                continue
        return value


def ask_int(prompt: str, default: int = 0) -> int:
    raw = ask(prompt, str(default) if default else "")
    try:
        return int(raw) if raw else default
    except ValueError:
        print("  ⚠ 请输入数字")
        return ask_int(prompt, default)


def ask_list(prompt: str, default: list = None) -> list:
    """逗号分隔多选，空输入保留默认。"""
    d = ", ".join(default) if default else ""
    raw = ask(prompt, d)
    return [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]


def ask_choice(prompt: str, options: list, default: Optional[str] = None) -> str:
    """带编号单选。"""
    labels = " / ".join(options)
    d = default or options[0]
    while True:
        raw = ask(f"{prompt} ({labels})", d)
        if raw in options:
            return raw
        for i, o in enumerate(options, 1):
            if raw == str(i):
                return o
        print(f"  ⚠ 请从 {labels} 中选择，或输入编号 1-{len(options)}")


# ---------------- Profile 向导 ----------------

def run_profile_wizard() -> None:
    p = load_profile()
    print("\n=== E-Resume 档案建立（可直接回车跳过） ===\n")

    p.name = ask("姓名", p.name)
    p.location = ask("所在城市", p.location)
    p.status = ask("当前状态 (在校学生/应届毕业生/在职/离职空窗/自由职业)", p.status)

    print("\n-- 语言 --")
    langs = []
    for lang in p.languages or [{}]:
        langs.append({"lang": ask("语言", lang.get("lang", "")), "level": ask("水平", lang.get("level", ""))})
    more = ask("还要添加语言吗？(y/N)", "")
    while more.lower() in ("y", "yes", "是"):
        langs.append({"lang": ask("语言", ""), "level": ask("水平", "")})
        more = ask("还要添加语言吗？(y/N)", "")
    p.languages = [x for x in langs if x["lang"]]

    print("\n-- 教育经历 --")
    edu = []
    for e in p.education or []:
        edu.append({
            "degree": ask("学位", e.get("degree", "")),
            "major": ask("专业", e.get("major", "")),
            "school": ask("学校", e.get("school", "")),
            "years": ask("年份", e.get("years", "")),
            "note": ask("备注(论文/成绩/课程)", e.get("note", "")),
        })
    more = ask("还要添加教育经历吗？(y/N)", "")
    while more.lower() in ("y", "yes", "是"):
        edu.append({
            "degree": ask("学位", ""), "major": ask("专业", ""), "school": ask("学校", ""),
            "years": ask("年份", ""), "note": ask("备注", ""),
        })
        more = ask("还要添加教育经历吗？(y/N)", "")
    p.education = [x for x in edu if x["degree"] or x["school"]]

    print("\n-- 工作/实习经历 --")
    exp = []
    for e in p.experience or []:
        bullets = ask_list("成果要点(逗号分隔)", e.get("bullets", []))
        exp.append({
            "title": ask("职位", e.get("title", "")),
            "company": ask("公司", e.get("company", "")),
            "years": ask("时间", e.get("years", "")),
            "bullets": bullets,
        })
    more = ask("还要添加经历吗？(y/N)", "")
    while more.lower() in ("y", "yes", "是"):
        bullets = ask_list("成果要点(逗号分隔)", [])
        exp.append({"title": ask("职位", ""), "company": ask("公司", ""), "years": ask("时间", ""), "bullets": bullets})
        more = ask("还要添加经历吗？(y/N)", "")
    p.experience = [x for x in exp if x["title"] or x["company"]]

    p.skills_primary = ask_list("核心技能(逗号分隔)", p.skills_primary)
    p.skills_secondary = ask_list("次要技能(逗号分隔)", p.skills_secondary)
    p.target_roles = ask_list("目标岗位方向(逗号分隔)", p.target_roles)
    p.dealbreakers = ask_list("硬性约束/不接受的(逗号分隔)", p.dealbreakers)
    p.career_goals = ask_list("职业目标(逗号分隔)", p.career_goals)

    save_profile(p)
    print(f"\n✅ 档案已保存：{p.name or '(未填姓名)'}，技能 {len(p.skills_primary)} 项，经历 {len(p.experience)} 条")
    print("下一步：运行 `eresume prefs` 设置求职偏好，然后 `eresume match <岗位>` 开始匹配。\n")


# ---------------- Preferences 向导 ----------------

COMPANY_TYPES = ["小而美", "外企", "大厂", "潜力股", "国企央企", "外包"]


def run_prefs_wizard(section: str = "") -> None:
    pr = load_preferences()

    if section in ("", "employment"):
        print("\n=== §1 雇佣类型 ===")
        pr.status = ask("当前状态", pr.status)
        pr.employment_types = ask_list("期望类型(全职/实习/兼职/合同工/远程，逗号分隔)", pr.employment_types)
        pr.start_availability = ask("可到岗时间", pr.start_availability)
        if "实习" in pr.employment_types:
            pr.internship_days_per_week = ask_int("每周可到岗天数", pr.internship_days_per_week)
            pr.internship_duration_months = ask_int("实习时长(月)", pr.internship_duration_months)
            pr.internship_remote_ok = ask_choice("接受远程实习", ["是", "否"], "是" if pr.internship_remote_ok else "否") == "是"
            pr.internship_conversion_hoped = ask_choice("期望转正", ["是", "否"], "是" if pr.internship_conversion_hoped else "否") == "是"

    if section in ("", "salary"):
        print("\n=== §2 薪资 ===")
        pr.salary_monthly_min = ask_int("期望月薪下限(税前元/月)", pr.salary_monthly_min or 0) or None
        pr.salary_monthly_max = ask_int("期望月薪上限(税前元/月)", pr.salary_monthly_max or 0) or None
        pr.salary_floor = ask_int("硬底线(低于此直接不投)", pr.salary_floor or 0) or None
        pr.salary_basis = ask_choice("薪资口径", ["税前", "税后"], pr.salary_basis)
        pr.accept_below_for_growth = ask_choice("是否接受低于期望但成长性强的 offer", ["是", "否", "视情况"], "是" if pr.accept_below_for_growth else "否") == "是"

    if section in ("", "company"):
        print("\n=== §3 公司类型 ===")
        current = [c.get("type", "") for c in pr.company_types]
        wanted = ask_list("期望类型(按优先级逗号分隔: 小而美,外企,大厂,潜力股,国企央企)", current)
        pr.company_types = [{"type": t, "priority": i + 1} for i, t in enumerate(wanted)]
        pr.company_excludes = ask_list("明确排除(如: 外包)", pr.company_excludes)
        pr.company_size = ask_choice("公司规模偏好", ["<50", "50-200", "200-1000", "1000-10000", "10000+", "不限"], pr.company_size)
        pr.funding_stage = ask_choice("融资阶段偏好(创业公司)", ["种子", "A轮", "B轮", "C轮+", "不限"], pr.funding_stage)

    if section in ("", "industry"):
        print("\n=== §4 行业 ===")
        pr.industries = ask_list("目标行业(逗号分隔)", pr.industries)
        pr.industry_excludes = ask_list("明确排除行业(逗号分隔)", pr.industry_excludes)

    if section in ("", "location"):
        print("\n=== §5 地点与办公 ===")
        pr.cities = ask_list("期望城市(逗号分隔)", pr.cities)
        pr.work_mode = ask_choice("办公模式", ["坐班", "混合", "远程", "均可"], pr.work_mode)
        pr.commute_max_minutes = ask_int("通勤上限(分钟)", pr.commute_max_minutes)

    if section in ("", "workload"):
        print("\n=== §6 工作强度与文化 ===")
        pr.overtime_tolerance = ask_choice("加班接受度", ["完全不能接受", "偶尔项目期可以", "拒绝常态化996", "接受"], pr.overtime_tolerance or "拒绝常态化996")
        pr.travel_tolerance = ask_choice("出差接受度", ["不接受", "偶尔可以", "接受"], pr.travel_tolerance)
        pr.culture_likes = ask_list("文化偏好(逗号分隔)", pr.culture_likes)
        pr.culture_redflags = ask_list("文化雷区(逗号分隔)", pr.culture_redflags)

    if section in ("", "growth"):
        print("\n=== §7 职业阶段与成长 ===")
        pr.career_stage = ask_choice("当前阶段", ["初入职场", "成长期", "成熟期", "转型期"], pr.career_stage or "成长期")
        pr.growth_priorities = ask_list("优先成长方向(逗号分隔)", pr.growth_priorities)

    save_preferences(pr)
    print("\n✅ 求职偏好已保存。这些偏好将成为匹配与过滤的依据。\n")
