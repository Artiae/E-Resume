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

# 岗位大类 -> 精细询问内容。不面向单一行业：语言只在相关方向询问，其余方向可跳过。
ROLE_CATEGORIES: dict[str, dict] = {
    "技术类": {"ask_languages": True, "ask_projects": True, "ask_certs": True, "skill_label": "技术栈/技能"},
    "产品类": {"ask_languages": False, "ask_projects": True, "ask_certs": False, "skill_label": "产品技能/工具"},
    "运营市场类": {"ask_languages": False, "ask_projects": False, "ask_certs": False, "skill_label": "技能/工具"},
    "设计类": {"ask_languages": False, "ask_projects": True, "ask_certs": False, "skill_label": "设计技能/软件"},
    "职能类": {"ask_languages": False, "ask_projects": False, "ask_certs": True, "skill_label": "技能/工具"},
    "其他": {"ask_languages": False, "ask_projects": False, "ask_certs": False, "skill_label": "技能/特长"},
}

CATEGORY_OPTIONS = list(ROLE_CATEGORIES.keys())


def run_profile_wizard(resume_text: str = "") -> None:
    """建档向导。

    流程：
      1. 先问职业方向（岗位大类/行业/雇佣类型/城市）——决定后续精细问题的范围
      2. 选择建档方式：A) 粘贴已有简历自动提取（有现成简历者） B) 从零开始
      3. 按岗位大类动态补充细节（技术岗才问语言，非技术岗跳过无关项）
    """
    p = load_profile()
    pr = load_preferences()

    print("\n=== E-Resume 档案建立 ===\n")
    print("先花 30 秒告诉我你的职业方向，我据此决定接下来问你什么（可直接回车跳过）。")

    # ---- 第一步：职业方向概览（种子偏好） ----
    cats = ask_list("① 你找什么方向的岗位？(可多选，逗号分隔，如: 技术类,产品类)", [])
    valid_cats = [c for c in cats if c in CATEGORY_OPTIONS]
    p.target_roles = ask_list("② 具体目标岗位？(如: 后端开发 / 产品经理 / 新媒体运营)", p.target_roles)

    industries = ask_list("③ 意向行业？(如: 互联网 / 金融 / 制造 / 教育 / 医疗，可空)", pr.industries)
    if industries:
        pr.industries = industries

    emp_types = ask_list("④ 期望雇佣类型？(全职/实习/兼职/合同工/远程)", pr.employment_types or ["全职"])
    if emp_types:
        pr.employment_types = emp_types

    cities = ask_list("⑤ 期望城市？(可空)", pr.cities)
    if cities:
        pr.cities = cities

    # ---- 第二步：建档方式 ----
    if not resume_text:
        way = ask_choice("⑥ 你已经有写好的简历吗？\n   A) 有，我粘贴过来帮你提取   B) 没有，从零开始", ["A", "B"], "A")
        if way == "A":
            print("\n请粘贴你的简历全文（纯文本），粘贴完成后**单独输入一行 end 或按两下回车**：")
            pasted = []
            while True:
                try:
                    ln = input()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if ln.strip().lower() in ("end", "eof") or (ln.strip() == "" and pasted and pasted[-1].strip() == ""):
                    break
                pasted.append(ln)
            resume_text = "\n".join(pasted)

    if resume_text.strip():
        _import_from_resume(p, resume_text)
    else:
        _ask_from_scratch(p, valid_cats)

    # ---- 收尾：通用必填/可选 ----
    p.name = p.name or ask("姓名", "")
    p.location = p.location or ask("所在城市", "")
    p.status = p.status or ask("当前状态 (在校学生/应届毕业生/在职/离职空窗/自由职业)", "")

    if not p.dealbreakers:
        p.dealbreakers = ask_list("硬性约束/不接受的？(如: 外包/频繁出差/单休，可空)", [])
    if not p.career_goals:
        p.career_goals = ask_list("职业目标？(可空)", [])

    save_profile(p)
    save_preferences(pr)
    print(f"\n✅ 档案已保存：{p.name or '(未填姓名)'}，技能 {len(p.skills_primary)} 项，经历 {len(p.experience)} 条")
    print("下一步：`eresume prefs` 细化求职偏好（薪资/公司类型等），然后 `eresume match <岗位>` 开始匹配。\n")


def _print_extraction_summary(parsed: dict) -> None:
    print("\n── 已从简历中提取到以下内容 ──")
    if parsed["name"]:
        print(f"  姓名: {parsed['name']}")
    if parsed["contact"]:
        print(f"  联系方式: {parsed['contact']}")
    for e in parsed["education"]:
        print(f"  教育: {e['degree'] or '-'} {e['major'] or '-'} @ {e['school']} ({e['years']})")
    for e in parsed["experience"]:
        print(f"  经历: {e['title'] or '-'} @ {e['company'] or '-'} ({e['years']}) — {len(e['bullets'])} 条要点")
    if parsed["skills"]:
        print(f"  技能: {', '.join(parsed['skills'][:12])}{'…' if len(parsed['skills']) > 12 else ''}")
    for pj in parsed["projects"]:
        print(f"  项目: {pj}")
    for lg in parsed["languages"]:
        print(f"  语言: {lg['lang']} ({lg['level']})")
    print("────────────────────────────")


def _import_from_resume(p: Profile, resume_text: str) -> None:
    from .resume_import import parse_resume_text

    parsed = parse_resume_text(resume_text)
    _print_extraction_summary(parsed)

    ok = ask("以上提取是否正确？(y=正确直接使用 / n=哪里不对重新填哪里)", "y")
    if ok.lower() not in ("n", "no", "否"):
        p.name = p.name or parsed["name"]
        p.education = parsed["education"] or p.education
        p.experience = parsed["experience"] or p.experience
        p.skills_primary = parsed["skills"] or p.skills_primary
        p.projects = parsed["projects"] or p.projects
        p.languages = parsed["languages"] or p.languages
        print("✅ 已采用提取结果。下面只补充缺失的关键信息。")
    else:
        print("\n好的，我们手动逐项填写（可直接回车跳过）。")
        _ask_from_scratch(p, [])

    # 补齐缺失项（只问没填到的）
    if not p.education:
        _ask_education(p)
    if not p.experience:
        _ask_experience(p)
    if not p.skills_primary:
        p.skills_primary = ask_list("核心技能/特长(逗号分隔)", [])
    if not p.projects:
        more = ask("有项目/作品经历要补充吗？(y/N)", "")
        if more.lower() in ("y", "yes", "是"):
            p.projects = ask_list("项目/作品(分号或逗号分隔)", [])
    if not p.languages:
        more = ask("需要填写语言能力吗？(技术岗/外企岗需要，其他可跳过)", "N")
        if more.lower() in ("y", "yes", "是"):
            langs = []
            while True:
                lang = ask("语言(回车结束)", "")
                if not lang:
                    break
                level = ask("水平", "")
                langs.append({"lang": lang, "level": level})
            p.languages = langs


def _ask_from_scratch(p: Profile, categories: list[str]) -> None:
    """从零开始：按岗位大类动态询问。"""
    print("\n── 从零建档（可直接回车跳过任一节）──")

    p.name = p.name or ask("姓名", "")
    p.location = p.location or ask("所在城市", "")
    p.status = p.status or ask("当前状态 (在校学生/应届毕业生/在职/离职空窗/自由职业)", "")

    _ask_education(p)
    _ask_experience(p)

    # 技能：标签随岗位大类变化
    label = "核心技能/特长"
    for c in categories:
        if c in ROLE_CATEGORIES and ROLE_CATEGORIES[c]["skill_label"]:
            label = ROLE_CATEGORIES[c]["skill_label"]
            break
    p.skills_primary = ask_list(f"{label}(逗号分隔)", p.skills_primary)
    p.skills_secondary = ask_list("其他技能(可选)", p.skills_secondary)

    needs_projects = any(ROLE_CATEGORIES.get(c, {}).get("ask_projects") for c in categories)
    if needs_projects or ask("有项目/作品要填写吗？(y/N)", "N").lower() in ("y", "yes", "是"):
        p.projects = ask_list("项目/作品(分号或逗号分隔)", p.projects)

    needs_langs = any(ROLE_CATEGORIES.get(c, {}).get("ask_languages") for c in categories)
    if needs_langs:
        print("（技术类岗位通常需要语言能力）")
        _ask_languages(p)
    elif ask("需要填写语言能力吗？(技术岗/外企岗需要，其他可跳过) (y/N)", "N").lower() in ("y", "yes", "是"):
        _ask_languages(p)

    needs_certs = any(ROLE_CATEGORIES.get(c, {}).get("ask_certs") for c in categories)
    if needs_certs:
        p.certifications = ask_list("证书/资格(逗号分隔)", p.certifications)


def _ask_languages(p: Profile) -> None:
    langs = []
    for lg in p.languages or []:
        langs.append({"lang": ask("语言", lg.get("lang", "")), "level": ask("水平", lg.get("level", ""))})
    more = ask("还要添加语言吗？(y/N)", "")
    while more.lower() in ("y", "yes", "是"):
        langs.append({"lang": ask("语言", ""), "level": ask("水平", "")})
        more = ask("还要添加语言吗？(y/N)", "")
    p.languages = [x for x in langs if x["lang"]]


def _ask_education(p: Profile) -> None:
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


def _ask_experience(p: Profile) -> None:
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
