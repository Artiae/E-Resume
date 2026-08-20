# E-Resume · 你的求职，从此有备而来

**E-Resume** 是一个原创的 AI 求职助手命令行工具：把你的简历档案、求职偏好、投递记录
全部存在本地，用一套清晰的命令完成 **岗位匹配 → 求职材料 → HR 沟通 → 面试准备 → 策略复盘**
的完整闭环。

零第三方依赖（仅 Python 标准库），AI 能力按需接入任意 OpenAI 兼容接口；
没有 API Key 也能用「提示词模式」正常工作。

```
eresume profile ──► 简历档案（本地 JSON）
eresume prefs   ──► 求职偏好（雇佣类型/薪资/公司类型/筛选条件）
      │
      ▼
eresume job add / scrape ──► 岗位库
      │
      ▼
eresume match  ──► 偏好门 + 多维评分 → 结论与建议
      │
      ▼
eresume cover / resume ──► 求职信 / 简历
      │
      ▼
eresume hr     ──► HR 消息意图分类 + 回复草拟/角色扮演
eresume interview ──► 面试准备包
      │
      ▼
eresume apps / status / report ──► 投递记录与复盘
eresume advice ──► 求职策略建议
```

## ✨ 特色能力

| 能力 | 说明 |
|------|------|
| **偏好门（硬性过滤）** | 雇佣类型（全职/实习/兼职/合同工）、薪资底线、公司类型排除（如"外包"）、行业排除、语言要求 —— 不满足的岗位直接拦截，附引用依据 |
| **公司类型判定** | 规则分类：小而美 / 外企 / 大厂 / 潜力股 / 国企央企 / 外包，标注依据，提示用企查查/天眼查复核 |
| **实习日薪智能处理** | 实习岗位按日薪报价，不误套全职月薪底线（如 250-400 元/天 → 提示约合 8700 元/月） |
| **HR 消息互动** | 粘贴 HR 真实消息 → 本地意图分类（面试邀请/薪资沟通/拒信…）→ 生成 3 版回复草稿或角色扮演提示词，全部基于你的真实材料 |
| **提示词模式** | 无 API Key 时输出结构化提示词，粘贴到任意 AI 对话即可用；配置 `ERESUME_API_KEY` 后全自动 |
| **实习僧搜索** | 内置零依赖 Python 爬虫（NUXT 载荷解析 + 图标实体剥离），搜索/详情真实可用 |
| **投递渠道图谱** | 18 个渠道的官方入口、攻略、话术与风险提示；按你的状态推荐渠道组合 |
| **本地数据** | 全部数据在 `~/.eresume/`，JSON 明文，无任何云上传 |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/Artiae/E-Resume.git && cd E-Resume

# 2. 直接运行（无需安装）
python -m eresume init

# 3. 建档 + 设偏好（交互式向导）
python -m eresume profile
python -m eresume prefs

# 4. 添加岗位并匹配
python -m eresume job add "<职位描述文本或链接>"
python -m eresume match "<职位描述文本>"

# 5. 生成求职信（无 Key 时输出提示词，粘贴到任意 AI 对话）
python -m eresume cover 字节跳动 "Python开发实习生"

# 6. 处理 HR 消息
python -m eresume hr "您好，方便明天下午3点视频面试吗？"

# 7. 投递记录与报告
python -m eresume apps add 字节跳动 "Python开发实习生" --channel bosszhipin
python -m eresume report
```

也可以安装为命令（可选）：

```bash
pip install -e .
eresume advice
```

## 🔌 接入 AI（可选）

```bash
# OpenAI 兼容接口（也支持 DeepSeek / 通义 / Ollama 等）
export ERESUME_API_KEY=sk-...
export ERESUME_BASE_URL=https://api.openai.com/v1   # 默认
export ERESUME_MODEL=gpt-4o-mini                    # 默认

# 之后 AI 命令自动走 LLM：
python -m eresume cover 字节跳动 "Python开发实习生" --mode auto
python -m eresume advice --mode auto
```

## 📁 项目结构

```
E-Resume/
├── eresume/                  # Python 包（零依赖）
│   ├── cli.py                # 命令行入口
│   ├── wizard.py             # profile / prefs 交互式向导
│   ├── gates.py              # 偏好门（雇佣类型/薪资/公司类型/行业/语言）
│   ├── matcher.py            # 匹配评分引擎
│   ├── company.py            # 公司类型分类器
│   ├── salary.py             # 薪资解析与归一化
│   ├── hrbot.py              # HR 消息意图分类 + 回复生成
│   ├── channels.py           # 投递渠道
│   ├── advisor.py            # 策略建议
│   ├── interview.py          # 面试准备
│   ├── generators.py         # 简历/求职信生成
│   ├── llm.py                # OpenAI 兼容客户端（可选）
│   ├── report.py             # HTML 仪表盘
│   ├── scrapers/shixiseng.py # 实习僧爬虫（Python 零依赖）
│   └── prompts/              # 提示词模板
├── templates/                # 简历/求职信模板（含中文 LaTeX）
├── data/channels.json        # 渠道数据
├── tests/                    # 29 个测试（python tests/run_tests.py）
└── docs/                     # 文档
```

## 🧪 测试

```bash
python tests/run_tests.py     # 零依赖运行器，29 个测试
```

## 🧭 命令速览

| 命令 | 作用 |
|------|------|
| `eresume init` | 初始化数据目录 |
| `eresume profile` | 建立/编辑简历档案 |
| `eresume prefs [--section X]` | 求职偏好向导（雇佣/薪资/公司/行业/地点/强度/成长） |
| `eresume job add <文本或链接>` | 添加岗位 |
| `eresume job scrape -k 关键词 [--city 城市]` | 实习僧搜索 |
| `eresume match <岗位>` | 偏好门 + 评分 → 结论与建议 |
| `eresume resume [--target X]` | 生成 Markdown 简历 |
| `eresume cover <公司> <岗位>` | 生成求职信 |
| `eresume hr "<消息>"` | HR 消息：意图分类 + 回复草稿 |
| `eresume interview <公司>` | 面试准备包 |
| `eresume advice [--section 1-5]` | 求职策略建议 |
| `eresume channels [渠道名|--plan]` | 投递渠道攻略与计划 |
| `eresume apps add/list/update` | 投递记录 |
| `eresume status` | 投递概览 |
| `eresume report` | HTML 报告 |

## 📜 设计原则

- **本地优先**：你的数据只属于你，JSON 明文存储在本地
- **零依赖**：纯标准库，任何有 Python 3.10+ 的机器开箱即用
- **诚实**：不虚构经历、不编造薪资；公司类型判定永远标注依据与置信度
- **可解释**：每个评分/拦截都有原因，不是黑盒
- **AI 可选**：有 Key 全自动，无 Key 提示词模式照常工作

## 许可

MIT License

---

*E-Resume 是独立原创项目，灵感源于社区对 AI 辅助求职的探索。*
