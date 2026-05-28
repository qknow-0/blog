# Compound Engineering：让每一次提交都为下一次铺路

软件开发有一个令人沮丧的事实：**每加一个功能，下一次改动就更难一点**。代码库越来越大，上下文越来越重，没人记得上次为什么那样设计。每修一个 bug 都留下一段只有当事人理解的隐式知识，后来者要重新踩一遍坑。

Compound Engineering 要翻转这个局面。核心理念一句话：**每次工程工作都应该让后续工作更简单，而不是更难**。

这是 Every Inc.（一家内容 + 软件公司）在实践中总结出来的方法论，已经做成了 Claude Code 插件——37 个 skills、51 个 agents，覆盖从策略到执行的完整循环。

## 80/20：规划比写代码重要

Compound Engineering 把开发拆成一个循环：

```
/ce-brainstorm → /ce-plan → /ce-work → /ce-code-review → /ce-compound
```

五个命令，每步的输出是下一步的输入：

- **`/ce-brainstorm`** — 交互式问答，把模糊需求变成结构化的需求文档。它会追问你为什么、谁是用户、不做会怎样
- **`/ce-plan`** — 读取需求文档，输出实现计划。分阶段、标依赖、估工作量
- **`/ce-work`** — 在独立 worktree 中执行计划，按任务列表逐项完成
- **`/ce-code-review`** — **多 Agent 并行审查**。不是一个 Agent 看一遍，而是多个 Agent 从不同角度同时审查
- **`/ce-compound`** — 把这次学到的模式、坑、经验写下来，让下次不再重学

一个典型的开发流程：

```text
/ce-brainstorm "让后台任务重试更安全"
/ce-plan docs/brainstorms/background-job-retry-safety-requirements.md
/ce-work
/ce-code-review
/ce-compound
```

五步走完，不只是交付了一个功能——还留下了一份需求文档、一份实现计划、一份审查记录、一份经验笔记。下一次类似的需求再来，Agent 可以直接读这些产物，不用从头理解上下文。

## 复利怎么产生

传统开发中，每个功能是一个孤立事件。做完就完了，留下的只是代码变更。

Compound Engineering 每个循环产出一堆**可复用的知识制品**：

```
需求文档  →  下次类似需求有模板
实现计划  →  新 Agent 知道怎么拆分任务
审查记录  →  常见的坑和模式被记录下来
经验笔记  →  下一个人（或 Agent）不会踩同样的坑
```

**`/ce-compound`** 是复利的关键。它不是写完代码就结束——而是把这次学到的东西写下来，下次同一个 Agent（或同一个开发者）能直接检索到。这不是日志，是知识库。

## 命令全景

### 循环上游

| 命令 | 作用 |
|------|------|
| `/ce-strategy` | 创建 `STRATEGY.md`——产品要解决的问题、方法、用户画像、指标。brainstorm 和 plan 会把它作为基础上下文 |
| `/ce-ideate` | 生成并评估多个创意，选出最优的进入 brainstorm |

### 核心循环

| 命令 | 作用 |
|------|------|
| `/ce-brainstorm` | 交互式需求梳理，产出需求文档 |
| `/ce-plan` | 需求转实现计划，分阶段、标依赖 |
| `/ce-work` | 在 worktree 中按计划执行 |
| `/ce-code-review` | 多 Agent 并行审查，从不同角度审计 |
| `/ce-compound` | 记录经验和模式，知识库增长 |

### 辅助命令

| 命令 | 作用 |
|------|------|
| `/ce-debug` | 系统化复现失败、追踪根因、实现修复 |
| `/ce-product-pulse` | 生成单页产品报告（24h/7d 窗口），追踪用户行为和产品表现 |

## 安装

Claude Code 中两步搞定：

```text
/plugin marketplace add EveryInc/compound-engineering-plugin
/plugin install compound-engineering
```

安装后首次运行 `/ce-setup`，它会检查环境、安装缺失工具、初始化项目配置。Cursor、Codex、Copilot 也支持。

## 和 Spec-Kit 的对比

Spec-Kit 解决的是「从规范到代码」的翻译问题。Compound Engineering 解决的是「开发工作的知识沉淀」问题。

| | Compound Engineering | Spec-Kit |
|------|------|------|
| 关注点 | 知识复利 | 规范驱动代码生成 |
| 核心问题 | 怎么让下次更容易 | 怎么让 AI 正确实现 |
| 产物 | 需求文档 + 计划 + 经验笔记 | spec.md + plan.md + tasks.md |
| 审查 | 多 Agent 并行审查 | checklist 自检 |
| 知识留存 | `/ce-compound` 经验沉淀 | 无 |

两个可以配合使用：Spec-Kit 做结构化规范生成，Compound Engineering 做全过程知识管理。

> 仓库：[https://github.com/EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin)
> 理念文章：[https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents](https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents)
