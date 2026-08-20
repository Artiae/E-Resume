"""薪资解析测试。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.salary import parse_salary, to_monthly


def test_k_range():
    lo, hi, period = parse_salary("15-20K")
    assert (lo, hi, period) == (15000, 20000, "月")


def test_wan_range():
    lo, hi, period = parse_salary("1.5-2万")
    assert lo == 15000 and hi == 20000 and period == "月"


def test_daily():
    lo, hi, period = parse_salary("250-400元/天")
    assert (lo, hi, period) == (250, 400, "天")


def test_annual():
    lo, hi, period = parse_salary("年薪30-40万")
    assert lo == 300000 and hi == 400000 and period == "年"


def test_negotiable():
    assert parse_salary("面议") == (None, None, "未知")
    assert parse_salary("") == (None, None, "未知")


def test_to_monthly():
    assert to_monthly(300000, 400000, "年") == (25000, 33333)
    lo, hi = to_monthly(250, 400, "天")
    assert lo == 5437 and hi == 8700
