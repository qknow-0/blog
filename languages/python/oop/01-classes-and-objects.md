# Python 面向对象（一）：class、实例与对象模型

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

Python 的 OOP 不是 Java/C++ 的翻版。第一篇从最基础的 `class` 关键字讲起——类是怎么创建的、`self` 到底是什么、实例属性和类属性有什么区别、三种 method 各有什么用途。

## `class` 语句做了什么

```python
class Account:
    """银行账户"""

    bank_name = "Python Bank"     # 类属性——所有实例共享
    _total_accounts = 0            # 约定私有（单下划线）

    def __init__(self, owner, balance=0):
        self.owner = owner         # 实例属性——每个实例独有
        self._balance = balance
        Account._total_accounts += 1

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("存款金额必须 > 0")
        self._balance += amount
        return self._balance

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("取款金额必须 > 0")
        if amount > self._balance:
            raise ValueError("余额不足")
        self._balance -= amount
        return self._balance

    def __repr__(self):
        return f"Account(owner={self.owner!r}, balance={self._balance!r})"
```

`class` 是一个**运行时可执行语句**——不是静态声明。Python 执行 `class` 语句时，创建一个新的 namespace、执行类体里的代码、把结果收集到一个 dict 里，最后调用 `type(name, bases, namespace)` 创建类对象。

```python
# class 语句等价于：
def __init__(self, owner, balance=0): ...
def deposit(self, amount): ...

namespace = {
    '__init__': __init__,
    'deposit': deposit,
    'bank_name': "Python Bank",
    ...
}
Account = type('Account', (), namespace)
```

这意味着你可以在类体里写任意 Python 代码——循环、条件判断、甚至调用外部函数——它们都会在类创建时执行。

## `__init__` 不是构造函数

```python
a = Account("Alice", 100)

# 实际发生的事情：
# 1. Account.__new__(Account)   → 创建一个空的 Account 实例
# 2. Account.__init__(a, "Alice", 100) → 给实例填充属性
```

- `__new__` 是构造器——负责创建并返回实例。几乎从不重写（除了继承不可变类型和 singleton）
- `__init__` 是初始化器——实例已经有了，往里填数据

大部分时候你只需要关心 `__init__`。

## 实例属性 vs 类属性——关键差别

```python
a1 = Account("Alice", 100)
a2 = Account("Bob", 200)

print(a1.bank_name)      # "Python Bank"——来自类属性
print(a2.bank_name)      # "Python Bank"——同上
print(Account.bank_name) # "Python Bank"——直接从类访问

# 给实例赋值不会覆盖类属性——而是在实例上创建同名属性
a1.bank_name = "My Bank"
print(a1.bank_name)      # "My Bank"——实例属性遮蔽了类属性
print(a2.bank_name)      # "Python Bank"——a2 没有实例属性，找到类
print(Account.bank_name) # "Python Bank"——类属性没变
```

属性查找链：`instance.__dict__` → `class.__dict__` → 父类 `.__dict__`（沿 MRO 上溯）。

```python
# 可以直接看到查找链的结果
print(a1.__dict__)  # {'owner': 'Alice', '_balance': 100, 'bank_name': 'My Bank'}
print(a2.__dict__)  # {'owner': 'Bob', '_balance': 200}
# a2 没有 bank_name，所以向上找到 Account.bank_name == "Python Bank"
```

类属性适合存所有实例共享的状态——计数器、配置常量、默认值。实例属性适合每个实例不同的状态。

**可变类属性的陷阱**：

```python
class Team:
    members: list = []    # ❌ 所有实例共享同一个 list！

t1 = Team()
t2 = Team()
t1.members.append("Alice")
print(t2.members)         # ["Alice"]——t2 也被影响了

# 正确做法：类属性声明类型，实例属性在 __init__ 里初始化
class Team:
    members: list   # 只声明类型，不设默认值

    def __init__(self):
        self.members: list = []  # 每个实例有自己独立的 list
```

## `self` 不是关键字

`self` 只是一个参数名的约定——你可以用 `this`：

```python
class Foo:
    def bar(this):         # 合法，但别这么做
        print(this)

Foo.bar(Foo())             # 显式传 self
Foo().bar()                # 语法糖——实例自动作为第一个参数传入
```

方法调用 `obj.method(arg)` 在底层等价于 `Class.method(obj, arg)`。Python 通过 descriptor protocol 把函数「绑定」到实例上，自动填充第一个参数。

```python
# 验证
print(Account.deposit)     # <function Account.deposit at 0x...>（普通函数）
print(a1.deposit)          # <bound method Account.deposit of Account(...)>（已绑定）

# 两者等效
Account.deposit(a1, 50)    # 显式传 self
a1.deposit(50)             # 隐式传 self
```

## 三种 method

```python
from datetime import date

class Person:
    species = "Homo sapiens"

    def __init__(self, name, birth_year):
        self.name = name
        self.birth_year = birth_year

    # 实例方法——访问 self
    def age(self):
        return date.today().year - self.birth_year

    # 类方法——访问 cls，常用于替代构造函数
    @classmethod
    def from_birth_date(cls, name, birth_date_str):
        """从日期字符串创建 Person——'1990-05-15'"""
        year = int(birth_date_str.split('-')[0])
        return cls(name, year)

    # 静态方法——不访问 self 也不访问 cls
    @staticmethod
    def is_valid_name(name):
        """就是放在类命名空间里的普通函数"""
        return isinstance(name, str) and len(name) > 0
```

选择指南：

| 需要访问什么 | 用什么 |
|-------------|--------|
| 实例数据（`self.xxx`） | instance method |
| 类数据（`cls.xxx`）或创建实例 | `@classmethod` |
| 都不需要，但逻辑上属于这个类 | `@staticmethod` |

`@classmethod` 最常见的使用场景是替代构造函数：

```python
from datetime import datetime
dt = datetime.fromisoformat("2026-06-04")  # classmethod——返回 datetime 实例
dt = datetime.now()                        # classmethod
```

## 总结

这一篇的核心认知：

1. `class` 是运行时代码，不是静态声明——类体里的代码真的会被执行
2. `__init__` 是初始化器，`__new__` 才是构造器——但你几乎只用 `__init__`
3. 属性查找从实例 dict 开始，沿 MRO 链上溯到类 dict
4. `self` 不是关键字——是 descriptor protocol 自动绑定的结果
5. `@classmethod` + `@staticmethod` 各有明确的使用场景

第二篇讲封装——Python 没有真正的 private，那它是怎么保护数据不被随意篡改的？

→ [（二）封装与属性：Python 的数据隐藏之道](02-encapsulation.md)
