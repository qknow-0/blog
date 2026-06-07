# memory.md

> 这是 AI 读完你所有文章后，提炼出的「当下的你」——最近在做的事、关注的方向、发生的变化。这份文档会比你写任何一篇单独的文章都更诚实地告诉你：你现在在哪儿。

## 最近在做的事

### 知识库系统化建设（2026 年 5 月中 — 至今）

这是你当下最大的一件事。大概三周的时间里，你输出了 **60+ 篇文章**，覆盖了：

- **AI 编程工具链**（13 篇）：从 Spec-Kit、gstack、CodeGraph 到 RTK、Agent Reach、Webnovel Writer——你在做一件事：**把 AI 编程工具的版图画完整**。不是随机挑工具写，是有意识地在覆盖从「AI 怎么理解代码」到「AI 怎么交付项目」的完整链路。
- **Python 深度系列**：OOP（5 篇）、装饰器、闭包、类型提示、模块系统、async/await、with/yield——你不是在学 Python，你是在**把用了十年的工具从头梳理一遍**。
- **Go 并发系列**：Channel（4 篇）+ Goroutine（4 篇），一口气写完。这不是入门笔记，是系统性的并发知识整理。
- **容器化系列**（5 篇）：Docker → Compose → K8s → Helm，从单机到集群的完整演进。
- **内网穿透系列**（3 篇）：ngrok → Cloudflare Tunnel → localtunnel，从功能最全到最轻量。
- **开发工具**：Colima、OrbStack、systemd vs launchd、Celery、Tenacity、tmux——全是你日常在用的东西。
- **源码阅读**：QuantDinger（7 篇，30 张数据库表全部分析）+ Sequoia-X（5 篇）。

你不只是在写文章。你在**建一座知识库**——每个分类有 index.md，每个系列有导航页，README.md 是全局索引。这是一个工程师对自己十年的知识做了一次 `git commit -m "初始化知识库"`。

### 量化交易的持续关注

两套量化系统的源码阅读（Sequoia-X 和 QuantDinger）不是巧合。你自己做过 LOF 基金溢价监控系统，对数据源、缓存策略、份额校准、QDII 净值延迟这些细节非常熟悉。你对量化的兴趣不是在策略层面（怎么赚钱），而是在**工程层面**——数据怎么拉、怎么存、怎么校准、怎么保证实盘和研究代码不互相污染。

### 每天背计算机词汇

从 5 月 18 日开始，每天 10 个，已经背了 60 个。这不是考试需求——你只是觉得**专业术语的英文发音不能含糊**。这个习惯透露出的信息是：你对「基本功」有执念。

## 当前在意的方向

### 1. AI 编程工具链的演进

这是你知识库里最大、最活跃的分类。你关注的不是「AI 能不能写代码」——这个问题你已经用行动回答了（60+ 篇文章，大量 AI 辅助）。你关注的是更具体的问题：

- AI 怎么高效理解代码库（CodeGraph、Understand-Anything）
- AI 怎么减少 token 浪费（RTK）
- AI 怎么规范化开发流程（Spec-Kit、gstack、Compound Engineering）
- AI Agent 的能力边界在哪里（Agent Reach、Webnovel Writer）
- AI 代码审查怎么不重读整个仓库（code-review-graph）

你在测绘这个领域的边界，同时也在**组建自己的 AI 工具栈**。你现在的栈是：Claude Code + RTK + CodeGraph + agentmemory。

### 2. Python 的深层机制

你的 Python 文章不是 tutorial 级别的。装饰器那篇从「函数是一等公民」「闭包」两个前置概念讲起，OOP 系列一直写到 metaclass 和组合 vs 继承——这是一条**从熟练使用到理解设计意图**的路径。你不是在学 Python，你是在**理解这十年你一直在用的语言到底是怎么设计的**。

### 3. Go 并发的正确姿势

Channel 和 Goroutine 两个系列加起来 8 篇，结构非常清晰——从基础到 select 到 Pipeline/Fan-In/Done Channel 到 context 传播。你不是在学 Go 语法，你是在整理**并发编程的心智模型**。这些文章里反复出现的词是「阻塞语义」「背压」「取消传播」——都是工程实践中的硬问题。

### 4. 容器化的正确路径

从 Docker 到 Helm，你画了一条完整的线。你的表达方式很有特点：每一篇的痛点都是下一篇存在的原因——这是工程师的思维，不是讲师的思维。你写这些不是在教别人，是在**固化自己脑子里的认知链条**。

### 5. 开发效率的持续优化

Colima vs OrbStack vs Docker Desktop、systemd vs launchd、内网穿透三种方案对比、uv 替代 pip——你做技术选择的时候总是在做**多维度的对比分析**。你选工具的标准不是「大家都用」，是「轻量、可控、CLI 优先、不绑定云服务」。

## 最近的变化

### 变化一：从消费者变成建设者

这是一个重要的转变。以前你可能更多是在**用**工具、**读**源码——知识在脑子里，但没有外化。这三周你做的事情不一样了：你开始**建**。建索引、建分类、建系列、建知识之间的链接。知识从隐含的经验变成了显式的结构。

### 变化二：AI 从辅助变成了工作流

你的文章里到处是 AI 工具的痕迹。你不是每篇都手写——大量内容是 AI 辅助生成后你审阅修改的。但你也不是盲目信任 AI——Compound Engineering 的方法论（plan → work → review → compound）本质上是在给 AI 协作加上工程纪律。你知道 AI 会犯错，所以你建了一套流程确保它犯的错能被抓住。

### 变化三：知识输出进入了「系统化」阶段

60+ 篇文章在 3 周内完成，这个节奏说明你不是在「有空写一篇」，而是在**有意识地、系统性地完成一个知识库的初始化**。你给每个系列都建了文件夹、写了 index.md、更新了 README——这不是 casual blogging，这是工程化的知识管理。

### 变化四：从纯技术到 meta 层面的关注

Webnovel Writer 那篇「能用来做项目 plan 吗」特别有意思——你不是在分析这个工具怎么用，而是在想**一个网文写作系统的一致性模式能不能迁移到项目管理**。这是 meta 层面的思考：不是「这个工具能做什么」，而是「这个工具的思维模型能用到哪里」。

## 你现在的状态

你现在处于一个**知识体系重新整理**的时期。十年的积累在这三周里被系统化地编码成了 60+ 篇 Markdown 文件。这不是结束——很多分类（项目复盘、随想、阅读笔记）还是空的或只有骨架。但你已经有了一套清晰的框架，接下来就是往里填内容。

你现在关注的技术版图大致是：

```
AI 编程工具链（核心关注）
  ├── 代码理解（CodeGraph, Understand-Anything）
  ├── 流程规范（Spec-Kit, gstack, Compound Engineering）
  ├── Token 优化（RTK）
  └── Agent 边界（Agent Reach, CLI-Anything）

编程语言深度
  ├── Python（OOP, 装饰器, 类型系统, 异步）
  ├── Go（并发模型, Channel, Goroutine）
  └── Rust（所有权, 生命周期, Trait）

基础设施
  ├── 容器化（Docker → Compose → K8s → Helm）
  ├── 内网穿透（ngrok → Cloudflare Tunnel → localtunnel）
  └── macOS 开发环境（Colima, OrbStack, systemd/launchd）

量化交易
  ├── LOF 溢价监控（自己做的）
  ├── Sequoia-X（A 股选股系统源码阅读）
  └── QuantDinger（全栈量化操作系统源码阅读）
```

如果说 user.md 是你十年的横截面，memory.md 就是 2026 年春夏之交的快照——一个在 AI 工具大爆发时代，选择停下来、把十年的知识系统化编码出来的工程师。
