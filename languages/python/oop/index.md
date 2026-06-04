# Python 面向对象系列

从 `class` 关键字到 metaclass，系统理解 Python 的面向对象模型。

## 阅读顺序

1. **[（一）class、实例与对象模型](01-classes-and-objects.md)** — 2026-06-04
   - `class` 语句的执行过程、`__init__` vs `__new__`、实例属性 vs 类属性、三种 method

2. **[（二）封装与属性](02-encapsulation.md)** — 2026-06-04
   - 命名约定、name mangling 的真正用途、`@property` 与 descriptor protocol

3. **[（三）继承与 MRO](03-inheritance.md)** — 2026-06-04
   - `super()` 的正确理解、C3 线性化、Mixin 模式

4. **[（四）魔法方法](04-magic-methods.md)** — 2026-06-04
   - `__repr__`/`__eq__`/`__hash__`、运算符重载、上下文管理器

5. **[（五）进阶特性](05-advanced.md)** — 2026-06-04
   - `__slots__`、`@dataclass`、ABC、metaclass、组合 vs 继承
