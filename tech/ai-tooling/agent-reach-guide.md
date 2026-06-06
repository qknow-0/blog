# Agent Reach：给 AI Agent 装上互联网能力

> AI Agent 能写代码、改文档、管项目——但让它去网上找点东西就抓瞎了。Twitter API 要付费、Reddit 封服务器 IP、YouTube 没有现成字幕接口。Agent Reach 把这些问题都封装好了——一句话安装，Agent 自己会配，装完就能搜网页、读视频、看帖子。

## 一句话定位

Agent Reach 是一个脚手架——它帮你选好、装好、配好那些 Agent 访问互联网需要的基础工具，然后 Agent 直接调这些上游工具，不经过任何中间层。

```
安装前：Agent 不知道 Twitter 用什么读、Reddit 怎么绕封、YouTube 字幕怎么提取
安装后：Agent 读了 SKILL.md，知道"搜推文用 twitter-cli"、"读视频用 yt-dlp"
```

## 为什么需要它

AI Agent 有八个典型的信息获取盲区：

| 需求 | 痛点 |
|------|------|
| 📺 看视频 | YouTube/B站字幕提取——没有现成的免费 API |
| 🐦 搜社交媒体 | Twitter/X API 付费 + 限制多 |
| 📖 搜论坛 | Reddit 封服务器 IP，爬虫拿不到 |
| 📕 国内平台 | 小红书、抖音需要登录 + 反爬 |
| 🔍 搜索引擎 | 免费 API 质量差，付费的需要 key |
| 🌐 读网页 | 抓回来一堆 HTML 标签，Agent 没法读 |
| 📦 GitHub | 公开能读，Issue/PR/搜索需要认证 |
| 🎙️ 播客 | 音频转文字需要 Whisper + 转录流程 |

Agent Reach 对每个渠道选了一个上游工具——不需要你决策「用什么、怎么装、怎么配」。

## 安装——一句话

```bash
# 复制这句话给你的 Agent（Claude Code / OpenClaw / Cursor / Windsurf）
帮我安装 Agent Reach：https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
```

Agent 自己会完成：

1. `pip install agent-reach`
2. 检测并安装系统依赖（Node.js、gh CLI、mcporter、twitter-cli、yt-dlp、rdt-cli 等）
3. 通过 MCP 接入搜索引擎（Exa，免费）
4. 判断本地还是服务器，给对应建议
5. 注册 SKILL.md——之后 Agent 遇到「搜推文」「看视频」自己知道该调什么

装完后一条命令看状态：

```bash
agent-reach doctor
# ✅ web: Jina Reader — 可用
# ✅ youtube: yt-dlp — 可用
# ✅ github: gh CLI — 已登录
# ⚠️ twitter: twitter-cli — 未配置（需要 Cookie）
# ❌ reddit: rdt-cli — 未登录
```

## 支持的渠道

| 渠道 | 装好即用 | 配置后解锁 |
|------|---------|-----------|
| 🌐 网页 | 读任意网页（Jina Reader） | — |
| 📺 YouTube | 字幕提取 + 视频搜索 | — |
| 📡 RSS | 读任意 RSS/Atom 源 | — |
| 🔍 全网搜索 | — | Exa 语义搜索（免费，自动配） |
| 📦 GitHub | 读公开仓库 + 搜索 | 私有仓库、Issue/PR（`gh auth login`） |
| 🐦 Twitter/X | 读单条推文 | 搜索、时间线（Cookie 配置） |
| 📺 B站 | 字幕提取 + 搜索 | 服务器端（代理配置） |
| 📖 Reddit | — | 搜索、读帖、评论（rdt-cli + Cookie） |
| 📕 小红书 | — | 阅读、搜索、发帖（Cookie 配置） |
| 🎵 抖音 | — | 视频解析、无水印下载（Cookie） |
| 💼 LinkedIn | 读公开页面 | Profile、公司、职位搜索 |
| 💬 微信公众号 | 搜索 + 全文 Markdown | — |
| 📰 微博 | 热搜、搜索、动态、评论 | — |
| 💻 V2EX | 热门、帖子详情、用户信息 | — |
| 📈 雪球 | 股票行情、搜索、排行 | — |
| 🎙️ 小宇宙 | — | 播客转文字（Whisper） |

## 设计哲学——脚手架，不是框架

```
channels/
├── web.py          → Jina Reader     ← 不喜欢？换成 Firecrawl
├── twitter.py      → twitter-cli       ← 不喜欢？换成官方 API
├── youtube.py      → yt-dlp          ← 不喜欢？换成 YouTube API
├── github.py       → gh CLI          ← 不喜欢？换成 PyGithub
├── bilibili.py     → yt-dlp          ← 不喜欢？换成 bilibili-api
├── reddit.py       → rdt-cli         ← 不喜欢？换成 PRAW
├── xiaohongshu.py  → mcporter MCP    ← 不喜欢？换成其他 XHS 工具
└── ...
```

每个渠道背后是一个独立的上游工具，Agent Reach 不包装它们——Agent 直接调。你不满意某个渠道选的工具？换掉就行。Agent Reach 只是帮你把「选什么、怎么装、怎么配」这个决策做完了。

这和 Webnovel Writer 的 Story System 有类似的思维——**框架是约束，脚手架是起点**。

## 三种使用层次

### 层次一：装好即用（零配置）

```bash
# 在 Claude Code 里直接说
"帮我看看这个网页写了什么"                                    # → Jina Reader
"这个 YouTube 视频讲了什么"                                  # → yt-dlp 提取字幕
"搜一下 GitHub 上 Python 的 LLM 框架"                       # → gh search repos
"这个 GitHub 仓库是干嘛的"                                   # → gh repo view
"订阅这个 RSS"                                              # → feedparser
"帮我看看微博热搜"                                           # → 微博热搜榜
"V2EX 上最热门的帖子有哪些"                                   # → V2EX API
```

### 层次二：配置后解锁

```bash
# Cookie 配置——用 Chrome 插件导出，发给 Agent
"帮我配 Twitter"    # → 引导你用 Cookie-Editor 导出 Cookie
"帮我配小红书"       # → 同上
"帮我登录 GitHub"    # → gh auth login
"帮我配代理"         # → 服务器端访问 B 站需要
```

Cookie 只存在本地，代码开源可审查。

### 层次三：自定义替换

```bash
# 改 channels/web.py
# from: web.py → Jina Reader
# to:   web.py → Firecrawl
```

不需要 fork 整个项目——只改那个 channel 文件就行。

## 实际场景

### Agent 帮你做技术调研

```
你："我想了解一下最新的 LLM Agent 框架，帮我做个调研"

Agent：
1. agent-reach 搜 GitHub: gh search repos "LLM agent framework" --sort stars
2. agent-reach 搜网页: 搜"LLM agent framework 2026"
3. 读每个仓库的 README: gh repo view owner/repo
4. 搜 Reddit 讨论: rdt-cli search "best LLM agent framework"
5. 看 Twitter 评价: twitter search "LLM agent framework"
6. 汇总成调研报告
```

没有 Agent Reach 时，Agent 在第一步就卡住了——「我无法访问 GitHub API，请手动提供仓库信息」。

### Agent 帮你做竞品分析

```
你："帮我分析一下小红书上的竞品 A 的口碑"

Agent：
1. xiaohongsho-cli search "竞品A"
2. 读每条帖子的全文和评论
3. 情感分析 + 高频关键词提取
4. 汇总成口碑报告
```

小红书需要登录 + 设备注册才能搜索。Agent Reach 的 xiaohongshu channel 把这些封装好了，Agent 不需要知道细节。

### Agent 帮你录播客笔记

```
你："小宇宙上最新一期关于 AI 的播客，帮我做笔记"

Agent：
1. 搜索小宇宙播客: podcast-cli search "AI"
2. 下载音频
3. Whisper 转录成文字
4. LLM 提取要点 + 时间轴
5. 生成 Markdown 笔记
```

## Agent Reach doctor——一条命令诊断

```bash
$ agent-reach doctor

🔍 Agent Reach 诊断报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ web           Jina Reader 可用
✅ youtube       yt-dlp v2024.12.13
✅ github        gh CLI v2.93.0（已登录: panniantong）
✅ rss           feedparser 可用
✅ weibo         微博热搜 + 搜索 可用
✅ v2ex          V2EX API 可用
✅ xueqiu        雪球行情 + 搜索 可用
⚠️  twitter      twitter-cli 已安装，未配置 Cookie
⚠️  bilibili     yt-dlp 可用（本地），服务器需要代理
⚠️  xiaohongshu  mcporter 已安装，未配置 Cookie
❌ reddit        rdt-cli 未安装 → brew install rdt-cli
❌ douyin        mcporter 未配置 Cookie
⚠️  linkedin     linkedin-mcp 未配置 Cookie
```

每个渠道四种状态：✅ 可用 / ⚠️ 工具装了但缺配置 / ❌ 工具没装 / 🔧 需要手动处理。不是笼统的「好像不太对」，是精确到每个渠道「哪里不通、怎么修」。

## 和 Webnovel Writer 的对比

两个项目都是 Claude Code 生态里的工具，但它们代表了两种不同的设计路线：

| | Webnovel Writer | Agent Reach |
|---|---|---|
| 定位 | 领域框架——网文创作 | 基础设施脚手架——互联网访问 |
| 安装方式 | Marketplace plugin | Agent 自安装 |
| 核心机制 | Story System 提交链 | 上游工具直调 + SKILL.md |
| Agent 角色 | 按流水线执行创作 | 遇到需求时调对应工具 |
| 可替换性 | 低（深度集成 prompt 和 flow） | 高（每个 channel 独立可换） |
| 适用面 | 窄——只做网文 | 宽——任何需要上网的 Agent |

一个给 Agent 装上了「记忆和一致性」，一个给 Agent 装上了「眼睛和耳朵」。两个一起用——Agent 既能上网搜信息，又能把搜到的信息纳入一致性系统追踪。

这就是 Claude Code 生态的演进路径——不是造一个全能 Agent，而是通过专项工具让 Agent 的能力边界一点点外扩。
