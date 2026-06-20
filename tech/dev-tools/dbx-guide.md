# DBX：15MB 的数据库管理工具，干掉 400MB 的 DBeaver

> 一个数据库客户端为什么要 400MB？因为它带了整个 Java 虚拟机。DBX 用 Rust 重写了这一切——15MB，50+ 数据库，还内置了 AI。

## 是什么

[DBX](https://github.com/t8y2/dbx) 是一个开源（Apache-2.0）的轻量级跨平台数据库管理工具。Rust + Tauri 2 + Vue 3 构建，v0.5.30，GitHub 5,300+ stars（2026 年 4 月创建，两个月不到）。

```text
传统数据库客户端 = Java JRE + SWT/Eclipse 框架 + JDBC 驱动 → 400MB+
DBX              = Rust 原生 + 系统 WebView         → 15MB
```

核心定位：

- **15MB 单文件**——不需要 Java JRE、不需要 Python venv、不捆绑 Chromium
- **50+ 数据库**——MySQL、PostgreSQL、SQLite、Redis、MongoDB、DuckDB、ClickHouse、SQL Server、Oracle、Elasticsearch 等等
- **AI 内建**——自然语言转 SQL、查询解释、优化建议、错误修复
- **MCP 协议**——Claude Code、Cursor 等 AI Agent 可以直接查你的数据库
- **桌面 + Docker + Web**——同一套代码，三种部署方式

## 和主流产品对比

### 体积和性能

| | DBX | DBeaver | DataGrip | Navicat | TablePlus |
|---|---|---|---|---|---|
| 安装包 | **15 MB** | 400 MB+ | 800 MB+ | 200 MB+ | 30-50 MB |
| 运行时内存 | **~80 MB** | 500 MB+ | 1 GB+ | 300 MB+ | 80-150 MB |
| 启动速度 | **~1 秒** | 4-6 秒 | 5-8 秒 | 2-3 秒 | 1-2 秒 |
| 运行时依赖 | **无** | Java JRE | JVM | 无 | 无 |
| 技术栈 | Rust/Tauri | Java/SWT | Java/JetBrains | C++ | 原生 |

差两个数量级的体积，不是因为 DBeaver 功能多——而是因为它带着整个 Java 生态跑。

### 功能对比

| | DBX | DBeaver | DataGrip | Navicat | TablePlus |
|---|---|---|---|---|---|
| 数据库数量 | **50+** | 50+ | 40+ | 30+ | 10+ |
| AI SQL 助手 | **✅ 内建** | ⚠️ 插件 | ❌ | ❌ | ❌ |
| MCP 协议 | **✅** | ❌ | ❌ | ❌ | ❌ |
| Docker/Web | **✅** | ❌ | ❌ | ❌ | ❌ |
| ER 图 | ✅ | ✅ | ✅ | ✅ | ❌ |
| Schema Diff | ✅ | ✅ | ✅ | ✅ | ❌ |
| SSH 隧道 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Redis 浏览器 | **✅ 专用** | ⚠️ | ❌ | ❌ | ❌ |
| MongoDB 浏览器 | **✅ 专用** | ⚠️ | ✅ | ✅ | ❌ |
| 开源 | **✅** | ✅ 社区版 | ❌ | ❌ | ❌ |
| 价格 | **免费** | 免费/$199年 | $99/年 | $399/年 | 免费受限/$89年 |

### 逐个对比

**vs DBeaver**

DBX 赢在体积（15MB vs 400MB）、启动速度（1s vs 4-6s）、内存（80MB vs 500MB+）、AI 内建、Docker/Web、MCP。DBeaver 赢在成熟度——20 年历史、插件生态丰富、某些冷门数据库只有 JDBC 驱动时它更灵活。

**vs DataGrip**

DBX 赢在体积、价格（免费 vs $99/年）、AI、MCP、Docker。DataGrip 赢在 SQL 智能深度——schema 感知的自动补全、SQL 重构、执行计划分析。如果你一天写 8 小时 SQL，DataGrip 值那个钱。如果只是日常查数据、改表、看结构，DBX 够用。

**vs Navicat**

DBX 赢在价格（免费 vs $399-1299）、AI、MCP、Docker。Navicat 赢在企业功能——定时备份、数据同步向导、可视化查询构建器、20 年积累。Navicat 的定价决定了它不是开发者的日常工具。

**vs TablePlus**

DBX 赢在免费无限制（TablePlus 免费版限 2 个标签页 + 2 个连接）、数据库数量（50+ vs 10+）、AI、MCP、Docker。TablePlus 赢在 macOS 原生 UI 的精细度。

## AI SQL 助手：不是插件，是内建

这是 DBX 最核心的差异化功能。选中一张表，用自然语言描述需求：

```text
"查最近 30 天订单金额 TOP 10 的客户，包含他们的总订单数和平均客单价"
```

DBX 直接生成 SQL，并在执行前做安全检查：

```mermaid
flowchart LR
    Input["自然语言描述"] --> AI["AI 模型<br/>Claude / OpenAI / Ollama 本地"]
    AI --> SQL["生成 SQL"]
    SQL --> Safety["安全检查<br/>拦截 DROP/TRUNCATE 等危险操作"]
    Safety --> Execute["执行查询"]
    Execute --> Grid["结果表格"]
```

支持的模型：

- Claude（Anthropic）
- OpenAI
- DeepSeek
- Qwen
- Ollama 本地模型（完全离线）
- 任何 OpenAI 兼容的 API

## MCP 协议：让 AI Agent 查你的数据库

DBX 提供了 MCP Server，AI 编程 Agent 可以直接用你的数据库连接：

```bash
npx @dbx-app/mcp-server
```

`.mcp.json` 配置：

```json
{
  "mcpServers": {
    "dbx": { "command": "npx", "args": ["-y", "@dbx-app/mcp-server"] }
  }
}
```

配置后，Claude Code、Cursor、Windsurf 等 MCP 兼容的 Agent 就能：

- 列出你的数据库连接
- 浏览表结构
- 执行 SQL 查询
- 直接在 DBX UI 中打开查询结果

想象一下：Claude Code 在帮你调试一个 API bug 时，它可以直接查数据库里的数据来验证自己的假设——不需要你手动查了再告诉它。

## 命令行工具

DBX 也提供了 CLI：

```bash
# 安装
npm install -g @dbx-app/cli
# 或
brew tap t8y2/dbx && brew install dbx-cli

# 使用
dbx connections list --json
dbx query local "SELECT count(*) FROM orders" --json
```

## Docker 自托管：团队共享连接

```bash
docker run -d --name dbx -p 4224:4224 -v dbx-data:/app/data t8y2/dbx
```

浏览器打开 `http://localhost:4224`，Web 版功能完整。团队可以共享一套数据库连接配置，不用每个人各自维护一份。

## 适用场景

**适合用 DBX**：

- 日常开发中需要跨多种数据库查数据、改表
- 想要 AI 帮忙写 SQL，而不是手写复杂查询
- 想让 AI Agent 能直接查数据库
- 团队需要一个轻量的共享数据库 Web 控制台
- 讨厌 Java 运行时、讨厌 Electron 体积

**不适合用 DBX**：

- 一天写 8 小时复杂 SQL——DataGrip 的 SQL 智能更好
- 需要定时备份、数据同步向导——Navicat 这类企业工具
- 连接极端冷门的 JDBC 数据库——DBeaver 的插件生态更全

## 小结

DBX 三个核心优势：

1. **轻**——15MB，无运行时依赖。对比 DBeaver 的 400MB+ Java 运行时，这是 Rust 原生编译的结构性优势
2. **AI 原生**——AI SQL 助手不是后加的插件，是设计之初就有的功能。MCP 支持让 AI Agent 能直接查库
3. **全场景**——桌面端、Docker Web、CLI 三种形态。一个人用桌面端，团队用 Docker Web

大部分开发者日常用到的数据库操作——连接、查询、改表、导数据、看结构——DBX 已经覆盖了。不需要为了这些功能忍受 400MB 的安装包。

---

**相关阅读：**
- [Git Worktree：同一个仓库，多个工作区同时干活](git-worktree-guide.md)
- [开发工具索引](index.md)
