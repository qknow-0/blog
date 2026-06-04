# 我的知识库

写了十年代码，再不输出点东西脑子要溢出了。这里没有正确的废话，只有踩过的坑、读过的源码、用过的工具——每一个结论背后都有一段不想回忆的 debug 经历。

## 目录

- [技术笔记](tech/index.md) — 框架、工具
  - [AI 编程工具链](tech/ai-tooling/index.md) — 11 篇
  - [Claude Code](tech/claude-code/index.md) — 3 篇
  - [开发工具](tech/dev-tools/index.md) — 5 篇
  - [容器化系列](tech/containerization/index.md) — 5 篇，Docker → Compose → K8s → Helm
- [编程语言](languages/index.md) — 语法、特性
  - [Python](languages/python/index.md)
    - [Python 闭包：函数为什么能“记住”外部变量](languages/python/closures.md) — 2026-05-31
    - [Python 装饰器：从函数到可调用对象的完整理解](languages/python/decorators.md) — 2026-05-30
    - [Python 模块系统：每一个 import 背后发生了什么](languages/python/modules.md) — 2026-05-30
    - [Python 异步编程：从回调地狱到 async/await](languages/python/async-await.md) — 2026-05-30
    - [with 语句：上下文管理器的正确打开方式](languages/python/with-statement.md) — 2026-05-17
    - [yield 与生成器：惰性求值的艺术](languages/python/yield-statement.md) — 2026-05-17
  - [Go](languages/golang/index.md)
    - [Go 单元测试：标准库就够了](languages/golang/unit-testing.md) — 2026-05-30
  - [Java](languages/java/index.md)
    - [Java 单元测试：JUnit 5 不是唯一解](languages/java/unit-testing.md) — 2026-05-30
  - [Node.js](languages/nodejs/index.md)
    - [Node.js 事件循环：理解了它才算真会用](languages/nodejs/event-loop.md) — 2026-05-30
    - [Node.js 最新版本实用特性盘点](languages/nodejs/practical-features.md) — 2026-05-27
  - [Rust](languages/rust/index.md)
    - [Rust 生命周期：'a 不是魔法，是编译器在检查指针有效期](languages/rust/lifetimes.md) — 2026-06-04
    - [Rust 模块系统：一个文件不是天然模块](languages/rust/modules.md) — 2026-05-30
    - [Rust Trait 与泛型：多态不只是继承](languages/rust/traits-generics.md) — 2026-05-30
    - [Rust 单元测试：编译器帮你测](languages/rust/unit-testing.md) — 2026-05-27
    - [Rust 错误处理：Result、Option 和 ? 运算符](languages/rust/error-handling.md) — 2026-05-27
    - [Rust 所有权：三张图看懂最核心的概念](languages/rust/ownership.md) — 2026-05-24
- [项目复盘](project-retro/index.md) — 项目回顾与总结
- [架构设计](architecture/index.md) — 系统设计、技术方案
  - [基金溢价数据设计](architecture/fund-premium-data.md) — 2026-05-24
- [阅读笔记](reading/index.md) — 书、文章、视频的读后记录
- [源码阅读](source-read/index.md) — 开源项目的源码分析
  - [QuantDinger](source-read/quant_dinger/01-intro.md) — AI 量化交易操作系统（7 篇）
    - [（一）项目概览](source-read/quant_dinger/01-intro.md) · [（二）数据库设计](source-read/quant_dinger/02-database.md) · [（三）数据层](source-read/quant_dinger/03-data-layer.md)
    - [（四）策略引擎](source-read/quant_dinger/04-strategy-engine.md) · [（五）执行层](source-read/quant_dinger/05-execution.md) · [（六）AI 集成](source-read/quant_dinger/06-ai-agent.md)
    - [（七）基础设施](source-read/quant_dinger/07-infra.md)
  - [Sequoia-X（一）项目介绍与使用方式](source-read/sequoia_x/01-intro.md) — 2026-05-17
  - [Sequoia-X（二）数据引擎](source-read/sequoia_x/02-data-engine.md) — 2026-05-17
  - [Sequoia-X（三）策略体系](source-read/sequoia_x/03-strategies.md) — 2026-05-18
  - [Sequoia-X（四）飞书推送与基础设施](source-read/sequoia_x/04-notify-infra.md) — 2026-05-18
  - [Sequoia-X（五）测试体系](source-read/sequoia_x/05-testing.md) — 2026-05-18
- [随想](thoughts/index.md) — 非技术类的日常思考

## 开发环境

`./scripts/setup.sh` 个人当前使用环境，一键安装。
