# Go 面向对象系列

Go 没有 class、没有继承、没有 `implements` 关键字——但它有一套更简洁的 OOP 方式。五篇覆盖 Go 面向对象编程的全部核心机制。

## 阅读顺序

1. **[（一）结构体与方法：Go 没有 class，但有更轻量的替代](01-struct-and-methods.md)** — 2026-06-07
   - 结构体是数据的骨架、方法是绑定到类型的函数、值接收者 vs 指针接收者

2. **[（二）嵌入与组合：Go 对继承的回答](02-embedding.md)** — 2026-06-07
   - struct embedding 怎么替代继承、方法提升、字段提升、composition over inheritance

3. **[（三）隐式接口：Go 最与众不同的设计](03-interfaces.md)** — 2026-06-07
   - 不用 `implements` 声明、接口自动满足、小接口哲学、`interface{}` 到 `any`

4. **[（四）多态与类型断言：接口之下的灵活性](04-polymorphism.md)** — 2026-06-07
   - 基于接口的多态、type assertion、type switch、空接口的用法与陷阱

5. **[（五）惯用模式：Functional Options 与组合之道](05-patterns.md)** — 2026-06-07
   - Functional Options、Builder、Decorator、accept interfaces return structs
