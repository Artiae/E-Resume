"""实习僧搜索：Python 零依赖实现。

抓取 Nuxt SSR 页面中的 __NUXT__ 载荷。该载荷是纯 JS 表达式（IIFE），Python 无法 eval，
因此采用「参数映射替换」方案：
  1. 解析 IIFE 尾部的实参列表（JS 数据字面量）-> 得到 形参->实参 映射
  2. 对每个岗位对象 {…} 逐字段正则提取，变量引用通过映射还原
  3. 剥离站点防爬的图标字体实体（无分号 &#xXXXX）

个人使用：自动化访问违反平台 ToS，控制频率。
"""

from __future__ import annotations

import json
import re
from typing import Optional
from urllib import request as urllib_request
from urllib.request import ProxyHandler, build_opener
from urllib.error import HTTPError, URLError
import ssl

BASE_URL = "https://www.shixiseng.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 eresume-shixiseng/0.1")


# ---------------- 抓取 ----------------

def _opener():
    handlers = []
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        v = __import__("os").environ.get(key, "").strip()
        if v:
            handlers.append(ProxyHandler({"https": v, "http": v}))
            break
    return build_opener(*handlers)


def get_page(path: str, timeout: int = 20) -> str:
    url = BASE_URL + path
    opener = _opener()
    req = urllib_request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        raise RuntimeError(f"实习僧返回 HTTP {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"无法连接实习僧（{e.reason}）——检查网络或代理") from e


# ---------------- NUXT 载荷解析 ----------------

def _find_nuxt(html: str) -> str:
    i = html.find("__NUXT__=")
    if i == -1:
        raise RuntimeError("页面未包含 __NUXT__ 数据（结构变化或被拦截）")
    end = html.find("</script>", i)
    if end == -1:
        raise RuntimeError("__NUXT__ 脚本未闭合")
    return html[i + len("__NUXT__="):end]


def _split_top(text: str, sep: str) -> list[str]:
    """按顶层逗号/冒号切分（忽略字符串/数组/对象内部）。"""
    parts: list[str] = []
    depth = 0
    cur = ""
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            cur += ch
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"' or ch == "'":
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            cur += ch
        elif ch in "[{(":
            depth += 1
            cur += ch
        elif ch in "]})":
            depth -= 1
            cur += ch
        elif ch == sep and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _parse_js_value(text: str):
    """解析 JS 数据字面量（字符串/数字/布尔/null/undefined/数组/对象）。"""
    t = text.strip()
    if not t:
        return None
    if t == "undefined" or t == "null":
        return None
    if t == "true":
        return True
    if t == "false":
        return False
    if t.startswith('"') or t.startswith("'"):
        body = t[1:-1]
        return _unescape_js(body)
    if t.startswith("["):
        return [_parse_js_value(x) for x in _split_top(t[1:-1], ",")]
    if t.startswith("{"):
        obj = {}
        for pair in _split_top(t[1:-1], ","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                obj[k.strip().strip('"\'')] = _parse_js_value(v)
        return obj
    try:
        return int(t)
    except ValueError:
        try:
            return float(t)
        except ValueError:
            return None


def _unescape_js(s: str) -> str:
    # 还原 JS 字符串转义（\uXXXX、\\、\" 等）
    def repl(m):
        return chr(int(m.group(1), 16))
    s = re.sub(r"\\u([0-9a-fA-F]{4})", repl, s)
    s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "")
    s = s.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
    return s


def _extract_payload(expr: str) -> tuple[dict, str]:
    """返回 (参数映射, return 对象源码)。search 页为 return {...}；detail 页另有赋值段。"""
    m = re.search(r"function\s*\(([^)]*)\)\s*\{[\s\S]*?return\s*(\{)", expr)
    if not m:
        raise RuntimeError("无法定位 IIFE 结构（页面结构变化）")
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]
    # 找到 return { 的匹配花括号（跳过字符串字面量）
    start = m.start(2)
    depth = 0
    i = start
    while i < len(expr):
        ch = expr[i]
        if ch in ('"', "'"):
            q = ch
            i += 1
            while i < len(expr):
                if expr[i] == "\\":
                    i += 2
                    continue
                if expr[i] == q:
                    break
                i += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    return_body = expr[start:i + 1]
    tail = expr[i + 1:]
    # 尾部形如 })(arg1,arg2,...);（函数体闭合 } 后接调用）
    mm = re.search(r"[})]\s*\(([\s\S]*)\)\s*;?\s*$", tail)
    if not mm:
        raise RuntimeError("无法定位 IIFE 实参列表")
    arg_src = mm.group(1)
    args = [_parse_js_value(a) for a in _split_top(arg_src, ",")]
    mapping = {p: args[j] for j, p in enumerate(params) if j < len(args)}
    return mapping, return_body


def _read_value(src: str, pos: int) -> tuple[str, int]:
    """从 pos 处读取一个 JS 值（字符串/数字/数组/对象），返回 (值源码, 结束下标)。"""
    depth = 0
    in_str = False
    esc = False
    i = pos
    while i < len(src):
        ch = src[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"' or ch == "'":
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
        elif ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
            if depth < 0:
                break
        elif ch == ";" and depth == 0:
            return src[pos:i].strip(), i
        i += 1
    return src[pos:i].strip(), i


def _collect_assignments(expr: str, mapping: dict) -> dict:
    """提取详情页的 `var.field = value;` 赋值（如 k.address="..."）。"""
    m = re.search(r"function\s*\(([^)]*)\)\s*\{", expr)
    if not m:
        return {}
    body = expr[m.end():]
    # 截取到 return 之前
    ret = body.find("return")
    if ret != -1:
        body = body[:ret]
    fields: dict = {}
    # 匹配 `var.field=` 赋值
    for am in re.finditer(r"([a-zA-Z_$][\w$]*)\.([a-zA-Z_$][\w$]*)\s*=\s*", body):
        name = am.group(2)
        if name in fields:
            continue
        value_src, _ = _read_value(body, am.end())
        if not value_src:
            continue
        fields[name] = _resolve(value_src, mapping)
    return fields


def _resolve(value_src: str, mapping: dict):
    """把字段源码（变量名/字面量）解析为 Python 值。"""
    v = value_src.strip()
    if not v:
        return None
    if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", v):
        return mapping.get(v)
    return _parse_js_value(v)


def _extract_jobs(return_body: str, mapping: dict) -> list[dict]:
    """在 return 对象源码中定位 internships 的 data:[ ... ] 并解析每个岗位对象。"""
    m = re.search(r"interns\s*:\s*\{[^{}]*data:\s*\[", return_body)
    if not m:
        raise RuntimeError("载荷中未找到岗位数据")
    start = m.end() - 1  # 指向 '['
    depth = 0
    i = start
    while i < len(return_body):
        ch = return_body[i]
        if ch in ('"', "'"):
            q = ch
            i += 1
            while i < len(return_body):
                if return_body[i] == "\\":
                    i += 2
                    continue
                if return_body[i] == q:
                    break
                i += 1
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    array_src = return_body[start + 1:i]
    jobs = []
    for item in _split_top(array_src, ","):
        item = item.strip()
        if not item.startswith("{"):
            continue
        job = {}
        # 逐字段解析
        for pair in _split_top(item[1:-1], ","):
            if ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            k = k.strip()
            # 嵌套对象字段（如 job_label）跳过，只取标量字段
            if v.strip().startswith("{") or v.strip().startswith("["):
                if v.strip().startswith("["):
                    inner = _resolve(v.strip(), mapping)
                    if isinstance(inner, list):
                        job[k] = inner
                continue
            job[k] = _resolve(v, mapping)
        jobs.append(job)
    return jobs


# ---------------- 字段清洗 ----------------

def strip_icons(value) -> str:
    """剥离站点图标字体实体（无分号 &#xXXXX）与零宽字符。"""
    if not isinstance(value, str):
        return ""
    return re.sub(r"&#x[0-9a-fA-F]{2,6};?", "", value)


def clean_html(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|li|ul|ol|div|h\d|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    import html as _html
    text = _html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None


# ---------------- 结果重塑 ----------------

def _ftype_label(ftype) -> str:
    return "全职" if str(ftype) == "1" else "实习"


def _salary_line(job: dict) -> Optional[str]:
    lo = job.get("minsalary")
    hi = job.get("maxsalary")
    if not isinstance(lo, (int, float)) and not isinstance(hi, (int, float)):
        return None
    lo = int(lo) if isinstance(lo, (int, float)) else None
    hi = int(hi) if isinstance(hi, (int, float)) else None
    if lo is not None and hi is not None and lo != hi:
        return f"{lo}-{hi} 元/天"
    return f"{lo or hi} 元/天"


def to_result(job: dict) -> dict:
    uuid = str(job.get("uuid") or "")
    tags = [str(t) for t in (job.get("c_tags") or []) if t]
    return {
        "id": uuid,
        "title": strip_icons(job.get("name")) or "(未命名)",
        "company": job.get("cname") or None,
        "company_slug": job.get("c_uuid") or None,
        "location": job.get("city") or None,
        "url": f"{BASE_URL}/intern/{uuid}" if uuid else BASE_URL,
        "salary": _salary_line(job),
        "degree": job.get("degree") or None,
        "employment_type": _ftype_label(job.get("ftype")) if job.get("ftype") is not None else None,
        "company_scale": strip_icons(job.get("scale")) or None,
        "industry": job.get("industry") or None,
        "tags": tags,
        "skills": [s for s in (job.get("skill") or []) if isinstance(s, str)],
        "date": None,
    }


def search(keyword: str, city: str = "全国", page: int = 1) -> dict:
    if not keyword.strip():
        raise RuntimeError("需要搜索关键词")
    import urllib.parse
    params = urllib.parse.urlencode({"keyword": keyword.strip(), "city": city})
    if page > 1:
        params += f"&p={page}"
    html = get_page(f"/interns?{params}")
    expr = _find_nuxt(html)
    mapping, return_body = _extract_payload(expr)
    jobs = _extract_jobs(return_body, mapping)
    results = [to_result(j) for j in jobs]
    # 总数：从 return 对象中找 total:
    tm = re.search(r"total:(\d+)", return_body)
    total = int(tm.group(1)) if tm else len(results)
    return {"total": total, "page": page, "results": results}


def detail(uuid: str) -> dict:
    if not re.fullmatch(r"inn_[A-Za-z0-9]+", uuid):
        raise RuntimeError("无效的实习 id")
    html = get_page(f"/intern/{uuid}")
    expr = _find_nuxt(html)
    mapping, return_body = _extract_payload(expr)
    # 详情页载荷通过 `k.字段=值;` 赋值携带数据
    fields = _collect_assignments(expr, mapping)
    if not fields.get("cname") and not fields.get("iname"):
        raise RuntimeError("详情解析失败（结构变化）")

    result = to_result(fields)
    result["title"] = strip_icons(fields.get("iname")) or result["title"]
    result["url"] = f"{BASE_URL}/intern/{uuid}"
    if fields.get("salary_desc"):
        result["salary"] = strip_icons(fields["salary_desc"]) or fields["salary_desc"]
    if str(fields.get("is_part_job")) == "true":
        result["employment_type"] = "兼职"
    result["address"] = fields.get("address") or None
    attraction = fields.get("attraction")
    result["attraction"] = [str(a) for a in attraction] if isinstance(attraction, list) else []
    result["description"] = clean_html(fields.get("content") or fields.get("info"))
    result["requirements"] = clean_html(fields.get("job_requirements"))
    result["weekly_days"] = strip_icons(fields.get("week_time")) or None
    result["duration"] = strip_icons(fields.get("months")) or None
    return result
