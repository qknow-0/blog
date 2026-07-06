# 我的知识库

写了十年代码，再不输出点东西脑子要溢出了。这里没有正确的废话，只有踩过的坑、读过的源码、用过的工具——每一个结论背后都有一段不想回忆的 debug 经历。

- [user.md](profile/user.md) — 我是谁，我在乎什么
- [memory.md](profile/memory.md) — 我最近在做什么，关心什么

## 目录

- [技术笔记](tech/index.md) — 框架、工具
  - [AI 编程工具链](tech/ai-tooling/index.md) — 26 篇
  - [Claude Code](tech/claude-code/index.md) — 4 篇
    - [Claude Code 最佳实践：从 vibe coding 到 agentic engineering](tech/claude-code/claude-code-best-practice.md) — 2026-06-26
  - [开发工具](tech/dev-tools/index.md) — 19 篇
    - [watchexec：文件变了就自动跑命令](tech/dev-tools/watchexec-guide.md) — 2026-07-03
    - [bacon：Rust 开发者最该开着不关的终端窗口](tech/dev-tools/bacon-guide.md) — 2026-07-03
  - [容器化系列](tech/containerization/index.md) — 5 篇
  - [Robot Framework](tech/robotframework/index.md) — 1 篇
  - [逆向工具链](tech/reversing/index.md) — 6 篇
  - [AI Agent 系列](tech/ai-agent/index.md) — 13 篇
  - [NewsNow](tech/newsnow/index.md) — 1 篇
  - [向量数据库系列](tech/vector-db/index.md) — 4 篇
  - [Neo4j](tech/neo4j/index.md) — 1 篇
  - [HTTP 协议系列](tech/http/index.md) — 9 篇
    - [RESTful API 设计](tech/http/restful-api-guide.md) — 2026-06-22
    - [GraphQL](tech/http/graphql-guide.md) — 2026-06-22
    - [gRPC](tech/http/grpc-guide.md) — 2026-06-22
- [编程语言](languages/index.md) — 语法、特性
  - [Python](languages/python/index.md)
    - [Python exec 与 eval：危险的动态代码执行](languages/python/exec-eval.md) — 2026-06-19
    - [Python 描述器：`obj.x` 背后究竟发生了什么](languages/python/descriptors.md) — 2026-06-16
    - [Python functools：标准库里最被低估的模块](languages/python/functools.md) — 2026-06-15
    - [Python 并发编程：threading、multiprocessing、asyncio 怎么选](languages/python/concurrency.md) — 2026-06-11
    - [Python 类型提示：从 Any 到 Protocol 的渐进类型之路](languages/python/type-hints.md) — 2026-06-04
    - [Python 面向对象系列](languages/python/oop/index.md) — 2026-06-04（5 篇）
    - [Python 闭包：函数为什么能“记住”外部变量](languages/python/closures.md) — 2026-05-31
    - [Python 装饰器：从函数到可调用对象的完整理解](languages/python/decorators.md) — 2026-05-30
    - [Python 模块系统：每一个 import 背后发生了什么](languages/python/modules.md) — 2026-05-30
    - [Python 异步编程：从回调地狱到 async/await](languages/python/async-await.md) — 2026-05-30
    - [with 语句：上下文管理器的正确打开方式](languages/python/with-statement.md) — 2026-05-17
    - [yield 与生成器：惰性求值的艺术](languages/python/yield-statement.md) — 2026-05-17
  - [Go](languages/golang/index.md)
    - [Go Context：一根贯穿所有 goroutine 的线](languages/golang/context.md) — 2026-07-03
    - [Go 面向对象系列](languages/golang/oop/index.md) — 2026-06-07（5 篇）
    - [Go Channel 系列](languages/golang/channels/index.md) — 2026-06-04（4 篇）
    - [Go Goroutine 系列](languages/golang/goroutine/index.md) — 2026-06-04（4 篇）
    - [Go 单元测试：标准库就够了](languages/golang/unit-testing.md) — 2026-05-30
  - [Java](languages/java/index.md)
    - [Java 单元测试：JUnit 5 不是唯一解](languages/java/unit-testing.md) — 2026-05-30
  - [Node.js](languages/nodejs/index.md)
    - [Node.js 错误处理：别让一个未捕获的异常崩了你的服务](languages/nodejs/error-handling.md) — 2026-07-03
    - [Node.js V8 内存管理：你的内存去哪了](languages/nodejs/v8-memory.md) — 2026-07-03
    - [Node.js Buffer：二进制数据处理](languages/nodejs/buffer.md) — 2026-06-15
    - [Node.js 进程与线程：cluster、worker_threads 与 child_process](languages/nodejs/process-and-threads.md) — 2026-06-11
    - [Node.js Stream：数据不是一次性搬完的](languages/nodejs/stream.md) — 2026-06-08
    - [Node.js 事件循环：理解了它才算真会用](languages/nodejs/event-loop.md) — 2026-05-30
    - [Node.js 最新版本实用特性盘点](languages/nodejs/practical-features.md) — 2026-05-27
  - [React](languages/react/index.md)
    - [React 入门到精通教程](languages/react/tutorial/index.md) — 2026-06-10（5 篇）
    - [React 心智模型：声明式 UI 到底改变了什么](languages/react/react-mental-model.md) — 2026-06-10
    - [React Hooks 不完全设计史：闭包陷阱与依赖数组](languages/react/react-hooks-design.md) — 2026-06-10
    - [React 渲染机制：Virtual DOM、Fiber 与批量更新](languages/react/react-rendering.md) — 2026-06-10
    - [React 19：Server Components 是对 Web 架构的重新分层](languages/react/react-19-server-components.md) — 2026-06-10
    - [React 19 新 API 全景：Actions 与状态管理新范式](languages/react/react-19-new-apis.md) — 2026-06-10
  - [Rust](languages/rust/index.md)
    - [Rust LazyLock：延迟初始化的标准答案](languages/rust/lazy-lock.md) — 2026-06-29
    - [Unsafe Rust：编译器让开，我自己保证安全](languages/rust/unsafe-rust.md) — 2026-07-03
    - [Rust 闭包：FnOnce、FnMut、Fn 的区别](languages/rust/closures.md) — 2026-06-15
    - [Rust 生命周期：'a 不是魔法，是编译器在检查指针有效期](languages/rust/lifetimes.md) — 2026-06-04
    - [Rust Box\<dyn\>：trait 对象与动态分发完全理解](languages/rust/box-dyn.md) — 2026-06-07
    - [Rust Arc：多线程共享所有权的正确姿势](languages/rust/arc.md) — 2026-06-07
    - [Rust 模块系统：一个文件不是天然模块](languages/rust/modules.md) — 2026-05-30
    - [Rust Trait 与泛型：多态不只是继承](languages/rust/traits-generics.md) — 2026-05-30
    - [Rust 单元测试：编译器帮你测](languages/rust/unit-testing.md) — 2026-05-27
    - [Rust 错误处理：Result、Option 和 ? 运算符](languages/rust/error-handling.md) — 2026-05-27
    - [Rust 所有权：三张图看懂最核心的概念](languages/rust/ownership.md) — 2026-05-24
  - [Solidity](languages/solidity/index.md)
    - [Solidity 系列](languages/solidity/index.md) — 2026-06-15（7 篇）
- [项目复盘](project-retro/index.md) — 项目回顾与总结
- [架构设计](architecture/index.md) — 系统设计、技术方案
  - [设计模式：Rust 视角](architecture/design-patterns/index.md) — 2026-06-19（6/23）
    - [Builder 模式：Rust 里最自然的构造方式](architecture/design-patterns/builder.md) — 2026-06-16
  - [基金溢价数据设计](architecture/fund-premium-data.md) — 2026-05-24
- [阅读笔记](reading/index.md) — 书、文章、视频的读后记录
- [源码阅读](source-read/index.md) — 开源项目的源码分析
  - [nanobot 源码阅读系列](source-read/nanobot_notes/) — 2026-06-16（6 篇）
  - [TrendRadar 源码阅读系列](source-read/trend_radar/index.md) — 2026-06-11（6 篇）
  - [QuantDinger 源码阅读系列](source-read/quant_dinger/01-intro.md) — 2026-05-30（7 篇）
  - [Sequoia-X 源码阅读系列](source-read/sequoia_x/index.md) — 2026-05-17（5 篇）
- [随想](thoughts/index.md) — 非技术类的日常思考
  - [跨服务约定：一套我自己维护的工程纪律](thoughts/cross-service-conventions.md) — 2026-06-10

- [运动打卡](exercise/index.md) — 每天动一下，不让身体生锈

## 开发环境

`./scripts/setup.sh` 个人当前使用环境，一键安装。
