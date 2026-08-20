"""autopilot：半自动投递（实验性）。

两层模式：
  1. 人工协助模式（assist，默认）：不需要 Selenium。
     打开预填搜索页 → 你手动登录/搜索 → 逐条给你话术 → 你确认发送 → 记录。
     HR 回复永远由你手动发送。
  2. 自动模式（--auto，实验性）：需要 Selenium + ChromeDriver。
     由于各平台 DOM 频繁改版且无法远程验证选择器，自动模式是骨架实现：
     一旦选择器失效或出错，立即回退到人工协助模式，绝不强行重试（避免触发风控）。
"""

from __future__ import annotations

from .models import Profile, Preferences
from .risk import confirm_risks
from . import applyplan


def check_selenium() -> tuple[bool, str]:
    """检查 Selenium 是否可用。返回 (可用, 提示信息)。"""
    try:
        import selenium  # noqa: F401
        return True, "Selenium 已安装"
    except ImportError:
        return False, (
            "未安装 Selenium（可选依赖）。安装方法：\n"
            "  pip install selenium\n"
            "  pip install webdriver-manager   # 自动管理 ChromeDriver\n"
            "然后重试。不装也能用人工协助模式（不加 --auto）。"
        )


def _ask_yn(prompt: str, default: str = "y") -> bool:
    try:
        answer = input(f"{prompt} (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if not answer:
        answer = default
    return answer in ("y", "yes", "是", "1")


def run_assist(channel: str, keyword: str, city: str, profile: Profile) -> int:
    """人工协助模式：打开预填搜索页，逐条确认投递并记录。"""
    url = applyplan.build_url(channel, keyword, city)
    greeting = applyplan.build_greeting(profile, keyword, channel)

    print(f"\n═══ 人工协助投递: {channel} ═══")
    print(f"  搜索页: {url}")
    print("\n  步骤 1: 浏览器已打开搜索页后，请手动登录（登录永远由你完成）")
    print("  步骤 2: 逐个查看岗位，本工具会给你对应的话术")
    print("  步骤 3: 你确认后手动发送/投递，然后在此记录\n")

    import webbrowser
    webbrowser.open(url)

    print(f"  当前话术（复制使用）:\n  {greeting}\n")

    count = 0
    while True:
        if not _ask_yn("这条已经投递/发送了吗？"):
            break
        count += 1
        try:
            company = input("  公司名（回车跳过）: ").strip()
        except (EOFError, KeyboardInterrupt):
            company = ""
        from .storage import upsert_application
        from .models import Application, gen_id
        import datetime
        app = Application(
            id=gen_id("app", f"{company or channel}{keyword}{datetime.date.today().isoformat()}{count}"),
            company=company or "（未填）", role=keyword, channel=channel,
            date=datetime.date.today().isoformat(), status="applied",
        )
        upsert_application(app)
        if not _ask_yn("继续下一条？"):
            break

    print(f"\n✅ 本轮已记录 {count} 条投递。")
    print("  提醒: HR 的回复请用 `eresume hr \"<消息>\"` 生成草稿，确认后手动发送。")
    return 0


# 实验性：各平台选择器模板（未远程验证，改版即失效，仅供骨架参考）
SELECTOR_TEMPLATES: dict[str, dict] = {
    "shixiseng": {
        "search_box": "input[placeholder*='搜索']",
        "job_item": ".intern-item, .job-card",
        "apply_button": "text=投递",
    },
    "zhilian": {
        "search_box": "input[class*='search']",
        "job_item": ".joblist-box__item",
        "apply_button": "text=投递",
    },
    "bosszhipin": {
        "search_box": "input[class*='search']",
        "job_item": ".job-card-wrapper",
        "apply_button": "text=立即沟通",
    },
}


def run_auto(channel: str, keyword: str, city: str, profile: Profile) -> int:
    """自动模式（实验性骨架）：风险确认 -> Selenium 检查 -> 尝试驱动，失败回退协助。"""
    if not confirm_risks():
        return 1
    ok, msg = check_selenium()
    if not ok:
        print(msg)
        print("已回退到人工协助模式。\n")
        return run_assist(channel, keyword, city, profile)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except Exception:
            service = None
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"⚠ 浏览器启动失败（{e}）。已回退到人工协助模式。\n")
        return run_assist(channel, keyword, city, profile)

    sel = SELECTOR_TEMPLATES.get(channel, SELECTOR_TEMPLATES["shixiseng"])
    url = applyplan.build_url(channel, keyword, city)
    print(f"\n═══ 自动模式（实验性）: {channel} ═══")
    print("  1. 请在弹出的浏览器里手动登录（登录永远由你完成）")
    print("  2. 脚本将尝试自动搜索并逐个询问是否投递")
    print("  3. 选择器可能失效——失效会立即回退，不会强行重试\n")
    driver.get(url)
    try:
        input("登录完成后按回车继续...")
        try:
            box = driver.find_element("css selector", sel["search_box"])
            box.clear()
            box.send_keys(keyword)
            box.submit()
        except Exception:
            raise RuntimeError("选择器失效")
        import time
        time.sleep(3)
        items = driver.find_elements("css selector", sel["job_item"])
        if not items:
            raise RuntimeError("未找到岗位元素")
        count = 0
        for i, item in enumerate(items[:10], 1):
            greeting = applyplan.build_greeting(profile, keyword, channel)
            print(f"\n[岗位 {i}] {item.text[:80]}")
            print(f"  话术: {greeting}")
            if _ask_yn("投递这个岗位？"):
                try:
                    btn = item.find_element("css selector", sel["apply_button"])
                    driver.execute_script("arguments[0].click();", btn)
                    count += 1
                except Exception:
                    print("  ⚠ 投递按钮定位失败，请手动操作")
                from .storage import upsert_application
                from .models import Application, gen_id
                import datetime
                upsert_application(Application(
                    id=gen_id("app", f"{channel}{keyword}{i}{datetime.date.today().isoformat()}"),
                    company="（自动模式）", role=keyword, channel=channel,
                    date=datetime.date.today().isoformat(), status="applied"))
        print(f"\n✅ 本轮自动投递 {count} 条（其余手动确认）。")
        print("  提醒: HR 回复永远由你确认后手动发送，绝不代发。")
    except RuntimeError as e:
        print(f"\n⚠ 自动模式失败（{str(e) or '选择器失效'}），已回退到人工协助模式。")
        return run_assist(channel, keyword, city, profile)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return 0
