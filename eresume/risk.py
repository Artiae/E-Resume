"""风险告知与知情确认：自动化操作的入口闸门。

原则：自动化投递/回复存在真实风险，工具不替用户做决定——
先把风险讲清楚，用户必须显式确认后才能继续。
"""

from __future__ import annotations

import os

RISK_NOTICE = """
════════════════════ 风险告知（请务必阅读） ════════════════════
本功能为【实验性】半自动操作，使用前请确认你已了解以下风险：

1. 【封号风险】BOSS直聘/智联/51job 等平台有登录墙、验证码、设备指纹
   与行为检测。自动化操作违反各平台服务条款（ToS），一旦被检测到，
   可能导致账号被封禁、简历被下架、沟通被限制。平台检测规则随时变化。

2. 【自动回复风险】自动向 HR 发送消息有不可控风险：AI 生成的内容可能
   语气不当、信息有误、或与你的真实情况不符，一旦发出难以撤回，
   可能损害真实机会。因此：HR 回复【永远由你确认后手动发送】，
   本工具只生成草稿，绝不代发。

3. 【技术稳定性】平台页面结构会频繁改版，自动化选择器可能随时失效；
   失效时本工具会回退到人工协助模式，不会强行重试以免触发风控。

4. 【使用建议】仅用于个人求职，保持低频、小批量；每条投递由你逐条确认。

确认方式：输入「我了解风险」继续；输入其他内容将退出。
══════════════════════════════════════════════════════════════
"""

# 非交互场景（测试/脚本）可用环境变量跳过确认
ACK_ENV = "ERESUME_ACK_RISKS"
REQUIRED_ACK = "我了解风险"


def confirm_risks(interactive: bool = True) -> bool:
    """打印风险告知并要求显式确认。返回 True 表示已确认。"""
    if os.environ.get(ACK_ENV, "").strip() == "1":
        return True
    if not interactive:
        return False
    print(RISK_NOTICE)
    try:
        answer = input("请输入「我了解风险」继续，或直接回车退出: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已退出")
        return False
    if answer == REQUIRED_ACK:
        print("✅ 已确认。进入半自动模式。\n")
        return True
    print("未确认，已退出。\n")
    return False
