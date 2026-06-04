# Python 面向对象（五）：进阶特性——slots、dataclass、ABC 与 metaclass

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

最后一篇覆盖 Python OOP 的进阶主题：`__slots__` 内存优化、`@dataclass` 自动生成代码、ABC 接口契约、metaclass 类工厂、以及组合 vs 继承的设计选择。

## `__slots__`——用空间换灵活性

默认每个 Python 实例有一个 `__dict__` 字典来存属性——灵活但耗内存（每个实例 ~100+ bytes 的 dict 开销）。`__slots__` 用 C 级数组替代：

```python
class Point:
    __slots__ = ('x', 'y')        # 只允许这两个属性

    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.x = 3     # ✅
# p.z = 4   # ❌ AttributeError: 'Point' object has no attribute 'z'
# p.__dict__ # ❌ 没有 __dict__
```

| | 默认 | `__slots__` |
|---|---|---|
| `__dict__` | ✅ | ❌（除非手动加 `'__dict__'` 到 slots 里） |
| 动态加属性 | ✅ | ❌ |
| 内存占用 | ~104 bytes/实例（dict 开销） | ~8 bytes/slot |
| 属性访问速度 | dict lookup | 数组索引——更快 |
| 适用场景 | 少量实例 | 百万级实例 |

**不要过早使用 `__slots__`**。大多数代码只创建几十到几百个实例——dict 开销完全忽略。当你真的创建了海量实例（金融交易记录、游戏粒子、数据流中的事件）才需要考虑。

## `@dataclass`——停止手写 `__init__`（Python 3.7+）

```python
from dataclasses import dataclass, field
from typing import ClassVar
import time

@dataclass
class Trade:
    symbol: str
    price: float
    quantity: int
    side: str = "buy"                            # 默认值
    timestamp: float = field(default_factory=time.time)
    tags: list = field(default_factory=list)     # 可变默认值必须用 default_factory
    _id: int = field(default=0, repr=False)      # 不出现在 __repr__ 里

    # 类变量——所有实例共享，不计入字段
    exchange: ClassVar[str] = "NASDAQ"

    def value(self):
        """自定义方法——dataclass 不限制你加自己的方法"""
        return self.price * self.quantity

# 自动生成：__init__, __repr__, __eq__
t1 = Trade("AAPL", 185.5, 100)
t2 = Trade("AAPL", 185.5, 100)
print(t1)              # Trade(symbol='AAPL', price=185.5, quantity=100, side='buy', ...)
print(t1 == t2)        # True
print(t1.value())      # 18550.0
print(Trade.exchange)  # "NASDAQ"
```

**`frozen=True` 的陷阱**：

```python
@dataclass(frozen=True)
class ImmutableConfig:
    host: str
    tags: list = field(default_factory=list)

c = ImmutableConfig("localhost")
c.host = "remote"   # ❌ FrozenInstanceError
c.tags.append("x")  # ✅ 这居然可以——list 本身可变，frozen 只保护引用
```

`frozen=True` 是浅不可变——字段引用不能改，但引用指向的可变对象内容仍可改。和 Rust 的所有权语义完全不同。

### dataclass vs namedtuple vs 手写

```python
# namedtuple（Python 3.1+）——不可变、轻量、可哈希
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])
p = Point(1, 2)
print(p.x, p[0])   # namedtuple 支持索引访问
# p.x = 3          # ❌ 不可变

# dataclass——可变、可自定义方法、可设默认值
@dataclass
class Point3D:
    x: float
    y: float
    z: float = 0.0
    def distance(self):
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

# 手写——最大控制力，但样板代码最多
```

选型：不可变 + 简单数据 → namedtuple。需要方法 + 默认值 + 类型注解 → dataclass。需要极致的定制逻辑 → 手写。

## ABC——抽象基类，定义接口契约

```python
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def charge(self, amount: float) -> bool:
        """扣款——子类必须实现"""
        ...

    @abstractmethod
    def refund(self, transaction_id: str) -> bool:
        """退款——子类必须实现"""
        ...

    def log_transaction(self, amount: float):
        """日志——提供默认实现，子类可选覆盖"""
        print(f"[Payment] {amount} processed")

class StripeProcessor(PaymentProcessor):
    def charge(self, amount):
        print(f"Stripe charged {amount}")
        return True

    def refund(self, transaction_id):
        print(f"Stripe refunded {transaction_id}")
        return True

# processor = PaymentProcessor()  # ❌ 不能实例化抽象类
processor = StripeProcessor()     # ✅
print(isinstance(processor, PaymentProcessor))  # True
```

ABC 的价值不是「强制子类实现方法」——Python 的 duck typing 本来就不关心这个。它的价值是：
1. **让 IDE 和类型检查器在你遗漏方法时报错**
2. **`isinstance(obj, PaymentProcessor)` 做结构化判断**

## metaclass——当类本身需要被定制时

```python
class Meta(type):
    def __new__(mcs, name, bases, namespace):
        """创建类时调用——在 class 语句执行完之后"""
        # 自动给所有公开方法加上日志
        for attr_name, attr_value in namespace.items():
            if callable(attr_value) and not attr_name.startswith('_'):
                namespace[attr_name] = mcs._add_log(attr_value)
        return super().__new__(mcs, name, bases, namespace)

    @staticmethod
    def _add_log(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[LOG] Calling {func.__name__}")
            return func(*args, **kwargs)
        return wrapper

class Service(metaclass=Meta):
    def process(self):
        print("Processing...")

s = Service()
s.process()
# [LOG] Calling process
# Processing...
```

metaclass 的调用时机：

```mermaid
flowchart LR
    ClassStmt["class 语句"] --> BodyExec["执行类体"]
    BodyExec --> Collect["收集 namespace dict"]
    Collect --> MetaCall["Meta.__new__ + __init__"]
    MetaCall --> ClassObj["返回类对象"]
```

metaclass 是 Python 最底层的钩子——Django ORM、abc.ABCMeta、singleton 模式都靠它。

**但绝大多数代码不需要 metaclass。** 替代方案：

```python
# 用 __init_subclass__ 实现插件注册——不需要 metaclass（Python 3.6+）
class PluginBase:
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        """子类定义时自动调用——不需要 metaclass"""
        super().__init_subclass__(**kwargs)
        PluginBase._registry[cls.__name__] = cls

class PDFExporter(PluginBase):
    pass

class CSVExporter(PluginBase):
    pass

print(PluginBase._registry)
# {'PDFExporter': <class 'PDFExporter'>, 'CSVExporter': <class 'CSVExporter'>}
```

能用类装饰器或 `__init_subclass__` 实现，就不要用 metaclass。

## 组合 vs 继承

```python
# ❌ 用继承表达了错误的关系
class Stack(list):           # Stack is a list？不是——Stack HAS a list
    def push(self, item):
        self.append(item)

# 问题：Stack 继承了 list 的所有方法——insert、remove、sort——
# 它们都暴露在外面，破坏了 Stack 的 LIFO 语义

s = Stack()
s.push(1)
s.insert(0, 99)   # 栈可以从中间插入？语义崩坏

# ✅ 组合——Stack HAS a list
class Stack:
    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        return self._items.pop()

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)
```

判断规则：**如果能说「B 是一个 A」→ 继承。如果只能说「B 有一个 A」→ 组合。**

## 总结

五篇系列覆盖了 Python OOP 的完整栈：

```mermaid
mindmap
  Python OOP
    基础
      class 语句
      __init__ / __new__
      self 不是关键字
      instance vs class 属性
      @classmethod / @staticmethod
    封装
      单下划线约定
      name mangling
      @property
    继承
      super() 和 MRO
      C3 线性化
      Mixin 模式
    魔法方法
      __repr__ __str__
      __eq__ __hash__
      运算符重载
      上下文管理器
    进阶
      __slots__
      @dataclass
      ABC
      metaclass
      __init_subclass__
      组合 vs 继承
```

Python OOP 的核心思想：**类和实例都是运行时可修改的对象——class 语句不是蓝图，是运行时代码**。这让你可以做到静态语言做不到的事（运行时动态修改类、用 metaclass 截获类创建过程），但也意味着你不能依赖编译器来保证封装和继承——约定和测试是 Python 世界里代替编译器检查的保障。
