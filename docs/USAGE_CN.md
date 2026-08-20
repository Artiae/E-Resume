# E-Resume 中文使用说明

E-Resume 是一个本地运行的 AI 求职助手命令行工具。所有数据存在你本地，零第三方依赖。

## 一、安装

需要 Python 3.10+（无需安装任何第三方包）。

```bash
git clone https://github.com/Artiae/E-Resume.git
cd E-Resume
python -m eresume init        # 初始化数据目录（默认 ~/.eresume）
```

> 小技巧：Windows 上让中文正常显示，先执行 `set PYTHONIOENCODING=utf-8`。
> 想指定数据目录：`set ERESUME_DIR=D:\my-data`。

## 二、第一步：建档 + 偏好（必做）

### 建档 `profile`

```bash
python -m eresume profile
```

交互式向导：姓名、城市、语言、教育、工作/实习经历、核心技能、目标岗位、硬性约束等。
直接回车可跳过；以后可重复运行补充。

### 求职偏好 `prefs`

```bash
python -m eresume prefs                       # 全部设置
python -m eresume prefs --section salary      # 只改薪资部分
python -m eresume prefs --section company     # 只改公司类型
```

偏好是匹配的"红绿灯"：

- **雇佣类型**：全职/实习/兼职/合同工，不匹配的岗位直接拦截
- **薪资**：期望区间 + 硬底线；低于底线直接拦截；实习岗位按日薪处理不误杀
- **公司类型**：小而美/外企/大厂/潜力股/国企央企 按优先级评分；可排除"外包"等
- **行业 / 城市 / 加班文化 / 出差** 等软硬条件

## 三、日常流程

### 1. 收集岗位

```bash
# 方式 A：粘贴职位描述文本
python -m eresume job add "Python后端开发实习生 字节跳动 北京 250-400元/天 实习 负责大模型评测方向"

# 方式 B：实习僧搜索（自动解析，无需登录）
python -m eresume job scrape -k "python" --city "北京"
python -m eresume job scrape -k "前端" --save    # --save 存入岗位库

# 方式 C：实习僧链接
python -m eresume job add "https://www.shixiseng.com/intern/inn_xxxx"

python -m eresume job list    # 查看岗位库
```

### 2. 匹配评估

```bash
python -m eresume match "<职位描述或岗位ID>"
```

输出：**偏好门**（✅/⛔/⚠️ 逐条）+ **评分**（技术/经验/公司类型/职业方向/薪资）+ 综合分
+ 优点/缺口 + 建议。硬性门不通过会明确告诉你为什么，不会盲目打分。

### 3. 生成求职材料

```bash
python -m eresume resume                        # 生成 Markdown 简历
python -m eresume cover 字节跳动 "Python开发实习生"
```

`cover` 默认输出**提示词模式**：复制提示词粘贴到任意 AI 对话（Claude/ChatGPT/DeepSeek）
即可得到定制求职信。配置 API Key 后直接输出结果（见下文"接入 AI"）。

### 4. 处理 HR 消息

```bash
python -m eresume hr "您好，看了您的简历，我们觉得您很适合这个岗位，方便明天下午3点视频面试吗？"
```

- 本地先做**意图分类**：面试邀请 / 笔试邀请 / 约时间 / 加微信 / 薪资沟通 / 拒信 / 已读不回…
- 自动匹配岗位库中该公司岗位，结合你的简历偏好
- 输出提示词 → 粘贴到 AI 对话得到 3 版回复（稳妥/积极/简短）

配置 API Key 后直接生成回复。

### 5. 面试准备

```bash
python -m eresume interview 字节跳动 --role "Python开发实习生" --stage "初面"
```

输出面试准备提示词：可能的问题清单（含 HR 轮）、STAR 映射、一致性问题、薪资谈判要点、
该问面试官的问题。

### 6. 策略建议

```bash
python -m eresume advice              # 完整策略
python -m eresume advice --section 2  # 只看期望校准
```

### 7. 投递渠道

```bash
python -m eresume channels                # 渠道速查
python -m eresume channels 内推           # 某渠道攻略
python -m eresume channels --plan         # 本周投递计划
```

### 8. 记录与复盘

```bash
python -m eresume apps add 字节跳动 "Python开发实习生" --channel bosszhipin --score 75
python -m eresume apps update <ID> --status interview --note "HR 约了周五视频面试"
python -m eresume status                  # 概览
python -m eresume report                  # HTML 报告（浏览器打开）
```

## 四、接入 AI（可选，推荐）

```bash
# 任意 OpenAI 兼容接口
export ERESUME_API_KEY=sk-xxxx
export ERESUME_BASE_URL=https://api.openai.com/v1    # 可换 DeepSeek/通义/Ollama 地址
export ERESUME_MODEL=gpt-4o-mini

# 之后所有 AI 命令自动走 LLM：
python -m eresume cover 字节跳动 "Python开发实习生" --mode auto
python -m eresume hr "..." --mode-llm auto
python -m eresume advice --mode auto
```

Windows（PowerShell）用 `$env:ERESUME_API_KEY="sk-..."`。

## 五、实习僧爬虫说明

- 零依赖 Python 实现，解析 Nuxt SSR 载荷，剥离站点图标字体实体
- **个人使用**：自动化访问违反平台条款，请控制频率
- 结构变化时可能解析失败，会给出明确错误提示

## 六、数据与隐私

- 数据目录 `~/.eresume/`（或 `ERESUME_DIR` 指定）：`profile.json`、`preferences.json`、
  `postings.json`、`applications.json`、`report.html`
- 全部明文 JSON，不上传任何云端；LLM 调用仅在你配置 API Key 后发生
- 简历含个人信息的文件默认被 `.gitignore` 排除，不会误提交

## 七、常见问题

| 问题 | 解决 |
|------|------|
| 中文乱码 | `set PYTHONIOENCODING=utf-8` |
| `job add` 解析不出标题/薪资 | 粘贴格式化的多行 JD（标题一行，薪资单独一行）效果最好；URL 优先用实习僧链接 |
| 实习僧搜索失败 | 网络/代理问题（设置 HTTPS_PROXY），或站点结构更新 |
| 想要其他平台搜索 | BOSS直聘/智联等有强反爬，E-Resume 将其作为投递渠道指导而非爬虫 |
| 不想用 AI | 提示词模式完全够用，把提示词粘贴到任何 AI 即可 |
