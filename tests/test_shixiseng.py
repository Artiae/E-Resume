"""实习僧载荷解析测试（合成夹具，无网络）。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eresume.scrapers import shixiseng

# 模拟搜索页 __NUXT__：IIFE + return 对象 + 图标实体（无分号）
SEARCH_FIXTURE = """__NUXT__=(function(a,b,c){return {layout:"default",data:[{interns:{total:2,pageNumber:1,data:[
{uuid:"inn_mz8b1aexey65",name:"&#xee71&#xf0aa开发实习&#xf010",cname:"埃森哲",city:"大连",minsalary:150,maxsalary:150,degree:"本科",ftype:"0",scale:"&#xe2c0&#xf74f以上",industry:"互联网/游戏/软件",c_uuid:"com_5oltrfxbxwg5",skill:[],c_tags:["世界五百强","可转正"],day:a,type:"intern"},
{uuid:"inn_dl5z5hbve2hi",name:"AI产品实习生",cname:"保亚科技",city:"北京",minsalary:200,maxsalary:300,degree:"硕士",ftype:"0",scale:b,industry:"人工智能",c_uuid:"com_qwjjf9rk0iu0",skill:["python"],c_tags:["不加班"],day:c,type:"intern"}
]}}]}}})("1天前","500-2000人","3个月");</script>"""

DETAIL_FIXTURE = """__NUXT__=(function(a,b,c,d){k.address="辽宁/大连/甘井子区 蔡大岭软件园29号楼";k.attraction=["可转正实习"];
k.iname="python开发实习生";k.cname="埃森哲";k.city="大连";k.degree="本科";k.ftype="0";
k.minsalary=a;k.maxsalary=a;k.is_part_job=b;k.salary_desc="150/天";
k.content="<p>负责 Python 相关开发</p><p>支持大模型应用方向</p>";k.job_requirements="本科及以上";
return {fig:{_app:{basePath:c}}})(150,"false",null,"\\u002F");</script>"""


def test_strip_icons():
    assert shixiseng.strip_icons("&#xee71&#xf0aa开发实习&#xf010") == "开发实习"
    assert shixiseng.strip_icons("AI产品实习生") == "AI产品实习生"
    assert shixiseng.strip_icons(None) == ""


def test_clean_html():
    assert shixiseng.clean_html("<p>负责 <b>AI</b> 平台</p><p>第二段 &amp; 更多</p>") == "负责 AI 平台\n第二段 & 更多"
    assert shixiseng.clean_html("") is None


def test_extract_payload_search():
    expr = shixiseng._find_nuxt(SEARCH_FIXTURE)
    mapping, return_body = shixiseng._extract_payload(expr)
    assert mapping["a"] == "1天前"
    assert mapping["b"] == "500-2000人"
    jobs = shixiseng._extract_jobs(return_body, mapping)
    assert len(jobs) == 2
    r0 = shixiseng.to_result(jobs[0])
    assert r0["title"] == "开发实习"
    assert r0["company"] == "埃森哲"
    assert r0["salary"] == "150 元/天"
    assert r0["employment_type"] == "实习"
    assert r0["url"] == "https://www.shixiseng.com/intern/inn_mz8b1aexey65"
    r1 = shixiseng.to_result(jobs[1])
    assert r1["salary"] == "200-300 元/天"


def test_extract_payload_detail():
    expr = shixiseng._find_nuxt(DETAIL_FIXTURE)
    mapping, _ = shixiseng._extract_payload(expr)
    fields = shixiseng._collect_assignments(expr, mapping)
    assert fields["iname"] == "python开发实习生"
    assert fields["cname"] == "埃森哲"
    assert fields["attraction"] == ["可转正实习"]
    assert fields["is_part_job"] == "false"
    r = shixiseng.to_result(fields)
    r["title"] = shixiseng.strip_icons(fields.get("iname")) or r["title"]
    assert r["title"] == "python开发实习生"
    assert shixiseng.clean_html(fields.get("content")) == "负责 Python 相关开发\n支持大模型应用方向"
