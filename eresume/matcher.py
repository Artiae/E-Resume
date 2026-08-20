"""匹配引擎：偏好门 + 加权评分 + 结论与建议。

无 LLM 时用规则化关键词评分（诚实、可解释）；配置 LLM 后可用 LLM 深度报告覆盖。
评分维度（0-100）：
  technical   技术匹配      权重 30%
  experience  经验匹配      权重 25%
  company     公司类型匹配   权重 20%
  career      职业方向匹配   权重 25%
  salary      薪资匹配      有薪资时加入并重新归一化
"""

from __future__ import annotations

import re
from typing import Optional

from .models import Profile, Preferences, Posting, Evaluation, GateResult
from .gates import run_all_gates, any_hard_fail
from .company import classify
from .salary import to_monthly


def _tokens(text: str) -> set[str]:
    """粗粒度分词：中文按字符二元组 + 英文按词。"""
    text = (text or "").lower()
    tokens: set[str] = set()
    for word in re.findall(r"[a-z][a-z0-9+#.\-]{1,}", text):
        tokens.add(word)
    cjk = re.findall(r"[\u4e00-\u9fa5]{2}", text)
    tokens.update(cjk)
    return tokens


def _overlap_score(need: str, have: list[str]) -> int:
    """关键词重叠得分 0-100。"""
    have_tokens = set()
    for h in have:
        have_tokens |= _tokens(h)
    need_tokens = _tokens(need)
    if not need_tokens:
        return 50
    hits = need_tokens & have_tokens
    if not hits:
        return 20
    ratio = len(hits) / len(need_tokens)
    return min(100, int(30 + ratio * 70))


def score_technical(posting: Posting, profile: Profile) -> int:
    need = f"{posting.title} {posting.description}"
    have = profile.skills_primary + profile.skills_secondary
    base = _overlap_score(need, have)
    # 加分：核心技能命中
    primary = set()
    for s in profile.skills_primary:
        primary |= _tokens(s)
    if primary & _tokens(need):
        base = min(100, base + 15)
    return base


def score_experience(posting: Posting, profile: Profile) -> int:
    need = f"{posting.title} {posting.description}"
    bullets = []
    for e in profile.experience:
        bullets.extend(e.get("bullets", []))
    if not bullets:
        return 40
    return _overlap_score(need, bullets)


def score_company(posting: Posting, prefs: Preferences) -> int:
    label, _ = classify(posting)
    if label == "未知":
        return 50
    priority = {c.get("type"): c.get("priority", 99) for c in prefs.company_types}
    if label in priority:
        p = priority[label]
        # 第 1 优先 -> 95，第 2 -> 80，依次
        return max(55, 100 - (p - 1) * 15)
    if label in prefs.company_excludes:
        return 0
    return 50


def score_career(posting: Posting, profile: Profile) -> int:
    need = f"{posting.title} {posting.description}"
    roles = profile.target_roles or []
    goals = profile.career_goals or []
    if not roles and not goals:
        return 60
    return _overlap_score(need, roles + goals)


def score_salary(posting: Posting, prefs: Preferences) -> Optional[int]:
    if posting.salary_min is None and posting.salary_max is None:
        return None
    lo_m, hi_m = to_monthly(posting.salary_min, posting.salary_max, posting.salary_period)
    expect_min = prefs.salary_monthly_min or prefs.salary_floor or 0
    expect_max = prefs.salary_monthly_max or expect_min
    if hi_m is not None and hi_m >= expect_max:
        return 95
    if lo_m is not None and lo_m >= expect_min:
        return 75
    if hi_m is not None and hi_m >= (prefs.salary_floor or expect_min):
        return 55
    return 25


def _verdict(score: int) -> str:
    if score >= 75:
        return "强烈匹配"
    if score >= 60:
        return "推荐投递"
    if score >= 45:
        return "可以考虑"
    if score >= 30:
        return "谨慎评估"
    return "建议放弃"


def evaluate(posting: Posting, profile: Profile, prefs: Preferences) -> Evaluation:
    """完整评估：门 + 评分 + 结论。"""
    gates = run_all_gates(posting, prefs, profile.languages)
    blocked_reasons = any_hard_fail(gates)
    blocked = bool(blocked_reasons)
    scores = {
        "technical": score_technical(posting, profile),
        "experience": score_experience(posting, profile),
        "company": score_company(posting, prefs),
        "career": score_career(posting, profile),
    }
    salary = score_salary(posting, prefs)

    weights = {"technical": 0.30, "experience": 0.25, "company": 0.20, "career": 0.25}
    if salary is not None:
        scores["salary"] = salary
        # 重新归一化权重：salary 占 20%，其余按比例缩放
        weights = {k: v * 0.8 for k, v in weights.items()}
        weights["salary"] = 0.20

    overall = int(sum(scores[k] * weights[k] for k in weights if k in scores))
    ev = Evaluation(
        posting=posting,
        gates=gates,
        scores=scores,
        overall=overall,
        verdict=_verdict(overall),
        blocked=blocked,
        blocked_reasons=blocked_reasons,
    )

    # 优点与缺口（规则版）
    if scores.get("technical", 0) >= 70:
        ev.strengths.append("技术关键词覆盖良好")
    else:
        ev.gaps.append("技术关键词覆盖一般，需在简历中突出相关技能")
    if scores.get("experience", 0) >= 70:
        ev.strengths.append("经历与岗位方向契合")
    else:
        ev.gaps.append("经历匹配度一般，求职信里需要讲清可迁移能力")
    if scores.get("company", 0) >= 80:
        ev.strengths.append("公司类型符合偏好优先级")
    elif scores.get("company", 0) < 40:
        ev.gaps.append("公司类型与偏好冲突")

    if blocked:
        ev.advice = "该岗位未通过硬性偏好门（" + "、".join(blocked_reasons) + "）。不建议投递；" \
                    "如你认为判断有误，可用 `eresume prefs` 调整偏好后重新匹配。"
    else:
        hint = ""
        for g in gates:
            if g.verdict == "FLAG" and g.name == "薪资":
                hint = "岗位未标明薪资，建议沟通阶段先让对方报价再谈。"
            if g.verdict == "FLAG" and g.name == "公司类型":
                hint = "公司类型无法自动判定，投递前请核实。"
        ev.advice = f"综合评分 {overall}/100（{ev.verdict}）。" + (hint or "可进入下一步：生成简历/求职信。")

    return ev


def render(evaluation: Evaluation) -> str:
    """人类可读的评估报告。"""
    p = evaluation.posting
    lines = [
        f"\n═══ 岗位评估: {p.title or '(未命名岗位)'} @ {p.company or '未知公司'} ═══",
        "",
        "【偏好门】",
    ]
    for g in evaluation.gates:
        mark = {"PASS": "✅", "FAIL": "⛔", "FLAG": "⚠️"}.get(g.verdict, "•")
        lines.append(f"  {mark} {g.name}: {g.verdict}" + (f" — {g.detail}" if g.detail else ""))
    lines += ["", "【评分】"]
    for k, v in evaluation.scores.items():
        lines.append(f"  {k:10s} {v}/100")
    lines.append(f"\n综合评分: {evaluation.overall}/100 → {evaluation.verdict}")

    if evaluation.strengths:
        lines += ["", "【优点】"] + [f"  + {s}" for s in evaluation.strengths]
    if evaluation.gaps:
        lines += ["", "【缺口】"] + [f"  - {g}" for g in evaluation.gaps]
    if evaluation.advice:
        lines += ["", "【建议】", f"  {evaluation.advice}"]
    lines.append("")
    return "\n".join(lines)
