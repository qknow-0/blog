# agentmemory：为 AI 代理赋予持久记忆的轻量级 MCP 工具

## 前言

你有没有遇到过这样的场景：用 Claude Code 完成了一个复杂的功能，关掉会话后第二天再开，AI 对昨天讨论的上下文一无所知？或者你在调试一个棘手的问题，好不容易梳理出关键线索，AI 却在下一个回合忘记了之前的结论？

这正是当前 AI 编程助手面临的核心痛点——**无状态**。每个会话都是一张白纸，没有长期记忆。

[agentmemory](https://github.com/rohitg00/agentmemory) 就是为解决这个问题而生的：一个轻量级的 Python 库，为 AI 代理提供**持久化记忆能力**，让你和 AI 之间的协作不再"每次从头开始"。

---

## 项目概述

agentmemory 的核心定位是 AI 代理的**记忆层**。它提供一套简洁的 API，让 AI 能够：

- **记住**重要的上下文、决策和发现
- **回忆**跨会话的信息，通过语义搜索精准定位
- **忘记**不需要的内容，且操作可审计

### 核心特性

| 特性 | 说明 |
|------|------|
| **持久化存储** | 记忆写入本地存储，跨会话持久保留 |
| **语义搜索** | 基于自然语言相似度检索，非关键词精确匹配 |
| **混合搜索** | 语义 + 关键词双重检索，兼顾精准与模糊 |
| **记忆分类** | 支持多种记忆类型：模式、偏好、架构、Bug、工作流、事实 |
| **会话管理** | 按会话维度组织记忆，随时查看会话状态与观察数 |
| **审计追溯** | 所有操作有记录，删除必须附带原因 |
| **完整导出** | 一键导出全部记忆为 JSON 格式 |
| **MCP 原生集成** | 作为 MCP Server 运行，Claude Code 开箱即用 |

### 技术底座

- **语言**：Python 3.x
- **存储**：本地持久化（SQLite + 向量嵌入）
- **嵌入模型**：本地运行，无需外部 API
- **接口**：Python API + MCP Server + CLI

---

## 核心功能详解

### 1. 记忆存储（Memory Save）

将任意文本内容保存为记忆，支持附加上下文标签：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | 是 | 要记住的内容 |
| `type` | string | 否 | 记忆类型：`pattern`、`preference`、`architecture`、`bug`、`workflow`、`fact` |
| `concepts` | string | 否 | 关联的概念标签，逗号分隔 |
| `files` | string | 否 | 关联的文件路径，逗号分隔 |

### 2. 记忆回忆（Memory Recall）

通过语义搜索找回记忆，支持多种输出格式：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `query` | string | - | 搜索关键词，自然语言 |
| `limit` | number | 10 | 最大返回条数 |
| `format` | string | `full` | 输出格式：`full`（完整）、`compact`（紧凑）、`narrative`（叙事） |
| `token_budget` | number | - | Token 预算上限，超出则裁剪 |

### 3. 混合搜索（Smart Search）

结合语义相似度与关键词匹配的混合检索，支持渐进式信息展开——先看摘要，再展开感兴趣的具体条目。

### 4. 会话管理（Sessions）

所有记忆按会话组织。你可以查看所有历史会话、每个会话的状态和观察数，方便追踪每次交互的上下文变迁。

### 5. 审计与治理（Audit & Governance）

- **审计**：所有记忆操作都有记录，可按操作类型筛选
- **治理删除**：删除记忆时必须提供原因，确保操作可追溯

### 6. 数据导出（Export）

一键将全部记忆导出为 JSON 格式，方便备份、迁移或分析。

---

## 安装方式

### 通过 pip 安装

```bash
pip install agentmemory
```

推荐使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install agentmemory
```

### 通过 pipx 安装（推荐用于全局使用）

```bash
pipx install agentmemory
```

### 配置 MCP Server

为了与 Claude Code 集成，需要在 `~/.claude.json` 中添加 MCP 配置：

```json
{
  "mcpServers": {
    "agentmemory": {
      "command": "uvx",
      "args": ["agentmemory"]
    }
  }
}
```

配置完成后，重启 Claude Code，agentmemory 的 MCP 工具即可自动加载。

### 验证安装

在终端中测试：

```bash
python -c "import agentmemory; print(agentmemory.__version__)"
```

如果配置了 MCP，在 Claude Code 中输入 `/tools` 即可看到 agentmemory 提供的工具列表。

---

## 快速上手

### 在 Claude Code 中使用（MCP 方式）

安装并配置好 MCP 后，你可以直接在对话中让 Claude 使用记忆功能：

**保存一段记忆：**

> "帮我记住：这个项目的认证方案使用 JWT + Refresh Token，access_token 有效期 15 分钟，保存在 mem 类型为 architecture，关联文件 auth.py"

Claude 会自动调用 `memory_save` 工具，将信息持久化。

**在需要时回忆：**

> "这个项目的认证方案是怎么设计的？"

Claude 会调用 `memory_recall` 查找相关记忆，即使这是全新的会话。

### 通过 Python API 编程使用

```python
from agentmemory import save, recall, search, get_sessions, export

# 保存记忆
save(
    content="这个微服务的核心逻辑是：收到订单事件后，先校验库存，再扣减，最后通知发货服务。",
    type="architecture",
    concepts="订单,微服务,库存",
    files="order-service/main.py"
)

# 回忆记忆
results = recall("订单处理流程是什么")
for r in results:
    print(f"[{r['type']}] {r['content']}")

# 混合搜索
results = search("库存扣减")
for r in results:
    print(r['content'])

# 查看所有会话
sessions = get_sessions()
for s in sessions:
    print(f"会话 {s['id']}: {s['observation_count']} 条观察记录")

# 导出全部记忆
export("memories-backup.json")
```

### 导出与审计

```python
from agentmemory import export, audit

# 导出为 JSON
export_data = export()
print(f"共 {len(export_data)} 条记忆")

# 查看审计记录
audit_logs = audit(operation="delete")
for log in audit_logs:
    print(f"{log['timestamp']} - 删除原因: {log['reason']}")
```

---

## 实战场景

### 场景一：跨会话的架构决策记忆

你在开发一个微服务项目，Claude Code 帮你设计了事件驱动架构。如果不保存记忆，下次会话你需要重新解释所有背景。

**在会话中保存：**

```
memory_save(
  type="architecture",
  content="采用 RabbitMQ 作为消息总线，订单服务发布事件，库存服务和通知服务订阅消费。",
  concepts="RabbitMQ,事件驱动,微服务",
  files="docker-compose.yml"
)
```

**新会话中回忆：**

```
memory_recall(query="消息队列和事件驱动")
```

→ 自动获得完整架构上下文，直接继续上次的工作。

### 场景二：团队编码规范记忆

团队成员有一套约定好的编码规范，每次代码审查都要反复提醒。用 agentmemory 记住后，Claude 会自动遵守。

```
memory_save(
  type="pattern",
  content="错误处理统一使用 Result 类型，不抛裸异常。Controller 层捕获后返回统一 JSON 格式。",
  concepts="错误处理,Result,规范"
)
```

### 场景三：Bug 调试记录

修复一个棘手的并发 Bug 后，把根因和解决思路保存下来。

```
memory_save(
  type="bug",
  content="并发下单时库存超卖：原因是 Redis 缓存与数据库之间存在竞态条件。解决方案：引入分布式锁 + 乐观锁双重保障。",
  concepts="并发,Bug,分布式锁,乐观锁",
  files="inventory/service.py"
)
```

之后再遇到类似症状，Claude 会主动关联这条记忆。

### 场景四：工作流模板

记住一个常见的部署工作流，以后每次只需要一句话就能触发。

```
memory_save(
  type="workflow",
  content="生产部署流程：1. 切 10% 流量到新版本 2. 观察 5 分钟错误率 3. 逐步放量 25% -> 50% -> 100% 4. 确认后旧版本保留 1 小时后下线",
  concepts="部署,生产环境,灰度发布"
)
```

---

## 为什么选择 agentmemory？

在 AI 编程工具日益普及的今天，**记忆能力**正在成为区分工具好不好用的关键维度。

| 对比维度 | 无记忆方案 | agentmemory |
|----------|-----------|-------------|
| 跨会话上下文 | 每次重头开始 | 自动恢复之前的知识 |
| 信息组织 | 靠人脑记忆 | 结构化分类存储 |
| 检索方式 | 关键词精确匹配 | 语义模糊搜索 |
| 可审计性 | 无 | 完整操作审计 |
| 与 Claude 集成 | 需要手动输入 | MCP 原生集成 |

agentmemory 最大的优势是**轻量**——没有外部依赖（不需要 PostgreSQL、不需要 Redis、不需要任何云服务），一个 `pip install` 加上几行 JSON 配置就能跑起来。它把"为 AI 做记忆"这件事的门槛降到了最低。

---

## 总结

agentmemory 解决了 AI 编程工具使用中一个非常实际的痛点：**记忆的持久化**。它不追求大而全，而是聚焦在"记住 -> 回忆 -> 管理"这条核心链路上，用最简洁的方式完成了最重要的功能。

如果你在使用 Claude Code 或其他 MCP 兼容的 AI 工具，并且遇到了"每次都要重复背景信息"的烦恼，agentmemory 值得一试。

---

**原文仓库**：[github.com/rohitg00/agentmemory](https://github.com/rohitg00/agentmemory)

**许可证**：MIT
