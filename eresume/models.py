"""数据模型：档案、偏好、岗位、投递记录、评估结果。

全部为纯 dataclass + JSON 序列化，无第三方依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ---------------- 求职者档案 (Profile) ----------------

@dataclass
class Profile:
    name: str = ""
    location: str = ""
    languages: list = field(default_factory=list)          # [{"lang": "中文", "level": "母语"}, ...]
    status: str = ""                                       # 在校学生/应届/在职/离职/自由职业
    education: list = field(default_factory=list)          # [{"degree","major","school","years","note"}]
    experience: list = field(default_factory=list)         # [{"title","company","years","bullets":[...]}]
    skills_primary: list = field(default_factory=list)
    skills_secondary: list = field(default_factory=list)
    projects: list = field(default_factory=list)           # 独立项目/开源/竞赛
    certifications: list = field(default_factory=list)
    target_roles: list = field(default_factory=list)       # 目标岗位方向
    dealbreakers: list = field(default_factory=list)       # 硬性约束
    strengths: list = field(default_factory=list)          # 行为特质/优势
    career_goals: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


# ---------------- 求职偏好 (Preferences) ----------------

@dataclass
class Preferences:
    # §1 雇佣类型
    employment_types: list = field(default_factory=list)   # ["全职","实习","兼职","合同工","远程"]
    status: str = ""
    start_availability: str = ""
    internship_days_per_week: int = 0
    internship_duration_months: int = 0
    internship_remote_ok: bool = False
    internship_conversion_hoped: bool = False
    # §2 薪资
    salary_monthly_min: Optional[int] = None               # 期望下限（税前，元/月）
    salary_monthly_max: Optional[int] = None
    salary_floor: Optional[int] = None                     # 硬底线
    salary_basis: str = "税前"                              # 税前/税后
    salary_includes_bonus: bool = True
    accept_below_for_growth: bool = False
    # §3 公司类型
    company_types: list = field(default_factory=list)      # 按优先级：[{"type":"潜力股","priority":1}, ...]
    company_excludes: list = field(default_factory=list)   # ["外包", ...]
    company_size: str = "不限"
    funding_stage: str = "不限"
    # §4 行业
    industries: list = field(default_factory=list)
    industry_excludes: list = field(default_factory=list)
    # §5 地点
    cities: list = field(default_factory=list)
    work_mode: str = "均可"                                 # 坐班/混合/远程/均可
    commute_max_minutes: int = 0
    # §6 工作强度
    overtime_tolerance: str = ""                           # 不能接受/偶尔项目期/拒绝996/接受
    flexible_hours: str = "无所谓"
    travel_tolerance: str = "不接受"
    culture_likes: list = field(default_factory=list)
    culture_redflags: list = field(default_factory=list)
    # §7 成长
    career_stage: str = ""
    growth_priorities: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Preferences":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


# ---------------- 岗位 (Posting) ----------------

@dataclass
class Posting:
    id: str = ""
    source: str = ""                # url / text / shixiseng / manual
    title: str = ""
    company: str = ""
    employment_type: str = ""       # 全职/实习/兼职/合同工/远程/未知
    salary_text: str = ""           # 原文薪资描述
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_period: str = ""         # 月/年/天
    location: str = ""
    industry: str = ""
    company_scale: str = ""
    company_funding: str = ""
    description: str = ""
    url: str = ""
    deadline: str = ""
    tags: list = field(default_factory=list)
    posted_at: str = ""
    # 人工标注
    company_type: str = ""          # 小而美/外企/大厂/潜力股/国企/外包/未知

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Posting":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


# ---------------- 投递记录 (Application) ----------------

@dataclass
class Application:
    id: str = ""
    company: str = ""
    role: str = ""
    channel: str = ""               # bosszhipin/zhilian/51job/shixiseng/referral/careers-page/linkedin/headhunter/campus/other
    date: str = ""
    status: str = "applied"         # drafted/applied/interview/offer/hired/rejected/no_response/withdrawn
    fit_score: Optional[int] = None
    contact_person: str = ""
    notes: list = field(default_factory=list)   # 时间线备注，含 HR 反馈
    posting_id: str = ""
    deadline: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Application":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


# ---------------- 评估结果 (Evaluation) ----------------

@dataclass
class GateResult:
    name: str
    verdict: str            # PASS / FAIL / FLAG
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Evaluation:
    posting: Posting
    gates: list = field(default_factory=list)            # [GateResult]
    scores: dict = field(default_factory=dict)           # {"technical": 75, ...}
    overall: int = 0
    verdict: str = ""                                    # 强烈匹配/推荐/考虑/弱/放弃
    strengths: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    advice: str = ""
    blocked: bool = False                                # 任一硬门失败则为 True
    blocked_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "posting": self.posting.to_dict(),
            "gates": [g.to_dict() for g in self.gates],
            "scores": self.scores,
            "overall": self.overall,
            "verdict": self.verdict,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "advice": self.advice,
            "blocked": self.blocked,
            "blocked_reasons": self.blocked_reasons,
        }


def gen_id(prefix: str, payload: str) -> str:
    """基于内容的稳定短 ID（去重友好）。"""
    import hashlib
    return f"{prefix}_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:10]}"
