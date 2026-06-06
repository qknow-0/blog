# Python 类型提示：从 Any 到 Protocol 的渐进类型之路

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

Python 的类型系统是**渐进式的**——不需要一步到位全标注，可以一个函数一个函数地加。本文从最基础的标注讲起，覆盖泛型、Protocol、TypedDict、以及类型检查器实际在做什么。

## 为什么需要类型提示

在一个没有类型标注的函数里：

```python
def process_order(order, user_id, options=None):
    items = get_items(order)
    total = sum(i.price for i in items)
    charge(user_id, total, options)
    return total
```

五个问题只能靠查代码回答：
- `order` 是 dict 还是对象？
- `user_id` 是 int 还是 str？
- `options` 的合法键是什么？
- `get_items` 返回什么类型？
- `charge` 会不会抛异常？

类型标注把这些问题从运行时挪到编码时：

```python
from typing import Optional

def process_order(
    order: Order,
    user_id: int,
    options: Optional[PaymentOptions] = None,
) -> float:
    items: list[LineItem] = get_items(order)
    total = sum(i.price for i in items)
    charge(user_id, total, options)
    return total
```

IDE 自动补全变准了——它知道 `i` 是 `LineItem`、知道 `i.price` 存在。重构时改了 `Order` 的字段名，所有调用方立刻标红。类型标注换来的是**阅读速度和重构信心**。

## 基础标注

```python
# 基本类型
name: str = "Alice"
age: int = 30
price: float = 99.9
active: bool = True

# 函数签名
def greet(name: str) -> str:
    return f"Hello, {name}"

# 可选类型——可以是 None
from typing import Optional
def find_user(user_id: int) -> Optional[User]:
    ...

# Python 3.10+ 可以用 X | None 替代 Optional[X]
def find_user(user_id: int) -> User | None:
    ...

# 容器类型（Python 3.9+ 原生支持）
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 95, "Bob": 87}
unique_ids: set[int] = {1, 2, 3}
pairs: tuple[str, float] = ("BTC", 68000.0)

# Union——多种类型之一
from typing import Union
def parse(value: str) -> Union[int, float]:
    ...

# Python 3.10+ 简写
def parse(value: str) -> int | float:
    ...

# Any——关掉类型检查
from typing import Any
def load_config(path: str) -> dict[str, Any]:
    ...
```

## 协议与结构——不用继承的类型约束

Python 的 duck typing 和类型系统天然有紧张关系。`Protocol` 解决了这个问题：

```python
from typing import Protocol

class SupportsClose(Protocol):
    def close(self) -> None: ...

class SupportsRead(Protocol):
    def read(self, size: int) -> str: ...

def cleanup(resource: SupportsClose) -> None:
    resource.close()

# 任何有 close() 方法的对象都满足 SupportsClose
# 不需要显式继承 SupportsClose
cleanup(open("file.txt"))       # ✅ file 有 close()
cleanup(db_connection)           # ✅ 连接有 close()
cleanup(socket)                  # ✅ socket 有 close()
```

这和 Java 的 interface 或 Go 的 interface 完全不同——**不需要在被标注的类上声明 `implements SupportsClose`**。类型检查器做的是结构匹配：查看对象上有没有 `close()` 方法，有就通过。Python 的 duck typing 和类型系统在 `Protocol` 这里握手了。

## TypedDict——给 dict 标注特定键

```python
from typing import TypedDict

class APIResponse(TypedDict):
    status: str
    data: dict[str, object]
    error: str | None

def handle(response: APIResponse) -> None:
    if response["status"] == "error":
        print(response["error"])      # ✅ 类型检查器知道 error 存在
    data = response["data"]

# 对比：
# dict[str, Any] → 类型检查器不知道有哪些键、不知道每个键的类型
# APIResponse    → 知道有 status (str)、data (dict)、error (str | None)
```

**TypedDict 不创建新的类——只影响类型检查，不影响运行时**。代码运行时它就是普通 dict，零开销。`NotRequired` 表示可选键（Python 3.11+）：

```python
from typing import TypedDict, NotRequired

class Config(TypedDict):
    host: str
    port: int
    debug: NotRequired[bool]    # 可选的键
```

## 泛型——函数和类型的参数

```python
# 泛型函数——T 表示「什么类型都行，但输入和输出类型相同」
from typing import TypeVar

T = TypeVar('T')

def first(items: list[T]) -> T | None:
    return items[0] if items else None

x = first([1, 2, 3])          # x: int | None
y = first(["a", "b"])         # y: str | None
# 类型检查器自动推断 T 的具体类型

# 泛型类
K = TypeVar('K')
V = TypeVar('V')

class LRUCache(dict[K, V]):
    def __init__(self, max_size: int):
        self.max_size = max_size

    def get(self, key: K) -> V | None:
        return super().get(key)

cache = LRUCache[str, int](max_size=100)
cache["key"] = 42             # ✅
# cache["key"] = "wrong"      # ❌ LRUCache[str, int] 要求值是 int
```

**TypeVar 可以有约束**：

```python
# 只接受 int 或 float
Number = TypeVar('Number', int, float)

def add(a: Number, b: Number) -> Number:
    return a + b              # 类型检查器知道返回值也是 int 或 float
```

## Literal——限制参数为特定字面量

```python
from typing import Literal

def set_mode(mode: Literal["read", "write", "append"]) -> None:
    ...

set_mode("read")              # ✅
set_mode("delete")            # ❌ "delete" 不在允许列表中
```

实践中最有用的场景是——把原来用 str 表达的枚举语义变明确：

```python
# 之前——caller 不知道传什么
def connect(protocol: str) -> None: ...
# connect("http") 还是 connect("HTTP") 还是 connect("Http")？

# 之后——IDE 自动补全，传错立刻标红
def connect(protocol: Literal["http", "https", "ws", "wss"]) -> None: ...
```

## overload——同一个函数，不同的参数组合

```python
from typing import overload

@overload
def get_user(identifier: int) -> User | None: ...

@overload
def get_user(identifier: str) -> User | None: ...

@overload
def get_user(identifier: int, include_deleted: bool) -> User | None: ...

def get_user(identifier: int | str, include_deleted: bool = False) -> User | None:
    # 实际的实现——只有一个
    ...
```

`@overload` 的签名**不执行**——只是给类型检查器看的。实际的函数体是最后一个 `def`。典型用途：同一个函数根据参数不同返回不同形状的结果。

## final——禁止覆写和继承

```python
from typing import final

@final
class ImmutableConfig:
    """不能被继承"""
    ...

class SubConfig(ImmutableConfig):  # ❌ 类型检查器报错
    ...

class BaseService:
    @final
    def authenticate(self, token: str) -> bool:
        """子类不能覆写这个方法"""
        ...
```

## Self——方法返回当前类（Python 3.11+）

```python
from typing import Self

class QueryBuilder:
    def select(self, *columns: str) -> Self:
        ...
        return self

    def where(self, condition: str) -> Self:
        ...
        return self

    def order_by(self, column: str) -> Self:
        ...
        return self

# 子类也能正确推断
class PostgresBuilder(QueryBuilder):
    def for_update(self) -> Self:
        ...
        return self

# builder.for_update() 的返回类型是 PostgresBuilder，不是 QueryBuilder
```

`Self` 替代了之前需要 `TypeVar` bound 模式的写法，更简洁直接。

## 类型检查不是运行时验证

一个关键认知——Python 类型标注**不在运行时检查**：

```python
def add(a: int, b: int) -> int:
    return a + b

add("hello", "world")    # ✅ 运行时完全正常——"helloworld"
# 类型检查器（mypy/pyright）会在编码时报告错误
# 但 Python 解释器不管你写的什么类型
```

所以类型标注和运行时验证是两件事：

```python
# 运行时验证——用 pydantic / dataclass 的 __post_init__
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    age: int

    def __post_init__(self):
        if not isinstance(self.name, str):
            raise TypeError(f"name must be str, got {type(self.name)}")
        if not isinstance(self.age, int):
            raise TypeError(f"age must be int, got {type(self.age)}")
```

类型检查器保编译时正确，运行时验证保数据正确——两者互补。

## 实操——渐进式给一个老项目加类型

```python
# 第一步：加函数签名——最小的改动，最大的收益
def calculate(price: float, quantity: int) -> float:
    return price * quantity

# 第二步：dict 换成 TypedDict——不影响运行时
class OrderItem(TypedDict):
    product_id: str
    price: float
    quantity: int

def calculate_total(items: list[OrderItem]) -> float:
    return sum(it["price"] * it["quantity"] for it in items)

# 第三步：裸 Any 换成具体类型
def load_config(path: str = "config.json") -> dict[str, Any]:
    ...  # 先给个 Any，后续慢慢细化

# 三周后，你搞清楚返回值的结构了
class AppConfig(TypedDict):
    db: DatabaseConfig
    cache: CacheConfig

def load_config(path: str = "config.json") -> AppConfig:
    ...  # 返回类型从 dict[str, Any] 收紧到 AppConfig
```

类型检查不是 all-or-nothing。项目可以保持大部分代码无类型，只在关键的公共接口和数据结构上加标注。收益曲线最陡峭的部分——API 边界、配置结构、数据库模型——也是标注回报最高的地方。

## 总结

| 需求 | 方案 |
|------|------|
| 基本类型 | `str`, `int`, `float`, `bool` |
| 可选值 | `X \| None`（3.10+） |
| 容器 | `list[X]`, `dict[K, V]`（3.9+） |
| 多种类型 | `X \| Y`（3.10+） |
| dict 结构 | `TypedDict` |
| duck typing | `Protocol` |
| 泛型 | `TypeVar` |
| 字面量 | `Literal["a", "b"]` |
| 函数重载 | `@overload` |
| 禁止覆写 | `@final` / `@final` class |
| 返回当前类 | `Self`（3.11+） |

Python 的类型系统不是要取代动态特性——**是在动态特性的基础上，给你的 IDE 和未来的自己多一份可检索的文档**。一份写得好类型标注，很多时候比旁边的 docstring 更能说清楚代码的意图。
