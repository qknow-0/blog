# Spec-Kit：让规范驱动开发的核心理念与实战指南

## 概述

[Spec-Kit](https://github.com/github/spec-kit) 是 GitHub 开源的一套**规范驱动开发（Spec-Driven Development, SDD）**工具包。它的核心理念很简单：**让规范生成代码，而不是让规范指导代码**。

传统开发流程里，PRD 写完就被丢在一边，代码才是唯一真相。Spec-Kit 把这个关系翻转了——规范（Spec）成为可执行的制品，通过 AI 编程助手直接转化为可工作的实现。

### 核心价值

- **意图驱动**：用自然语言描述"要做什么"和"为什么"，而不是纠结技术细节
- **自动化工作流**：从规范到计划到任务分解到实现，全流程通过斜杠命令驱动
- **质量内建**：模板强制检查清单、需求澄清、测试优先等工程纪律
- **技术无关**：同一份规范可以生成不同技术栈的实现

---

## 安装与初始化

### 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Git
- 支持的 AI 编程助手（Claude Code、GitHub Copilot、Gemini CLI、Cursor 等 30+）

### 安装 CLI

```bash
# 安装 specify 命令行工具（替换 vX.Y.Z 为最新版本号）
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z
```

### 初始化项目

```bash
# 创建新项目并指定 AI 助手集成（如使用 Claude Code）
specify init my-project --integration claude
cd my-project
```

初始化后，AI 编程助手会自动获得一系列 `/speckit.*` 斜杠命令。

---

## 工作流全景

Spec-Kit 定义了一条清晰的 **6 步流水线**：

```
/speckit.constitution  →  制定项目宪章（开发原则）
         ↓
/speckit.specify       →  编写功能规范（是什么、为什么）
         ↓
/speckit.clarify       →  澄清模糊需求（可选但推荐）
         ↓
/speckit.plan          →  制定技术实现计划（技术栈、架构）
         ↓
/speckit.tasks         →  分解为可执行任务列表
         ↓
/speckit.implement     →  执行实现
```

### 斜杠命令一览

| 命令 | 用途 |
|------|------|
| `/speckit.constitution` | 创建项目宪章（代码质量、测试标准等原则） |
| `/speckit.specify` | 将需求描述转化为结构化规范（用户故事 + 验收标准） |
| `/speckit.clarify` | 逐项澄清规范中的模糊点 |
| `/speckit.plan` | 生成技术实现计划（技术栈、数据模型、API 合约） |
| `/speckit.tasks` | 将计划拆分为可执行任务，标注依赖和并行标记 |
| `/speckit.implement` | 按任务顺序执行实现 |
| `/speckit.checklist` | 生成验收检查清单 |
| `/speckit.analyze` | 跨制品一致性分析 |
| `/speckit.taskstoissues` | 将任务列表转为 GitHub Issues |

### 目录结构

初始化后，项目会生成以下结构：

```
.specify/
├── memory/
│   └── constitution.md          # 项目宪章
├── scripts/
│   └── bash/                    # 自动化脚本
├── specs/
│   └── 001-功能名/
│       ├── spec.md              # 功能规范
│       ├── plan.md              # 实现计划
│       ├── tasks.md             # 任务列表
│       ├── data-model.md        # 数据模型
│       ├── contracts/           # API/事件合约
│       ├── quickstart.md        # 快速验证指南
│       └── research.md          # 技术调研
└── templates/
    ├── spec-template.md
    ├── plan-template.md
    └── tasks-template.md
```

---

## 扩展与预设

Spec-Kit 支持通过**扩展（Extensions）**和**预设（Presets）**深度定制：

| 目的 | 使用 |
|------|------|
| 添加全新命令或工作流 | Extension |
| 自定义规范/计划/任务格式 | Preset |
| 集成外部工具或服务 | Extension |
| 强制执行组织或合规标准 | Preset |

```bash
# 搜索并安装扩展
specify extension search
specify extension add <extension-name>

# 搜索并安装预设
specify preset search
specify preset add <preset-name>
```

---

## 实战场景：用 Spec-Kit 构建一个团队协作看板

下面通过一个完整的使用案例，展示 Spec-Kit 如何将一个模糊想法变成可运行的代码。

### 背景

假设我们要做一个叫 **Taskify** 的团队看板工具，需求如下：

- 用户可以创建项目、添加团队成员、分配任务
- 看板视图支持拖拽，列包括"待办"、"进行中"、"评审中"、"已完成"
- 任务卡片可以评论、修改状态、分配负责人
- 自己的任务用不同颜色标识
- 只能编辑/删除自己写的评论

### Step 1：建立项目宪章

```text
/speckit.constitution 创建以下原则：
- 代码质量优先：所有代码必须通过 lint 和类型检查
- 80% 测试覆盖率：强制执行 TDD
- 用户体验一致性：使用统一的组件库和设计语言
- 性能要求：页面加载时间 < 2 秒
- 简洁性原则：不引入不必要的抽象层
```

这一步产生了 `.specify/memory/constitution.md`，后续所有步骤都会参照这些原则。

### Step 2：编写功能规范

```text
/speckit.specify 开发 Taskify 团队看板平台。支持：
- 创建项目、添加团队成员、分配任务
- 看板视图（待办、进行中、评审中、已完成）
- 拖拽移动任务卡片
- 无限评论、任务分配、状态变更
- 5 个预定义用户（1 PM + 4 工程师）
- 当前登录用户的任务用不同颜色标识
- 只能编辑/删除自己的评论
没有登录功能，这是第一版原型验证。
```

Spec-Kit 自动创建了 `001-create-taskify` 分支和 `spec.md`，内含完整的用户故事和验收标准。

### Step 3：澄清模糊需求

```text
/speckit.clarify
```

Agent 逐项提问，例如：
- "任务卡片是否需要有创建时间显示？"
- "当一个任务被拖入'已完成'列时，是否应该自动记录完成时间？"
- "如果一个任务没有分配负责人，卡片应该显示什么？"

每个答案都会被记录到规范的 Clarifications 章节。

### Step 4：制定技术计划

```text
/speckit.plan 使用 Next.js 14 App Router + TypeScript。
用 Prisma + SQLite 做数据层。
前端用 Tailwind CSS + shadcn/ui。
拖拽功能用 @dnd-kit。
```

Agent 生成了：
- `plan.md` — 架构总览和分阶段实施计划
- `data-model.md` — User、Project、Task、Comment 四个核心模型
- `contracts/api-spec.json` — REST API 合约
- `research.md` — `@dnd-kit` vs `react-beautiful-dnd` 调研结论

### Step 5：生成任务列表

```text
/speckit.tasks
```

Agent 自动将计划分解为任务，按用户故事分组：

```
Phase 1: 数据模型与数据库
  [P] Task 1.1: 创建 Prisma schema（含 User/Project/Task/Comment 模型）
  [P] Task 1.2: 编写 seed 脚本（5 个用户 + 3 个项目）
  Task 1.3: 运行初始迁移

Phase 2: 用户故事 — 选择用户进入主界面
  [P] Task 2.1: 实现用户选择页面组件
  Task 2.2: 实现用户状态管理（zustand store）

Phase 3: 用户故事 — 看板视图
  ...

Phase 4: 用户故事 — 拖拽与评论
  ...
```

`[P]` 标记表示可以并行执行，大大加速开发。

### Step 6：执行实现

```text
/speckit.implement
```

Agent 按照任务列表，严格 TDD：
1. 先写测试（Red）
2. 用户确认测试
3. 实现代码（Green）
4. 重构（Refactor）

最终产生了完整的可运行原型。

---

## 为什么这很重要

传统开发中，一个看板工具的完整规范文档需要 12+ 小时的设计和文档工作。使用 Spec-Kit：

| 步骤 | 传统耗时 | Spec-Kit 耗时 |
|------|---------|-------------|
| PRD 编写 | 2-3 小时 | 5 分钟 |
| 设计文档 | 2-3 小时 | 5 分钟 |
| 项目搭建 | 30 分钟 | 自动完成 |
| 技术规范 | 3-4 小时 | 5 分钟 |
| 测试计划 | 2 小时 | 5 分钟 |
| **总计** | **~12 小时** | **~15 分钟** |

差距不在于人更聪明，而在于**模板和约束让 AI 的工作质量从"可能还行"变成了"始终可靠"**。

---

## 总结

Spec-Kit 的核心思想是：**规范不是写完就可以丢掉的东西，它是整个开发流程的驱动力**。

它并非要取代开发者，而是把机械的翻译工作交给 AI——从需求到计划到代码——让开发者把精力集中在创意、实验和批判性思维上。

如果你已经在用 Claude Code、Copilot 或其他 AI 编程助手，Spec-Kit 提供了一个经过验证的结构化工作流，让你的 AI 助手从"代码生成器"升级为"架构伙伴"。

> 官方仓库：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
> 在线文档：[https://github.github.io/spec-kit/](https://github.github.io/spec-kit/)
