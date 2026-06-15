# Python functools：标准库里最被低估的模块

> 本文基于 Python 3.12。

## 你已经用了 functools，只是不知道

如果你写过装饰器，你一定写过这个：

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)   # ← 这就是 functools
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

`@wraps` 可能是 Python 生态中使用频率和知晓率反差最大的函数——天天用，但很少有人知道它来自 `functools`，更少有人翻过 `functools` 里还有什么。这篇文章把模块里最值得知道的五个函数一一拆开。

## 1. `partial` — 把多参数函数变成少参数函数

```python
from functools import partial

# 原始函数——三个参数
def send_notification(webhook_url, title, content):
    print(f"[{title}] → {webhook_url}: {content}")

# 飞书 webhook 是固定的——每次都要传很烦
feishu_notify = partial(send_notification,
    "https://open.feishu.cn/open-apis/bot/v2/hook/xxx")

# 现在只需要两个参数了
feishu_notify("告警", "CPU 超过 90%")
feishu_notify("通知", "新版本已部署")
```

### 不只是省参数——是固化接口

```python
import json

# 标准库大量用 partial 来固化函数签名
json_dumps = partial(json.dumps, ensure_ascii=False, indent=2)

data = {"name": "张三", "city": "北京"}
print(json_dumps(data))
# {
#   "name": "张三",
#   "city": "北京"
# }
```

没有 `partial` 的话，你只能每次写 `json.dumps(data, ensure_ascii=False, indent=2)` 或者包一层 lambda。`partial` 比 lambda 更快（C 实现）而且有 `__name__` 和 `__doc__` 属性——调试时能看到函数名，不是 `<lambda>`。

### 和 pipeline 配合——每个步骤只暴露需要的参数

```python
from functools import partial

class Pipeline:
    def __init__(self):
        self.steps = []

    def add_step(self, func, *args, **kwargs):
        self.steps.append(partial(func, *args, **kwargs))

    def run(self, data):
        for step in self.steps:
            data = step(data)
        return data

# 构建 pipeline
pipe = Pipeline()
pipe.add_step(clean_text, remove_html=True, max_length=500)
pipe.add_step(extract_keywords, top_k=10)

result = pipe.run(raw_html)
```

每个步骤被 `partial` 锁住了参数——pipeline 执行时只传一个 `data` 就行。这是轻量级的依赖注入。

## 2. `lru_cache` — 用一行代码消除重复计算

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(100))  # 354224848179261915075——瞬间
print(fibonacci.cache_info())
# CacheInfo(hits=98, misses=101, maxsize=128, currsize=101)
```

不加装饰器——`fibonacci(40)` 要算约 3 亿次递归。加了之后——每个 n 只算一次，存进字典，下次直接用。

### 不只是斐波那契——任何纯函数都能提速

```python
import sqlite3
from functools import lru_cache

@lru_cache(maxsize=256)
def get_user(user_id):
    """从数据库查用户——相同 user_id 在 256 个缓存空间内只查一次"""
    conn = sqlite3.connect("users.db")
    cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()

# 同一请求中多次调用 get_user(42) → 只查一次数据库
```

### `maxsize` 的选择

| maxsize | 说明 |
|---------|------|
| `None` | 无限缓存——但内存可能无限增长 |
| `128` | 默认值——足够大部分场景 |
| `1024` | 用于热点数据多的场景 |
| `1` | 只缓存上一次的结果 |

### `lru_cache` 的陷阱——可变参数和实例方法

```python
# ❌ 列表不能哈希——lru_cache 要求所有参数可哈希
@lru_cache
def bad_cache(items):   # items 是 list → TypeError
    return sum(items)

# ✅ 用 tuple
@lru_cache
def good_cache(items: tuple):
    return sum(items)

# ❌ 实例方法——缓存包含 self，可能导致内存泄漏
class Calculator:
    @lru_cache
    def calculate(self, x, y):   # self 也被哈希了
        return x * y

# ✅ 用 cached_property（下一节）或把缓存放在类级别
```

### `cache` — Python 3.9+ 的简化版

```python
from functools import cache

@cache   # 等价于 @lru_cache(maxsize=None)
def expensive(n):
    ...
```

## 3. `cached_property` — 懒计算一次，之后直接用

```python
from functools import cached_property

class Report:
    def __init__(self, data):
        self.data = data

    @cached_property
    def summary(self):
        """第一次访问时计算，之后直接从 __dict__ 拿"""
        print("计算中...")
        return {
            "total": len(self.data),
            "avg": sum(self.data) / len(self.data),
            "max": max(self.data),
            "min": min(self.data),
        }

r = Report([1, 2, 3, 4, 5])
print(r.summary)  # 计算中... → {'total': 5, 'avg': 3.0, ...}
print(r.summary)  # 不再计算，直接从 __dict__ 读
```

和 `@property` 的区别：

```python
class Demo:
    @property
    def always_run(self):        # 每次访问都执行
        print("property 每次计算")
        return sum(large_computation())

    @cached_property
    def run_once(self):          # 只执行一次
        print("cached_property 只算一次")
        return sum(large_computation())
```

**`cached_property` 适合**：计算昂贵但结果不变（数据库连接、配置文件解析、数据聚合）。**`property` 适合**：每次返回的值可能不同（当前时间、实时状态）。

## 4. `singledispatch` — 按第一个参数的类型分发

```python
from functools import singledispatch

@singledispatch
def format_output(data):
    """默认处理"""
    return str(data)

@format_output.register
def _(data: dict):
    """处理 dict"""
    return json.dumps(data, ensure_ascii=False, indent=2)

@format_output.register
def _(data: list):
    """处理 list"""
    return "\n".join(f"• {item}" for item in data)

@format_output.register
def _(data: int):
    """处理 int——带单位"""
    if data > 1_000_000:
        return f"{data / 1_000_000:.1f}M"
    elif data > 1_000:
        return f"{data / 1_000:.1f}K"
    return str(data)

# 同一个函数名，不同类型不同行为
print(format_output({"name": "张三", "age": 30}))
# → {"name": "张三", "age": 30}

print(format_output(["苹果", "香蕉", "橘子"]))
# → • 苹果
#   • 香蕉
#   • 橘子

print(format_output(1500000))
# → 1.5M
```

和 `if isinstance()` 的区别：**可扩展**——你可以在另一个模块里注册新类型，原代码不用改。

```python
# 在另一个文件里扩展——format_output 的作者不需要知道 datetime
from datetime import datetime

@format_output.register
def _(data: datetime):
    return data.strftime("%Y-%m-%d %H:%M")
```

## 5. `reduce` — 把列表变成单个值

```python
from functools import reduce

# 求和——和 sum() 一样，但演示 reduce 的语义
reduce(lambda acc, x: acc + x, [1, 2, 3, 4], 0)
# 执行过程: ((0 + 1) + 2) + 3) + 4 = 10

# 实际用法: 深度合并字典
def deep_merge(d1, d2):
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
            d1[k] = deep_merge(d1[k], v)
        else:
            d1[k] = v
    return d1

configs = [
    {"db": {"host": "localhost", "port": 5432}},
    {"db": {"port": 5433}, "cache": {"ttl": 300}},
    {"api": {"key": "sk-123"}},
]

final = reduce(deep_merge, configs, {})
# → {'db': {'host': 'localhost', 'port': 5433},  ← port 被后一个覆盖
#    'cache': {'ttl': 300},
#    'api': {'key': 'sk-123'}}
```

### 什么时候用 reduce，什么时候不用

| 场景 | 用 reduce | 不用 |
|------|----------|------|
| 列表求和 | ❌ `sum()` | ✅ |
| 深度合并 | ✅ | `for` 循环要好几个临时变量 |
| 组合函数 | ✅ `reduce(lambda f, g: lambda x: f(g(x)), funcs)` | ❌ |
| 列表拼接 | ❌ `''.join()` | ✅ |

一条原则：**如果 Python 有内置函数（sum、any、all、join），用它。如果没有，reduce 让循环的意图更清晰。**

## 小结

functools 的五个函数解决五种不同的问题：

| 函数 | 解决什么问题 | 一句话 |
|------|------------|--------|
| `partial` | 函数参数太多、锁定了用 | 把 f(a, b, c) 变成 f'(b, c) |
| `lru_cache` | 重复计算 | 相同输入不重复执行 |
| `cached_property` | 实例属性计算贵 | 首次算，之后从 `__dict__` 取 |
| `singledispatch` | 不同类型不同处理 | 函数重载——不写 if isinstance |
| `reduce` | 把列表聚合为单值 | 当 sum/join 不够用时 |

这些不是那种"学了就能写出更好的代码"的知识点——是那种**知道就省时间、不知道也一样过**的工具。但每次你正要写第三遍 `functools` 相关的轮子时，回想一下这篇文章——标准库里大概率已经有了。
