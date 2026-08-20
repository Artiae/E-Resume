"""偏好门测试。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.models import Posting, Preferences
from eresume.gates import (
    employment_gate, salary_gate, company_gate, industry_gate, language_gate,
)


def make_posting(**kw):
    defaults = dict(title="测试岗位", company="测试公司", employment_type="全职",
                    salary_text="15000-20000元/月", salary_min=15000, salary_max=20000,
                    salary_period="月", location="北京", industry="互联网", description="")
    defaults.update(kw)
    return Posting(**defaults)


def test_employment_match():
    prefs = Preferences(employment_types=["全职"])
    assert employment_gate(make_posting(), prefs).verdict == "PASS"


def test_employment_mismatch_hard_fail():
    prefs = Preferences(employment_types=["全职"])
    g = employment_gate(make_posting(employment_type="实习"), prefs)
    assert g.verdict == "FAIL"


def test_employment_unknown_flags():
    prefs = Preferences(employment_types=["全职"])
    assert employment_gate(make_posting(employment_type=""), prefs).verdict == "FLAG"


def test_salary_below_floor_fails():
    prefs = Preferences(salary_floor=12000)
    g = salary_gate(make_posting(salary_text="8000-10000元/月", salary_min=8000, salary_max=10000), prefs)
    assert g.verdict == "FAIL"


def test_salary_over_floor_passes():
    prefs = Preferences(salary_floor=12000)
    g = salary_gate(make_posting(salary_min=15000, salary_max=20000), prefs)
    assert g.verdict == "PASS"


def test_salary_unknown_flags_not_fails():
    prefs = Preferences(salary_floor=12000)
    g = salary_gate(make_posting(salary_min=None, salary_max=None, salary_text="面议"), prefs)
    assert g.verdict == "FLAG"


def test_internship_daily_salary_flags_not_fails():
    """实习日薪不套用全职底线。"""
    prefs = Preferences(salary_floor=10000)
    g = salary_gate(make_posting(employment_type="实习", salary_text="250-400元/天",
                                 salary_min=250, salary_max=400, salary_period="天"), prefs)
    assert g.verdict == "FLAG"


def test_company_exclude_fails():
    prefs = Preferences(company_excludes=["外包"])
    g = company_gate(make_posting(company="中软国际", description="人力外包驻场"), prefs)
    assert g.verdict == "FAIL"


def test_company_big_tech_passes():
    prefs = Preferences(company_types=[], company_excludes=[])
    g = company_gate(make_posting(company="字节跳动"), prefs)
    assert g.verdict == "PASS"


def test_industry_exclude_fails():
    prefs = Preferences(industry_excludes=["教培"])
    g = industry_gate(make_posting(industry="教培/在线教育"), prefs)
    assert g.verdict == "FAIL"


def test_language_gate():
    langs = [{"lang": "中文", "level": "母语"}, {"lang": "英语", "level": "CET-6"}]
    assert language_gate(make_posting(description="要求日语流利"), langs).verdict == "FAIL"
    assert language_gate(make_posting(description="英语流利优先"), langs).verdict == "PASS"
