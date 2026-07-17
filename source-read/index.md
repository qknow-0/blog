# 源码阅读

开源项目的源码分析和阅读笔记。

> 📋 [源码阅读规范](README.md) — clone 源码、Git 排除、备份排除的标准化流程

## 文章列表

### TrendRadar

- [（一）项目概览与架构全景](trend_radar/01-architecture.md) — 2026-06-11
- [（二）配置系统与调度引擎](trend_radar/02-config-and-scheduler.md) — 2026-06-11
- [（三）数据采集与存储层](trend_radar/03-crawler-and-storage.md) — 2026-06-11
- [（四）分析引擎：关键词匹配与 AI 过滤](trend_radar/04-analysis-engine.md) — 2026-06-11
- [（五）通知分发、报告生成与 MCP Server](trend_radar/05-notification-and-mcp.md) — 2026-06-11
- [（六）数据库设计：三套 Schema、按日分库与多态关联](trend_radar/06-database-design.md) — 2026-06-11

### QuantDinger

- [（一）项目概览与架构全景](quant_dinger/01-intro.md) — 2026-05-30
- [（二）数据库设计：从 Schema 看系统架构](quant_dinger/02-database.md) — 2026-05-30
- [（三）数据层：多市场数据源与缓存策略](quant_dinger/03-data-layer.md) — 2026-05-30
- [（四）策略引擎：双运行时、回测与实验优化](quant_dinger/04-strategy-engine.md) — 2026-05-30
- [（五）券商执行层：多交易所统一抽象与订单生命周期](quant_dinger/05-execution.md) — 2026-05-30
- [（六）AI 集成：Agent Gateway 与 MCP Server](quant_dinger/06-ai-agent.md) — 2026-05-30
- [（七）基础设施：Docker 部署、认证计费与安全设计](quant_dinger/07-infra.md) — 2026-05-30

### MetaGPT

- [（五）Prompt 系统：AI Agent 的真正壁垒](meta_gpt/05-prompt-system.md) — 2026-07-17
- [（四）值得学的 8 个设计](meta_gpt/04-learnings.md) — 2026-07-17
- [（三）Environment 与消息系统：多 Agent 如何协作](meta_gpt/03-messaging.md) — 2026-07-17
- [（二）Role 系统：一个 Agent 的内部运作](meta_gpt/02-role-system.md) — 2026-07-17
- [（一）架构总览：Role、Action、Environment 三角](meta_gpt/01-architecture.md) — 2026-07-17

### nanobot

- [（一）架构总览：MessageBus + AgentLoop 状态机](nanobot_notes/01-architecture-overview.md) — 2026-06-16
- [（二）Provider 系统：一套接口支持十几个 LLM](nanobot_notes/02-provider-system.md) — 2026-06-16
- [（三）Tool 系统：插件化的工具注册与执行](nanobot_notes/03-tool-system.md) — 2026-06-16
- [（四）Session 与 Memory：Dream 记忆巩固](nanobot_notes/04-session-memory.md) — 2026-06-16
- [（五）Channel 系统：15+ 平台的统一抽象](nanobot_notes/05-channel-system.md) — 2026-06-16
- [（六）WebUI 与 Gateway：前后端通信的多路复用](nanobot_notes/06-webui-gateway.md) — 2026-06-16

### newsnow

- [（一）项目概览与架构全景](newsnow_notes/01-architecture.md) — 2026-06-11
- [（二）源配置系统：从 human-friendly 到 machine-friendly](newsnow_notes/02-source-config.md) — 2026-06-11
- [（三）抓取引擎：42 个源、三种策略、一套工具](newsnow_notes/03-scraping-engine.md) — 2026-06-11
- [（四）API 层、缓存策略与认证](newsnow_notes/04-api-and-cache.md) — 2026-06-11
- [（五）前端架构：状态管理、数据流与交互设计](newsnow_notes/05-frontend.md) — 2026-06-11

### Sequoia-X

- [（一）项目介绍与使用方式](sequoia_x/01-intro.md) — 2026-05-17
- [（二）数据引擎](sequoia_x/02-data-engine.md) — 2026-05-17
- [（三）策略体系](sequoia_x/03-strategies.md) — 2026-05-18
- [（四）飞书推送与基础设施](sequoia_x/04-notify-infra.md) — 2026-05-18
- [（五）测试体系](sequoia_x/05-testing.md) — 2026-05-18
