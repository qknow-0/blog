# 设计模式：Rust 视角

用 Rust 的类型系统重新审视 GoF 23 个设计模式——哪些被语言特性替代了，哪些有了更 Rust 的实现方式。系列基于 Rust 1.95 稳定版，涉及特性标注最低支持版本。

## 创建型

| 模式 | Rust 关键点 | 状态 |
|---|---|---|
| [Singleton](singleton.md) | `OnceLock` / `lazy_static`；Rust 不鼓励全局可变状态 | ✅ |
| [Factory Method](factory-method.md) | trait 关联类型 + 泛型 | ✅ |
| [Abstract Factory](abstract-factory.md) | trait 组合表达产品族 | ✅ |
| [Builder](builder.md) | Rust 最惯用的模式；生命周期确保 build() 消费 builder | ✅ |
| [Prototype](prototype.md) | `Clone` trait；显式深拷贝 | ✅ |

## 结构型

| 模式 | Rust 关键点 | 状态 |
|---|---|---|
| [Adapter](adapter.md) | newtype 模式 + trait 实现 | ✅ |
| Bridge | trait 对象 vs 泛型；编译期 vs 运行时分发 | 待写 |
| Composite | enum 递归类型 + `Box<dyn>` | 待写 |
| Decorator | trait 组合 + `impl Trait` | 待写 |
| Facade | 模块可见性控制 `pub(crate)` | 待写 |
| Flyweight | `Arc<str>` / `internment`；零拷贝减少需求 | 待写 |
| Proxy | 智能指针 `Deref` | 待写 |

## 行为型

| 模式 | Rust 关键点 | 状态 |
|---|---|---|
| Chain of Responsibility | Iterator + fold | 待写 |
| Command | 闭包 Fn/FnMut/FnOnce + async | 待写 |
| Iterator | 标准库一等公民；for 循环语法糖 | 待写 |
| Mediator | channel 通信 vs 对象引用 | 待写 |
| Memento | serde 序列化；所有权防止非法状态 | 待写 |
| Observer | `tokio::watch` / 事件 channel | 待写 |
| State | enum + match 替代 State 类继承 | 待写 |
| Strategy | trait 泛型静态分发 vs `dyn Trait` 动态分发 | 待写 |
| Template Method | trait 默认方法实现 | 待写 |
| Visitor | enum + match vs 传统 Visitor | 待写 |
