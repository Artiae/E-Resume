"""公司类型分类器：小而美 / 外企 / 大厂 / 潜力股 / 国企央企 / 外包 / 未知。

规则 + 关键词启发式，纯本地判断；永远标注置信度，不猜测成"确定"。
"""

from __future__ import annotations

from .models import Posting

TYPE_LABELS = ["小而美", "外企", "大厂", "潜力股", "国企央企", "外包"]

# 大厂（头部互联网/科技/通信/金融科技）名单——可按需增补
BIG_TECH_HINTS = [
    "腾讯", "阿里巴巴", "阿里", "字节跳动", "百度", "美团", "京东", "网易", "拼多多", "小米",
    "华为", "中兴", "快手", "滴滴", "蚂蚁", "哔哩哔哩", "新浪", "搜狐", "360", "携程", "唯品会",
    "微软", "谷歌", "google", "microsoft", "amazon", "aws", "meta", "apple", "apple inc",
    "华为云", "阿里云", "腾讯云", "字节", "oppo", "vivo", "荣耀", "联想", "海尔", "美的", "比亚迪",
]

MNC_HINTS = [
    "外企", "跨国公司", "全球", "英语工作环境", "外资", "frankfurt", "singapore", "london",
    "new york", "硅谷", "硅谷", "global", "multinational",
]

SOE_HINTS = ["国企", "央企", "事业单位", "国有", "国资委", "中字头", "集团", "有限公司(国有)", "中国移动", "中国电信", "中国联通", "国家电网", "中石油", "中石化", "中国银行", "工商银行", "建设银行", "农业银行", "交通银行", "招商银行", "中国人寿", "中国平安(国有)", "中建", "中铁", "中粮"]

OUTSOURCE_HINTS = ["外包", "驻场", "外派", "人力外包", "中软国际", "软通动力", "文思海辉", "博彦科技", "东软", "法本信息", "纬创"]

STARTUP_HINTS = ["创业", "初创", "融资", "天使轮", "A轮", "B轮", "C轮", "pre-a", "startup", "高速成长", "潜力股", "大厂上下游", "生态企业"]

SMALL_BEAUTY_HINTS = ["小而美", "精品", "niche", "细分", "50-200", "团队扁平", "扁平", "小而精"]


def classify(posting: Posting, verbose: bool = False) -> tuple[str, list[str]]:
    """返回 (类型, 依据列表)。依据为空表示无信号 -> 未知。"""
    evidence: list[str] = []
    haystack = " ".join([
        posting.company or "",
        posting.company_scale or "",
        posting.company_funding or "",
        posting.description or "",
        posting.tags and " ".join(posting.tags) or "",
    ]).lower()

    def hit(hints: list[str], label: str) -> bool:
        for h in hints:
            if h.lower() in haystack:
                evidence.append(f"关键词「{h}」")
                return True
        return False

    # 外包优先于其他（信息最明确）
    if hit(OUTSOURCE_HINTS, "外包"):
        return "外包", evidence
    if hit(SOE_HINTS, "国企央企"):
        return "国企央企", evidence
    if hit(BIG_TECH_HINTS, "大厂"):
        return "大厂", evidence
    if hit(MNC_HINTS, "外企"):
        return "外企", evidence
    if hit(STARTUP_HINTS, "潜力股"):
        return "潜力股", evidence
    if hit(SMALL_BEAUTY_HINTS, "小而美"):
        return "小而美", evidence
    return "未知", evidence


def describe(posting: Posting) -> str:
    """给求职者看的分类说明 + 验证建议。"""
    label, evidence = classify(posting)
    lines = [f"公司类型判定：{label}"]
    if evidence:
        lines.append("  依据：" + "、".join(evidence[:5]))
    lines.append("  提示：以上为启发式判断，正式决策请用企查查/天眼查核实工商信息、融资历史与股东结构。")
    return "\n".join(lines)
