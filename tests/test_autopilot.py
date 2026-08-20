"""风险告知与 autopilot 骨架测试。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.risk import confirm_risks, REQUIRED_ACK, ACK_ENV
from eresume.autopilot import check_selenium, SELECTOR_TEMPLATES


def test_risk_gate_requires_ack():
    """非交互场景未确认 -> 拒绝。"""
    os.environ.pop(ACK_ENV, None)
    assert confirm_risks(interactive=False) is False


def test_risk_gate_env_ack():
    """显式设置 ERESUME_ACK_RISKS=1 -> 放行。"""
    os.environ[ACK_ENV] = "1"
    try:
        assert confirm_risks() is True
    finally:
        os.environ.pop(ACK_ENV, None)


def test_required_ack_phrase():
    assert REQUIRED_ACK == "我了解风险"


def test_selenium_check_without_selenium():
    ok, msg = check_selenium()
    # 无论装没装，返回都是结构化信息
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and len(msg) > 0


def test_selector_templates_cover_channels():
    assert "shixiseng" in SELECTOR_TEMPLATES
    assert "zhilian" in SELECTOR_TEMPLATES
    assert "bosszhipin" in SELECTOR_TEMPLATES
    for tpl in SELECTOR_TEMPLATES.values():
        assert "search_box" in tpl and "job_item" in tpl
