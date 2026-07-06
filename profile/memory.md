# memory.md

> 这是 AI 读完你所有文章后，提炼出的「当下的你」——最近在做的事、关注的方向、发生的变化。这份文档会比你写任何一篇单独的文章都更诚实地告诉你：你现在在哪儿。

## 最近在做的事

### 知识库持续建设（2026 年 6 月中 — 7 月初，新增 40+ 篇）

6 月中旬至今又新增了 40+ 篇文章和 2 个新模块，覆盖了几个值得注意的方向：

- **nanobot 源码阅读**（6 篇）：第一个 Python AI Agent 框架的完整源码分析。从 MessageBus 双队列解耦、AgentLoop 8 状态机、Provider 多模型抽象、Tool 自动发现、Session/Memory 的 Dream 记忆巩固、Channel 15+ 平台统一接入，到 WebUI 的 WebSocket 多路复用。这是你第一次分析一个完整的 AI Agent 基础设施——不只是"用了什么"，而是**每一层怎么解耦、怎么降级、怎么扩展**。
- **Rust 设计模式系列**（6 篇，已写 6/23）：用 Rust 的类型系统重新审视 GoF 23 个模式。已完成的 6 篇（Singleton、Factory Method、Abstract Factory、Builder、Prototype、Adapter）不是对经典的翻译，而是**从 Rust 的 trait、enum、所有权、生命周期的角度重新解释每个模式**——哪些被语言特性替代了（Singleton → OnceLock），哪些有了更好的实现（Builder → type state + build(self) 消费）。
- **AI 工具全景扫描**（8 篇）：Trellis（Agent 工程框架）、Cua（电脑操作 Agent）、Open Code Review（阿里 AI 代码审查）、Headroom（上下文压缩层）、Superset（Agent 并行调度）、Planning with Files（Agent 外存）、DBX（AI 数据库管理）、Orca（多 Agent IDE）。不是深度用，是**快速测绘 AI 工具链的版图**——知道什么东西存在、解决什么问题、怎么组合。
- **API 设计三篇**（RESTful / GraphQL / gRPC）：对比式写法，不是分别介绍，而是**同一个场景下三种方案的优劣选择**。
- **watchexec + bacon**：两个 Rust 开发工具——文件监听自动跑命令、后台代码检查。实用的开发者效率工具。
- **语言类文章**：Python descriptors、Python exec/eval、Rust LazyLock、Go Context、Unsafe Rust、Node.js 错误处理、Node.js V8 内存管理——持续在深度和广度上扩展。
- **Rust 全系列比喻重写**：一次大规模改写——所有权（搬家）、生命周期（停车票）、Trait（快递）、闭包（背包）、模块（图书馆）、Arc（公寓楼）、Box（集装箱）、错误处理（食品质检）、LazyLock（酒店）——全部用生活比喻重新解释。CLAUDE.md 也新增了"语言类文章用比喻"的正式约定。

### 新模块上线

- **运动打卡**：6 月 21 日新建，至今打卡 6 次（走路、俯卧撑、徒步、篮球 x2、更多徒步），累计 240+ 分钟。不是心血来潮——有每日打卡页面、月度统计、连续天数追踪、emoji 约定。
- **词汇学习继续**：day-007、day-008，已学 80 个计算机词汇。

### 工程规范的持续完善

- **语言版本约定**：所有文章统一使用各语言的最新稳定版本（CLAUDE.md 新增）
- **语言比喻约定**：语言类文章尽量使用生活比喻（CLAUDE.md 新增）
- **Obsidian 工作区同步**：`.obsidian/` 配置纳入版本管理
- 设计模式系列、源码阅读系列、新文章——所有索引和 README 同步更新

## 当前在意的方向

### 1. AI 工具的测绘与评估（新增）

这是 6 月下旬最重要的新方向。你不再只关注"怎么用"或"怎么构建"，你开始**系统性地扫描 AI 工具链的全景**——Agent 框架（Trellis）、电脑操作（Cua）、代码审查（Open Code Review）、上下文压缩（Headroom）、并行调度（Superset）、外存系统（Planning with Files）……你的态度是：**快速了解、精准判断、记录要点**。每篇文章控制在能说清楚"它解决什么问题 + 怎么用"的篇幅。

### 2. 设计模式的 Rust 化（新增）

这是一个独特的交叉领域——你在用 Rust 的类型系统重新审视 30 年前的 GoF 模式。不是翻译经典，是**把经典放在 Rust 的类型系统里重新蒸馏**。这个系列的价值不只在于讲设计模式，更在于它展示了 Rust 的 trait、enum、所有权、生命周期如何让很多"经典模式"变得不需要了，或者有了更优雅的实现。

### 3. 源码阅读的能力（持续深化）

从量化交易（Sequoia-X、QuantDinger、TrendRadar）到 AI Agent 框架（nanobot），从 Python 到 TypeScript——源码阅读的广度和深度都在增加。nanobot 系列尤其体现了你源码阅读方法的成熟：不是逐文件翻译，而是**先抓架构主干（MessageBus + 状态机），再逐层拆解**。

### 4. AI Agent 的构建能力（保持）

nanobot 源码阅读是"理解别人怎么构建"，AI 工具全景扫描是"知道已有轮子是什么"。你在从 consumer → builder → **evaluator** 进化。

### 5. 前端能力补齐（保持）

React 系列之后没有新增前端文章，但 newsnow 源码阅读（TypeScript）算是前端能力的延伸。

### 6. Python / Go / Rust 的深层机制（保持）

持续在语言深度上扩展——Python descriptors 和 exec/eval、Go Context、Rust LazyLock 和 Unsafe——这些都是"大多数人知道存在但不知道底层"的主题。

## 最近的变化

### 变化一：从"构建"到"测绘"

之前你对 AI 的关注集中在"怎么用 AI 编程工具"和"怎么构建 Agent"。6 月下旬新增了第三个层次——**测绘 AI 工具的全景**。Trellis、Cua、Headroom、Superset 这些不是你深度使用的工具，而是你快速评估、判断定位、记录要点的产物。这有点像你在做**技术雷达**。

### 变化二：写作有了一个新的维度——比喻

Rust 全系列比喻重写不是一次简单的润色——它是一种新的写作方法论。把抽象概念（所有权、生命周期、trait）映射到具象场景（搬家、停车票、快递），降低理解门槛的同时保持技术准确性。这已经成为 CLAUDE.md 里的正式约定。你对"怎么写"和"写什么"一样在意。

### 变化三：身体被纳入了工程系统

运动打卡不是"今天跑了步"的碎碎念——它有月度页面、每日格子、连续天数追踪、emoji 约定、月度统计。你在用**管理工程项目的方式管理身体健康**。连续打卡 2 天，最长连续 2 天——刚开始，但已经上路了。

### 变化四：源码阅读从"项目级"到"框架级"

QuantDinger、TrendRadar 是应用项目（量化交易、舆情监控），nanobot 是**基础设施框架**（AI Agent 运行时）。前者关心"这个系统怎么运作"，后者关心"这个框架怎么设计的、为什么每一层这样解耦"。

### 变化五：设计模式系列打开了一个新的写作方向

GoF 23 个模式 + Rust 实现——这是一个可以写很久的系列。而且每个模式都可以对比 Python/Java/Go 的实现差异，让"设计模式"这个经典主题在 Rust 的类型系统里获得新的生命力。

## 你现在的状态

你现在处于一个**多元扩展 + 写作方法论成熟**的时期。5 月是初始化（编码已有知识），6 月是扩展（进入新领域），7 月初开始出现一个新的特征——**你不仅在写新东西，还在优化"怎么写"这件事本身**（比喻重写、版本约定、工具测绘的节奏）。

你现在关注的技术版图：

```
AI（三层关注）
  ├── AI 编程工具链（CodeGraph, RTK, Spec-Kit, gstack）      ← 使用
  ├── AI Agent 构建（LLM API, Function Calling, Memory）      ← 构建
  └── AI 工具测绘（Trellis, Cua, Headroom, Superset...）      ← 评估

编程语言深度（比喻写作风格）
  ├── Python（OOP, descriptors, exec/eval...）               ← 持续扩展
  ├── Go（Context, 并发模型, Channel, Goroutine）             ← 持续扩展
  ├── Rust（LazyLock, Unsafe, 设计模式系列, 比喻重写）        ← 活跃
  └── React（心智模型, Hooks, 渲染, RSC）                    ← 暂停，可能回头

架构与设计
  ├── 设计模式：Rust 视角（6/23）                            ← 活跃，长期系列
  └── API 设计（RESTful / GraphQL / gRPC）                   ← 已完成

源码阅读（框架级突破）
  ├── Python: nanobot（AI Agent 框架）                       ← 全新
  ├── Python: QuantDinger, Sequoia-X, TrendRadar              ← 已完成
  └── TypeScript: newsnow                                     ← 已完成

开发工具效率
  ├── Rust 生态：bacon, watchexec                             ← 新增
  └── 终端/Shell：Orca, Ghostty, tmux                         ← 扩展

工程规范（持续完善）
  ├── 语言版本约定 + 比喻写作约定                             ← 新增
  ├── 脱敏处理 + source-read 流程                             ← 稳定
  └── 运动打卡 + 词汇学习                                     ← 活跃

基础设施（稳定）
  ├── 容器化（Docker → Compose → K8s → Helm）
  ├── 内网穿透
  └── macOS 工具链
```

如果说 5 月的你是"把已有的东西写下来"，6 月的你是"系统性地向新领域推进"，那 7 月初的你是——**在快速扩张的同时，开始注重写作的工艺本身**。你不只是在积累内容，你是在打磨一套关于"怎么写好技术文章"的方法论。
