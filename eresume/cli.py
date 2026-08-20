"""E-Resume 命令行入口。

用法:
  eresume init
  eresume profile                 # 建档向导
  eresume prefs [--section X]     # 求职偏好向导
  eresume job add <url|文本>       # 添加岗位
  eresume job list
  eresume job scrape -k 关键词 [--city 城市] [--source shixiseng]
  eresume match <岗位ID|url|文本>  # 偏好门 + 评分
  eresume resume [--target 岗位]
  eresume cover <公司> <岗位> [--posting ID] [--mode auto|llm|prompt]
  eresume hr "<HR消息>" [--company X] [--mode roleplay|draft] [--channel X]
  eresume interview <公司> [--role X] [--stage X] [--posting ID]
  eresume advice [--section 1-5]
  eresume channels [渠道名|--plan]
  eresume apps add|update|list
  eresume status
  eresume report
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, APP_NAME, APP_SLOGAN
from . import storage
from .wizard import run_profile_wizard, run_prefs_wizard
from .posting_parse import parse_posting_text
from .models import Posting, Application, gen_id
from .matcher import evaluate, render
from . import matcher
from . import channels as channels_mod
from . import advisor, interview as interview_mod, generators, hrbot, report as report_mod, llm
from .scrapers import shixiseng
from .salary import salary_display


def _print(text: str) -> None:
    sys.stdout.write(text + "\n")


def cmd_init(_: argparse.Namespace) -> int:
    storage.init_workspace()
    return 0


def cmd_profile(_: argparse.Namespace) -> int:
    run_profile_wizard()
    return 0


def cmd_prefs(args: argparse.Namespace) -> int:
    run_prefs_wizard(section=args.section or "")
    return 0


def _resolve_posting_input(raw: str, source: str) -> Posting:
    """从 岗位ID / URL / 文本 解析出 Posting（自动保存）。"""
    # 已有 ID？
    existing = storage.get_posting(raw.strip())
    if existing:
        return existing
    # 实习僧 URL -> 详情抓取
    if "shixiseng.com" in raw:
        m = __import__("re").search(r"/intern/(inn_[A-Za-z0-9]+)", raw)
        if m:
            d = shixiseng.detail(m.group(1))
            p = Posting(
                id=gen_id("job", raw),
                source="shixiseng", title=d["title"], company=d.get("company") or "",
                employment_type=d.get("employment_type") or "",
                salary_text=d.get("salary") or "", location=d.get("location") or "",
                description=(d.get("description") or "") + "\n" + (d.get("requirements") or ""),
                url=d["url"], tags=d.get("tags") or [],
            )
            storage.upsert_posting(p)
            return p
    # 普通文本
    p = parse_posting_text(raw, source=source)
    p.id = gen_id("job", raw)
    storage.upsert_posting(p)
    return p


def cmd_job(args: argparse.Namespace) -> int:
    sub = args.job_sub
    if sub == "add":
        raw = args.input
        p = _resolve_posting_input(raw, "url" if raw.startswith("http") else "text")
        _print(f"✅ 已保存岗位 [{p.id}]")
        _print(f"   {p.title or '(未解析出标题)'} @ {p.company or '未知'} | {p.employment_type or '类型未知'} | {salary_display(p)} | {p.location or ''}")
        _print(f"   {p.url or '（无链接）'}")
        return 0
    if sub == "list":
        postings = storage.list_postings()
        if not postings:
            _print("暂无岗位。用 `eresume job add <链接或文本>` 添加。")
            return 0
        for p in postings:
            _print(f"[{p.id}] {p.title or '(无标题)'} @ {p.company or '?'} | {p.employment_type or '?'} | {salary_display(p)}")
        return 0
    if sub == "scrape":
        source = args.source or "shixiseng"
        if source == "shixiseng":
            r = shixiseng.search(args.keyword, args.city or "全国", args.page or 1)
            _print(f"共 {r['total']} 个实习岗位（第 {r['page']} 页，显示 {len(r['results'])}）")
            for j in r["results"]:
                _print(f"  [{j['id']}] {j['title']} | {j['company']} | {j['location']} | {j['salary'] or '面议'} | {j['degree'] or '-'} | {j['employment_type']}")
                if args.save:
                    p = Posting(
                        id=j["id"], source="shixiseng", title=j["title"], company=j["company"] or "",
                        employment_type=j.get("employment_type") or "", salary_text=j.get("salary") or "",
                        location=j.get("location") or "", url=j["url"], tags=j.get("tags") or [],
                    )
                    storage.upsert_posting(p)
            if args.save:
                _print("（已保存到岗位库）")
            return 0
        _print(f"暂不支持来源: {source}（可用 shixiseng）")
        return 1
    _print("未知的 job 子命令")
    return 1


def cmd_match(args: argparse.Namespace) -> int:
    from .storage import load_profile, load_preferences
    profile = load_profile()
    prefs = load_preferences()
    if not prefs.employment_types:
        _print("⚠ 尚未设置求职偏好，匹配结果不完整。先运行 `eresume prefs`。")
    posting = _resolve_posting_input(args.input, "url" if args.input.startswith("http") else "text")
    ev = evaluate(posting, profile, prefs)
    _print(render(ev))
    if not ev.blocked:
        _print("下一步: `eresume cover <公司> <岗位> --posting " + posting.id + "` 生成求职信")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    from .storage import load_profile
    profile = load_profile()
    _print(generators.resume_markdown(profile, target=args.target or ""))
    return 0


def cmd_cover(args: argparse.Namespace) -> int:
    from .storage import load_profile, load_preferences
    profile = load_profile()
    prefs = load_preferences()
    posting = storage.get_posting(args.posting) if args.posting else None
    if not posting and args.posting:
        _print(f"未找到岗位 {args.posting}")
        return 1
    out = generators.cover_letter(profile, prefs, posting, args.company, args.role,
                                  channel=args.channel or "", mode=args.mode or "auto")
    _print(out)
    return 0


def cmd_hr(args: argparse.Namespace) -> int:
    from .storage import load_profile, load_preferences
    profile = load_profile()
    prefs = load_preferences()
    posting = None
    if args.company:
        for p in storage.list_postings():
            if p.company and args.company in p.company:
                posting = p
                break
    mode = args.mode or "draft"
    if mode == "roleplay":
        _print(hrbot.analyze_message(args.message))
        _print(hrbot.handle_roleplay(args.message, profile, prefs, posting, channel=args.channel or "default", mode=args.mode_llm or "auto"))
    else:
        _print(hrbot.analyze_message(args.message))
        _print(hrbot.handle_draft(args.message, profile, prefs, posting, channel=args.channel or "default", mode=args.mode_llm or "auto"))
    return 0


def cmd_interview(args: argparse.Namespace) -> int:
    from .storage import load_profile, load_preferences
    profile = load_profile()
    prefs = load_preferences()
    posting = storage.get_posting(args.posting) if args.posting else None
    feedback = ""
    for a in storage.list_applications():
        if a.company and args.company in a.company:
            feedback = "\n".join(a.notes)
            break
    out = interview_mod.build_prep(args.company, args.role or "（岗位未指定）", args.stage or "初面",
                                   profile, prefs, posting, feedback=feedback, mode=args.mode or "auto")
    _print(out)
    return 0


def cmd_advice(args: argparse.Namespace) -> int:
    from .storage import load_profile, load_preferences
    profile = load_profile()
    prefs = load_preferences()
    _print(advisor.quick_checks(profile, prefs))
    section = args.section or ""
    out = advisor.run_advice(profile, prefs, section=section, mode=args.mode or "auto")
    _print(out)
    return 0


def cmd_channels(args: argparse.Namespace) -> int:
    if args.plan:
        from .storage import load_preferences
        _print(channels_mod.weekly_plan(load_preferences()))
        return 0
    if args.name:
        _print(channels_mod.detail(args.name))
        return 0
    from .storage import load_preferences
    _print(channels_mod.cheat_sheet())
    _print(channels_mod.recommend(load_preferences()))
    return 0


def cmd_apps(args: argparse.Namespace) -> int:
    sub = args.apps_sub
    if sub == "list":
        apps = storage.list_applications()
        if not apps:
            _print("暂无投递记录。用 `eresume apps add` 记录第一条。")
            return 0
        for a in apps:
            _print(f"[{a.id}] {a.date} {a.company} | {a.role} | 渠道:{a.channel or '-'} | 状态:{a.status} | 评分:{a.fit_score or '-'}")
        return 0
    if sub == "add":
        a = Application(
            id=gen_id("app", f"{args.company}{args.role}{args.date}"),
            company=args.company, role=args.role or "", channel=args.channel or "",
            date=args.date or "", status=args.status or "applied",
        )
        if args.score:
            try:
                a.fit_score = int(args.score)
            except ValueError:
                pass
        storage.upsert_application(a)
        _print(f"✅ 已记录投递 [{a.id}] {a.company} {a.role}")
        return 0
    if sub == "update":
        app = next((x for x in storage.list_applications() if x.id == args.id), None)
        if not app:
            _print(f"未找到投递记录 {args.id}")
            return 1
        if args.status:
            app.status = args.status
        if args.note:
            import datetime
            app.notes.append(f"{datetime.date.today().isoformat()} {args.note}")
        storage.upsert_application(app)
        _print(f"✅ 已更新 [{app.id}] 状态={app.status}")
        return 0
    _print("未知的 apps 子命令")
    return 1


def cmd_status(_: argparse.Namespace) -> int:
    apps = storage.list_applications()
    from collections import Counter
    cnt = Counter(a.status for a in apps)
    _print(f"累计投递: {len(apps)}")
    if cnt:
        _print("状态分布: " + ", ".join(f"{k}×{v}" for k, v in cnt.most_common()))
    return 0


def cmd_report(_: argparse.Namespace) -> int:
    out = report_mod.write_report()
    _print(f"✅ 报告已生成: {out}")
    _print(f"   浏览器打开: file://{out.as_posix()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eresume",
        description=f"{APP_NAME} — {APP_SLOGAN}（v{__version__}）",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化数据目录")
    sub.add_parser("profile", help="建立/编辑求职者档案")
    p = sub.add_parser("prefs", help="设置求职偏好")
    p.add_argument("--section", choices=["employment", "salary", "company", "industry", "location", "workload", "growth"])

    p = sub.add_parser("job", help="岗位管理")
    jsub = p.add_subparsers(dest="job_sub")
    ja = jsub.add_parser("add", help="添加岗位（链接或文本）")
    ja.add_argument("input")
    jsub.add_parser("list", help="列出岗位")
    js = jsub.add_parser("scrape", help="从招聘平台抓取")
    js.add_argument("-k", "--keyword", required=True)
    js.add_argument("--city", default="全国")
    js.add_argument("--page", type=int, default=1)
    js.add_argument("--source", default="shixiseng")
    js.add_argument("--save", action="store_true")

    p = sub.add_parser("match", help="匹配评估（偏好门+评分）")
    p.add_argument("input")

    p = sub.add_parser("resume", help="生成 Markdown 简历")
    p.add_argument("--target", default="")

    p = sub.add_parser("cover", help="生成求职信")
    p.add_argument("company")
    p.add_argument("role")
    p.add_argument("--posting")
    p.add_argument("--channel", default="")
    p.add_argument("--mode", choices=["auto", "llm", "prompt"], default="auto")

    p = sub.add_parser("hr", help="HR 消息互动")
    p.add_argument("message")
    p.add_argument("--company")
    p.add_argument("--mode", choices=["roleplay", "draft"], default="draft")
    p.add_argument("--mode-llm", dest="mode_llm", choices=["auto", "llm", "prompt"], default="auto")
    p.add_argument("--channel", default="default")

    p = sub.add_parser("interview", help="面试准备")
    p.add_argument("company")
    p.add_argument("--role", default="")
    p.add_argument("--stage", default="初面")
    p.add_argument("--posting")
    p.add_argument("--mode", choices=["auto", "llm", "prompt"], default="auto")

    p = sub.add_parser("advice", help="求职策略建议")
    p.add_argument("--section", default="")
    p.add_argument("--mode", choices=["auto", "llm", "prompt"], default="auto")

    p = sub.add_parser("channels", help="投递渠道")
    p.add_argument("name", nargs="?", default="")
    p.add_argument("--plan", action="store_true")

    p = sub.add_parser("apps", help="投递记录")
    asub = p.add_subparsers(dest="apps_sub")
    asub.add_parser("list")
    aa = asub.add_parser("add")
    aa.add_argument("company")
    aa.add_argument("role", nargs="?", default="")
    aa.add_argument("--channel", default="")
    aa.add_argument("--date", default="")
    aa.add_argument("--status", default="applied")
    aa.add_argument("--score", default="")
    au = asub.add_parser("update")
    au.add_argument("id")
    au.add_argument("--status", default="")
    au.add_argument("--note", default="")

    sub.add_parser("status", help="投递概览")
    sub.add_parser("report", help="生成 HTML 报告")

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    handler = {
        "init": cmd_init,
        "profile": cmd_profile,
        "prefs": cmd_prefs,
        "job": cmd_job,
        "match": cmd_match,
        "resume": cmd_resume,
        "cover": cmd_cover,
        "hr": cmd_hr,
        "interview": cmd_interview,
        "advice": cmd_advice,
        "channels": cmd_channels,
        "apps": cmd_apps,
        "status": cmd_status,
        "report": cmd_report,
    }.get(args.command)
    if not handler:
        parser.print_help()
        return 0
    try:
        return handler(args) or 0
    except (RuntimeError, ValueError) as e:
        _print(f"错误: {e}")
        return 1
    except KeyboardInterrupt:
        _print("\n已取消")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
