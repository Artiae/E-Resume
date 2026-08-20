"""投递报告：自包含 HTML 仪表盘（无外部依赖）。"""

from __future__ import annotations

import datetime
from pathlib import Path

from .config import data_dir
from .storage import list_applications

STATUS_LABEL = {
    "drafted": "已起草", "applied": "已投递", "interview": "面试中", "offer": "已发offer",
    "hired": "已入职", "rejected": "已拒绝", "no_response": "无回应", "withdrawn": "已撤回",
}

STATUS_COLOR = {
    "drafted": "#8b8b8b", "applied": "#2d7ff9", "interview": "#f59e0b", "offer": "#10b981",
    "hired": "#059669", "rejected": "#ef4444", "no_response": "#9ca3af", "withdrawn": "#6b7280",
}


def build_html() -> str:
    apps = list_applications()
    today = datetime.date.today().isoformat()

    total = len(apps)
    interviews = sum(1 for a in apps if a.status in ("interview", "offer", "hired"))
    offers = sum(1 for a in apps if a.status in ("offer", "hired"))
    hired = sum(1 for a in apps if a.status == "hired")
    pending = sum(1 for a in apps if a.status not in ("hired", "rejected", "no_response", "offer_declined", "withdrawn"))

    # 渠道统计
    from collections import Counter
    chan = Counter(a.channel for a in apps if a.channel)

    rows = []
    for a in sorted(apps, key=lambda x: x.date, reverse=True):
        color = STATUS_COLOR.get(a.status, "#6b7280")
        label = STATUS_LABEL.get(a.status, a.status)
        rows.append(
            f"<tr><td>{a.date}</td><td><b>{a.company}</b></td><td>{a.role}</td>"
            f"<td>{a.channel or '-'}</td><td>{a.fit_score if a.fit_score is not None else '-'}</td>"
            f"<td><span class='badge' style='background:{color}'>{label}</span></td></tr>"
        )
    rows_html = "\n".join(rows) if rows else "<tr><td colspan='6' style='text-align:center;color:#888'>暂无投递记录</td></tr>"

    chan_html = "".join(
        f"<span class='chip'>{k} × {v}</span>" for k, v in chan.most_common(10)
    ) or "<span style='color:#888'>暂无</span>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>E-Resume 投递报告</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; background: #f5f6fa; color: #1f2937; }}
  header {{ background: #111827; color: #fff; padding: 24px 32px; }}
  header h1 {{ margin: 0; font-size: 22px; }}
  header p {{ margin: 4px 0 0; color: #9ca3af; font-size: 13px; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }}
  .card {{ background: #fff; border-radius: 12px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 110px; }}
  .card .num {{ font-size: 28px; font-weight: 700; }}
  .card .label {{ font-size: 13px; color: #6b7280; }}
  .panel {{ background: #fff; margin: 0 32px 24px; border-radius: 12px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .panel h2 {{ margin: 0 0 12px; font-size: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eef0f3; }}
  th {{ color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  .badge {{ color: #fff; padding: 2px 10px; border-radius: 999px; font-size: 12px; }}
  .chip {{ display: inline-block; background: #eef2ff; color: #4338ca; border-radius: 999px; padding: 4px 12px; margin: 2px; font-size: 13px; }}
</style></head><body>
<header>
  <h1>📊 E-Resume 投递报告</h1>
  <p>生成于 {today} · 数据保存在本地 ~/.eresume/applications.json</p>
</header>
<div class="stats">
  <div class="card"><div class="num">{total}</div><div class="label">累计投递</div></div>
  <div class="card"><div class="num">{interviews}</div><div class="label">进入面试</div></div>
  <div class="card"><div class="num">{offers}</div><div class="label">收到 Offer</div></div>
  <div class="card"><div class="num">{hired}</div><div class="label">已入职</div></div>
  <div class="card"><div class="num">{pending}</div><div class="label">进行中</div></div>
</div>
<div class="panel"><h2>渠道分布</h2>{chan_html}</div>
<div class="panel"><h2>投递明细</h2>
<table><thead><tr><th>日期</th><th>公司</th><th>岗位</th><th>渠道</th><th>匹配分</th><th>状态</th></tr></thead>
<tbody>{rows_html}</tbody></table></div>
</body></html>"""


def write_report() -> Path:
    out = data_dir() / "report.html"
    out.write_text(build_html(), encoding="utf-8")
    return out
