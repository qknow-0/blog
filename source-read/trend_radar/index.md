# TrendRadar 源码阅读系列

热点新闻聚合 + 关键词/AI 过滤 + 多渠道推送——一个完整的 Python 全栈项目，从配置加载到 MCP Server 的源码级分析。

## 阅读顺序

1. **[（一）项目概览与架构全景](01-architecture.md)** — 2026-06-11
   - 核心 Pipeline、目录结构、AppContext 门面模式、Storage 抽象层

2. **[（二）配置系统与调度引擎](02-config-and-scheduler.md)** — 2026-06-11
   - config.yaml 12 段配置、timeline.yaml 时间线模型、frequency_words DSL、Scheduler 调度

3. **[（三）数据采集与存储层](03-crawler-and-storage.md)** — 2026-06-11
   - NewsNow API 抓取、RSS 并行采集、SQLite 本地存储、S3 远程存储、StorageManager 自动切换

4. **[（四）分析引擎：关键词匹配与 AI 过滤](04-analysis-engine.md)** — 2026-06-11
   - 加权评分算法、频率统计、关键词 DSL 匹配、AI 兴趣分类、LiteLLM 多模型支持

5. **[（五）通知分发、报告生成与 MCP Server](05-notification-and-mcp.md)** — 2026-06-11
   - 9 通道推送、多账号路由、HTML 报告生成、FastMCP 26 个工具、AI 可查询热点数据

6. **[（六）数据库设计：三套 Schema、按日分库与多态关联](06-database-design.md)** — 2026-06-11
   - 15 张表、双库按日分文件、URL 去重、排名时间线、标签版本化、Token 成本控制
