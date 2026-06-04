# Python 面向对象（四）：魔法方法——像内置类型一样工作

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

前三篇覆盖了 class 基础、封装、继承。这一篇讲魔法方法——以双下划线开头和结尾的特殊方法。它们让你的自定义类可以像 Python 内置类型一样参与运算符、比较、迭代、上下文管理。

## 为什么需要魔法方法

```python
# 没有魔法方法——每次都要记方法名
v1 = Vector(3, 4)
v2 = Vector(1, 2)
# result = v1.plus(v2)       # Java 风格
# result = v1.add(v2)        # 还是 Java 风格

# 有了魔法方法——像内置类型一样用
result = v1 + v2              # Python 风格——直接用 +
```

魔法方法让你的类融入 Python 的语言体系——调用方不需要知道底层实现，只需使用标准的 Python 语法。

## `__repr__` 和 `__str__`——两个最该写的方法

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        """给开发者看的——尽可能精确，最好能 eval 还原"""
        return f"Vector({self.x!r}, {self.y!r})"

    def __str__(self):
        """给用户看的——简洁可读"""
        return f"({self.x}, {self.y})"

v = Vector(3, 4)
print(v)          # (3, 4)——print 调 __str__
print(repr(v))    # Vector(3, 4)——repr() 调 __repr__

# 没有 __str__ 时，__repr__ 作为 fallback
# 没有 __repr__ 时，默认输出 <Vector object at 0x...>——完全没用
```

**`__repr__` 几乎永远该写**。调试时 `print(obj)` 输出 `<__main__.Vector object at 0x...>` 是零信息量的。

## `__eq__` 和 `__hash__`——让对象可比、可哈希

```python
class User:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id

    def __hash__(self):
        """相等对象必须有相同 hash"""
        return hash(self.user_id)

    def __repr__(self):
        return f"User(id={self.user_id!r}, name={self.name!r})"

u1 = User(1, "Alice")
u2 = User(1, "Alice")
u3 = User(2, "Bob")

print(u1 == u2)        # True ——有 __eq__，比较 user_id
print(u1 == u3)        # False

# 可以放进 set 和 dict key——需要 __hash__
users = {u1, u2, u3}
print(len(users))      # 2——u1 和 u2 被当作同一个对象
```

黄金法则：**如果重写 `__eq__`，必须重写 `__hash__`**。相等对象的 hash 必须相同，否则 dict 和 set 的行为会出错。如果对象是可变的，直接把 `__hash__` 设为 `None` 来禁用哈希。

`NotImplemented` vs `NotImplementedError`：

```python
def __eq__(self, other):
    if not isinstance(other, User):
        return NotImplemented  # ← 告诉 Python "我不知道怎么比较"
    return self.user_id == other.user_id

# NotImplemented 让 Python 尝试反过来调 other.__eq__(self)
# NotImplementedError 是异常——语义完全不同
```

## 运算符重载

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):         # self + other
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other):         # self - other
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):        # self * scalar
        return Vector(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):       # scalar * self
        return self.__mul__(scalar)

    def __neg__(self):                # -self
        return Vector(-self.x, -self.y)

    def __abs__(self):                # abs(self)
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __bool__(self):               # bool(self)——零向量为 False
        return self.x != 0 or self.y != 0

    def __repr__(self):
        return f"Vector({self.x!r}, {self.y!r})"

v1 = Vector(3, 4)
v2 = Vector(1, 2)

print(v1 + v2)       # Vector(4, 6)
print(v1 * 2)        # Vector(6, 8)
print(2 * v1)        # Vector(6, 8)——rmul 被调用
print(abs(v1))       # 5.0
print(bool(Vector(0, 0)))  # False
```

`__rmul__`（right multiply）解决 `2 * v1` 的问题——Python 先尝试 `int.__mul__(2, v1)`，返回 `NotImplemented`，然后尝试 `v1.__rmul__(2)`。

## 让对象像容器：`__getitem__`、`__iter__`、`__len__`

```python
class Vector:
    # ... 上面的代码 ...

    def __len__(self):
        return 2     # 2D 向量是二维的

    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Vector index out of range")

    def __iter__(self):
        yield self.x
        yield self.y

v = Vector(3, 4)
print(len(v))               # 2
print(v[0], v[1])           # 3 4
x, y = v                    # 解包——调用 __iter__
for coord in v:             # 迭代——调用 __iter__
    print(coord)
```

实现了 `__getitem__` 和支持 sequence protocol，实现了 `__iter__` 支持迭代。两者都实现时，迭代优先走 `__iter__`。

## 上下文管理器：`__enter__` + `__exit__`

```python
class Transaction:
    """数据库事务——自动 commit 或 rollback"""
    def __init__(self, account):
        self.account = account
        self.original_balance = account._balance

    def __enter__(self):
        print("事务开始")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 有异常——回滚
            self.account._balance = self.original_balance
            print(f"事务回滚: {exc_val}")
        else:
            print("事务提交")
        return False  # False = 不吞异常，继续向上传播

from dataclasses import dataclass

@dataclass
class Account:
    owner: str
    _balance: float = 0

    def deposit(self, amount):
        self._balance += amount

    def withdraw(self, amount):
        if amount > self._balance:
            raise ValueError("余额不足")
        self._balance -= amount

acc = Account("Alice", 1000)
try:
    with Transaction(acc):
        acc.deposit(500)
        acc.withdraw(200)
        raise ValueError("Something went wrong")
except ValueError:
    pass

print(acc._balance)  # 1000——回滚到事务开始前的值
```

`__exit__` 的三个参数：异常类型、异常值、traceback。没有异常时三者都是 `None`。返回 `True` 会吞掉异常（不推荐），返回 `False` 让异常继续传播。

## 总结

最常用的魔法方法优先级：

| 必须写 | `__repr__` |
|--------|-----------|
| 需要比较 | `__eq__` + `__hash__` |
| 需要运算符 | `__add__` / `__sub__` / `__mul__` + `__rmul__` |
| 需要 bool 判断 | `__bool__` |
| 需要迭代/索引 | `__iter__` / `__getitem__` |
| 资源管理 | `__enter__` + `__exit__` |

不需要全部实现——按需选择。`__repr__` 是唯一一个写了永远不会后悔的。

最后一篇讲进阶特性——`__slots__`、`@dataclass`、ABC、metaclass、以及组合 vs 继承的选择。

→ [（五）进阶特性：slots、dataclass、ABC 与 metaclass](05-advanced.md)
