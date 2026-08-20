"""匹配引擎 / 公司分类 / HR 意图 / 渠道 / 实习僧解析 测试。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.models import Profile, Preferences, Posting
from eresume.matcher import evaluate
from eresume.company import classify
from eresume.hrbot import classify_intent
from eresume.channels import find_channel


# ---------- matcher ----------

def make_profile():
    return Profile(
        name="测试", location="北京", status="应届毕业生",
        languages=[{"lang": "中文", "level": "母语"}],
        skills_primary=["Python", "Flask", "MySQL"],
        target_roles=["后端开发", "Python开发"],
        experience=[{"title": "后端实习", "company": "某公司", "years": "2025",
                     "bullets": ["用 Python/Flask 开发接口", "优化 SQL 查询"]}],
    )


def make_prefs():
    return Preferences(
        employment_types=["全职", "实习"],
        salary_floor=10000,
        company_types=[{"type": "潜力股", "priority": 1}, {"type": "小而美", "priority": 2}],
        company_excludes=["外包"],
    )


def test_evaluate_blocked_on_employment_mismatch():
    posting = Posting(title="运营实习生", employment_type="兼职", salary_text="面议",
                      description="内容运营 新媒体 文案")
    ev = evaluate(posting, make_profile(), make_prefs())
    assert ev.blocked is True
    assert "雇佣类型" in ev.blocked_reasons


def test_evaluate_ok_posting():
    posting = Posting(title="Python后端开发实习生", company="某潜力公司",
                      employment_type="实习", salary_text="200-300元/天",
                      salary_min=200, salary_max=300, salary_period="天",
                      description="Python Flask MySQL Redis 后端开发 大模型应用")
    ev = evaluate(posting, make_profile(), make_prefs())
    assert ev.blocked is False
    assert 0 <= ev.overall <= 100


# ---------- company ----------

def test_classify_big_tech():
    label, ev = classify(Posting(company="字节跳动", description="大模型方向"))
    assert label == "大厂"


def test_classify_outsourcing():
    label, _ = classify(Posting(company="中软国际", description="驻场开发"))
    assert label == "外包"


def test_classify_soe():
    label, _ = classify(Posting(company="中国移动", description="国企"))
    assert label in ("国企央企",)


def test_classify_unknown():
    label, ev = classify(Posting(company="甲乙丙丁科技", description="招人"))
    assert label == "未知"


# ---------- hrbot ----------

def test_hr_intent():
    assert classify_intent("您好，方便明天下午3点视频面试吗？") == "面试邀请"
    assert classify_intent("请问您的期望薪资是多少？") == "薪资沟通"
    assert classify_intent("很遗憾，这个岗位不太匹配") == "拒信"


# ---------- channels ----------

def test_channel_find_alias():
    c = find_channel("内推")
    assert c and c["id"] == "referral"
    c2 = find_channel("bosszhipin")
    assert c2 and c2["id"] == "bosszhipin"
    c3 = find_channel("牛客职")
    assert c3 and c3["id"] == "nowcoder"


# ---------- LLM 厂商预设 ----------

from eresume.config import provider_preset, llm_config


def test_provider_presets():
    d = provider_preset("deepseek")
    assert d["base_url"] == "https://api.deepseek.com/v1"
    assert d["model"] == "deepseek-chat"
    q = provider_preset("通义")
    assert q and q["base_url"].startswith("https://dashscope")
    assert provider_preset("不存在的厂商") is None


def test_llm_config_prefers_env_over_preset():
    import os
    os.environ["ERESUME_PROVIDER"] = "kimi"
    os.environ["ERESUME_BASE_URL"] = "https://example.com/v1"
    cfg = llm_config()
    assert cfg["base_url"] == "https://example.com/v1"
    assert cfg["model"] == "moonshot-v1-8k"
    os.environ.pop("ERESUME_PROVIDER", None)
    os.environ.pop("ERESUME_BASE_URL", None)
