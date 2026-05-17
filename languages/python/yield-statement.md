# yield 与生成器：惰性求值的艺术

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

## 为什么需要 yield

假设你要处理一个百万行的日志文件，把所有行读进内存再处理会直接爆掉：

```python
# 不推荐：一次性加载
with open("huge.log") as f:
    lines = f.readlines()  # 百万行全进内存
    for line in lines:
        process(line)
```

`yield` 让你按需产出数据——用多少拿多少，内存只占一行：

```python
def read_logs(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

for line in read_logs("huge.log"):
    process(line)  # 内存中始终只有当前这一行
```

核心思想：**惰性求值**——不事先算完所有结果，调用方要一个才给一个。

## 生成器基础

任何包含 `yield` 的函数都变成**生成器函数**，调用它返回一个**生成器迭代器**（Python 2.2+，PEP 255）：

```python
def count_up_to(n):
    i = 0
    while i < n:
        yield i
        i += 1

g = count_up_to(3)
print(type(g))  # <class 'generator'>

print(next(g))  # 0
print(next(g))  # 1
print(next(g))  # 2
print(next(g))  # StopIteration
```

每次 `next()` 让函数执行到下一个 `yield`，停在那里，状态保留。这就解释了为什么生成器可以用在 `for` 循环里——`for` 在底层就是反复调用 `next()`。

### 生成器是单向迭代器

只能前进，不能后退，也不能重复遍历：

```python
g = (x * 2 for x in range(3))
list(g)  # [0, 2, 4]
list(g)  # [] — 已经耗尽了
```

需要多次遍历就每次重新创建，或者用 `list()` 把结果存下来。

## 生成器表达式

比函数更简洁的写法（Python 2.4+，PEP 289）：

```python
# 生成器表达式（惰性）
squares = (x * x for x in range(10))

# 加过滤条件
odd_squares = (x * x for x in range(10) if x % 2 == 1)

# 用 sum/min/max 等直接消费
sum(x * x for x in range(10))  # 285 — 不会创建中间列表
```

和列表推导式的区别就是一对方括号和一个内存：

```python
[x * x for x in range(1000000)]  # 立即分配 100 万个元素的列表
(x * x for x in range(1000000))  # 几乎不占内存，按需计算
```

规则：**消费一次就用生成器，消费多次就用列表**。

## yield from：委托给子生成器

（Python 3.3+，PEP 380）

当你的生成器需要「转发」到另一个生成器时：

```python
# 不用 yield from — 啰嗦
def flatten(nested):
    for sublist in nested:
        for item in sublist:
            yield item

# 用 yield from — 一行搞定
def flatten(nested):
    for sublist in nested:
        yield from sublist

data = [[1, 2], [3, 4], [5]]
list(flatten(data))  # [1, 2, 3, 4, 5]
```

`yield from` 不仅是语法糖——它还自动处理 `send()`、`throw()`、`close()` 的转发，以及 `return` 值的传递。

### 子生成器的返回值

```python
def inner():
    yield 1
    yield 2
    return "done"

def outer():
    result = yield from inner()
    yield f"inner returned: {result}"

list(outer())  # [1, 2, 'inner returned: done']
```

## 生成器的双向通信

生成器不只是往外产出数据——还可以往里面发送数据。

### send()：向生成器注入值

```python
def accumulator():
    total = 0
    while True:
        x = yield total
        if x is None:
            break
        total += x

acc = accumulator()
next(acc)       # 必须先推进到第一个 yield，输出 0
acc.send(10)    # 注入 10，输出 10
acc.send(20)    # 注入 20，输出 30
acc.send(None)  # 触发 break，StopIteration
```

注意 `x = yield total` 的执行顺序：
1. 先产出 `total` 的值
2. 外部 `send()` 传入的值赋给 `x`
3. 继续执行到下一个 `yield`

首次调用不能用 `send()`，必须先用 `next()` 或 `send(None)` 推进到第一个 `yield`。

### throw()：向生成器抛出异常

```python
def tolerant():
    try:
        yield 1
    except ValueError:
        yield "caught"
    yield 2

g = tolerant()
next(g)      # 1
g.throw(ValueError)  # "caught" — 异常在 yield 处抛出
next(g)      # 2
```

### close()：终止生成器

```python
g = count_up_to(100)
next(g)  # 0
g.close()
next(g)  # StopIteration
```

`close()` 在 `yield` 处抛出 `GeneratorExit`。生成器可以捕获 `GeneratorExit` 来做清理，但不能忽略它——如果 try/except 后继续 yield，运行时会抛出 `RuntimeError`。

## 实战场景

### 分块读取大文件

```python
def read_in_chunks(fileobj, chunk_size=8192):
    """每次 yield 一个数据块，而不是整个文件"""
    while True:
        chunk = fileobj.read(chunk_size)
        if not chunk:
            break
        yield chunk

with open("large.bin", "rb") as f:
    for chunk in read_in_chunks(f):
        process(chunk)
```

### 无限序列

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

from itertools import islice

# 取前 10 个斐波那契数
list(islice(fibonacci(), 10))
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

谁说无限循环不能用在 for 里？`islice` 配合生成器就是一个完美的按需截取。

### 分页 API 请求

```python
import requests

def fetch_pages(base_url, per_page=100):
    page = 1
    while True:
        resp = requests.get(f"{base_url}?page={page}&per_page={per_page}")
        items = resp.json()["data"]
        if not items:
            break
        yield from items
        page += 1

# 调用方完全不用关心分页逻辑
for user in fetch_pages("https://api.example.com/users"):
    print(user["name"])
```

### 工作流管道

```python
def read_input(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

def parse(lines):
    for line in lines:
        if line:
            yield line.split(",")

def filter_valid(rows):
    for row in rows:
        if len(row) == 3:
            yield {"name": row[0], "age": int(row[1]), "city": row[2]}

# 管道组合——仍然惰性，一行数据流经整条链
pipeline = filter_valid(parse(read_input("users.csv")))
for user in pipeline:
    print(user)
```

每步都是生成器，数据像流水线一样流过来，中间没有任何不必要的列表。

## 生成器 vs 其他方式

| 方式 | 内存 | 启动速度 | 适用场景 |
|------|------|----------|----------|
| 生成器 | O(1) | 即时 | 大数据流、无限序列、管道 |
| 列表 | O(n) | 要先算完 | 小数据集、需随机访问、多次遍历 |
| 迭代器类 | O(1) | 即时 | 复杂状态需要封装时 |

大部分场景生成器就够了。需要 `send()`/`throw()` 的复杂双向通信或者需要 `__iter__` 和 `__next__` 分开控制时再写自定义迭代器类。

## 常见坑

### 生成器只能用一次

```python
g = (x for x in range(5))
sum(g)  # 10
sum(g)  # 0 — 不是报错，而是静默失败
```

小心这种很难察觉的 bug。要么每次新建，要么先转 `list()`。

### yield 在 try/finally 中

```python
def leaky():
    try:
        yield "working"
    finally:
        print("cleanup")

for x in leaky():
    break  # break 时 finally 会执行吗？

# 输出: cleanup — 会执行！
```

好消息：垃圾回收未被引用的生成器时会自动触发 `close()`，进而执行 `finally`。但不能 100% 依赖 GC 时机——显式用完或用 `with` 包裹更安全。

### 不要重用耗尽的生成器

```python
lines = (line.strip() for line in open("data.txt"))
headers = next(lines)  # 消费了第一行
for line in lines:      # 处理剩余行 — OK
    process(line)
# 但如果前面不小心 list(lines) 了，这里 for 就什么都没了
```

## 版本速查

| 特性 | 最低版本 |
|------|----------|
| 生成器函数（`yield`） | 2.2 (PEP 255) |
| 生成器表达式 | 2.4 (PEP 289) |
| `yield from` | 3.3 (PEP 380) |
| `send()` / `throw()` / `close()` | 2.5 (PEP 342) |
| 生成器作为协程（已废弃） | 3.5 起不推荐 |

## 要点

1. **生成器 = 惰性序列**——用多少算多少，省内存又不卡
2. **消费一次就没了**——需要多次用就先 `list()`
3. **`yield from` > 手写 for 循环**——更短、更正确、更快
4. **管道用生成器串联**——数据像流水线一样流过，零中间列表
5. **`send()` 能不进则不进**——99% 的场景用不到双向通信
