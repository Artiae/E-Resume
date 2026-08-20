"""简历导入解析测试。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.resume_import import parse_resume_text

TECH_RESUME = """张小明
电话: 13812345678 邮箱: zhang@example.com

教育背景
2022-2026 本科 计算机科学与技术 北京工业大学

工作经历
2025.06-2025.12 后端开发实习生 某互联网科技公司
- 参与订单系统重构，QPS 提升 40%
- 使用 Python/Flask 开发接口 20+

专业技能
Python, Flask, MySQL, Redis, Docker

语言能力
英语 CET-6

项目经历
订单系统重构项目
"""

MARKETING_RESUME = """李小红
13900001111

教育背景
2020-2024 本科 市场营销 上海财经大学

工作经历
2024.03-至今 新媒体运营 某消费品牌公司
- 运营公众号粉丝 5 万+
- 策划 10 场线上活动

技能特长
文案写作, 数据分析, 公众号运营, Excel
"""


def test_parse_tech_resume():
    r = parse_resume_text(TECH_RESUME)
    assert r["name"] == "张小明"
    assert "13812345678" in r["contact"]
    assert r["education"] and r["education"][0]["school"] == "北京工业大学"
    assert r["education"][0]["degree"] == "本科"
    exp = r["experience"]
    assert exp and exp[0]["company"] == "某互联网科技公司"
    assert exp[0]["title"] == "后端开发实习生"
    assert any("QPS" in b for b in exp[0]["bullets"])
    assert "Python" in r["skills"]
    assert any(l["lang"] == "英语" for l in r["languages"])


def test_parse_marketing_resume():
    """非技术岗简历：不依赖技术关键词也能提取。"""
    r = parse_resume_text(MARKETING_RESUME)
    assert r["name"] == "李小红"
    assert r["experience"] and r["experience"][0]["company"] == "某消费品牌公司"
    assert any("公众号" in s for s in r["skills"])
    # 营销岗不写语言 -> languages 为空
    assert r["languages"] == []


def test_parse_empty():
    r = parse_resume_text("")
    assert r["name"] == ""
    assert r["education"] == []
    assert r["experience"] == []
