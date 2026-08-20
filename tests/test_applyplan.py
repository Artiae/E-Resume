"""投递计划测试：URL 构造与话术生成。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.applyplan import build_url, build_greeting, pick_channels
from eresume.models import Profile, Preferences


def test_build_url_encoding():
    u = build_url("bosszhipin", "后端开发", "北京")
    assert "query=%E5%90%8E%E7%AB%AF%E5%BC%80%E5%8F%91" in u
    assert "city=101010100" in u  # 北京 code


def test_build_url_no_city():
    u = build_url("bosszhipin", "python", "")
    assert "city=" not in u


def test_build_url_channels():
    assert "zhaopin.com" in build_url("zhilian", "产品经理", "上海")
    assert "51job.com" in build_url("51job", "运营")
    assert "shixiseng.com" in build_url("shixiseng", "前端", "北京")
    assert "linkedin.com" in build_url("linkedin", "developer")
    assert "iguopin.com" in build_url("soe", "不限")


def test_greeting_contains_profile():
    p = Profile(name="张小明", status="应届毕业生", skills_primary=["Python", "Flask"])
    g = build_greeting(p, "后端开发", "bosszhipin")
    assert "张小明" in g and "Python" in g and "后端开发" in g


def test_pick_channels_by_employment():
    pr = Preferences(employment_types=["实习"])
    assert "shixiseng" in pick_channels(pr)
    pr2 = Preferences(employment_types=["全职"], company_types=[{"type": "外企", "priority": 1}])
    assert "linkedin" in pick_channels(pr2)
