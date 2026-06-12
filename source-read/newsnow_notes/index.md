# newsnow 源码阅读系列

实时新闻聚合器——42+ 源抓取、Nitro API、React 19 前端、双层缓存、构建时代码生成。

> 基于 newsnow v0.0.40，MIT 协议，20.7K Star。

## 阅读顺序

1. **[（一）项目概览与架构全景](01-architecture.md)** — 2026-06-11
   - 整体架构、技术栈、核心模块关系、设计哲学

2. **[（二）源配置系统：从 human-friendly 到 machine-friendly](02-source-config.md)** — 2026-06-11
   - pre-sources.ts → sources.json、sub 展开、redirect 跟随、构建时代码生成、拼音索引

3. **[（三）抓取引擎：42 个源、三种策略、一套工具](03-scraping-engine.md)** — 2026-06-11
   - myFetch 封装、JSON API / Cheerio / RSS 三种策略、日期解析、Cloudflare 兼容、glob 导入

4. **[（四）API 层、缓存策略与认证](04-api-and-cache.md)** — 2026-06-11
   - /api/s 缓存状态机、interval vs TTL 双层窗口、批量预热、可选 GitHub OAuth

5. **[（五）前端架构：状态管理、数据流与交互设计](05-frontend.md)** — 2026-06-11
   - Jotai 原子化状态、TanStack Query 数据流、拖拽排序、cmdk 搜索、PWA 更新
