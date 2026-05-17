# with 语句：上下文管理器的正确打开方式

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

## 为什么需要 with

操作外部资源（文件、网络连接、锁）时，一个经典问题是：**用完必须释放，但中间可能抛异常**。

不用 with 时，你得这样写：

```python
f = open("data.txt", "r")
try:
    content = f.read()
finally:
    f.close()
```

三行业务逻辑，五行管理代码。而且 `close()` 本身也可能失败，写出健壮版本会更臃肿。

with 语句把「获取 → 使用 → 释放」这个模式固化为语法：

```python
with open("data.txt", "r") as f:
    content = f.read()
```

进入 `with` 块时获取资源，退出时自动释放——无论是否抛出异常。

## 上下文管理器协议

任何实现了 `__enter__` 和 `__exit__` 的对象都可以用在 with 语句中。

```python
class ManagedFile:
    def __init__(self, path, mode):
        self.path = path
        self.mode = mode

    def __enter__(self):
        self.file = open(self.path, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        # 返回 False 会让异常继续传播
        # 返回 True 会吞掉异常（慎用）
        return False

with ManagedFile("data.txt", "r") as f:
    print(f.read())
```

`__exit__` 的三个参数对应 `sys.exc_info()` 的返回值。正常退出时三者都是 `None`。如果 `__exit__` 返回 `True`，异常会被抑制——除非你很清楚自己在做什么，否则不要吞异常。

### 用 contextlib 简化

`contextlib.contextmanager` 装饰器把生成器函数转换为上下文管理器（Python 2.5+）：

```python
from contextlib import contextmanager

@contextmanager
def managed_file(path, mode):
    f = open(path, mode)
    try:
        yield f
    finally:
        f.close()

with managed_file("data.txt", "r") as f:
    print(f.read())
```

`yield` 之前的代码在 `__enter__` 中执行，之后的代码在 `__exit__` 中执行。**记住要用 try/finally**——yield 期间可能抛异常，不用 finally 会导致资源泄漏。

## 日常场景

### 文件操作

```python
# 读文件
with open("input.txt") as f:
    for line in f:
        print(line.strip())

# 写文件
with open("output.txt", "w") as f:
    f.write("hello\n")
```

### 多个上下文管理器

同时打开多个资源，用逗号分隔（Python 2.7+ / 3.1+）：

```python
with open("a.txt") as src, open("b.txt", "w") as dst:
    dst.write(src.read())
```

长列表可以用括号换行（Python 3.10+）：

```python
with (
    open("config.yaml") as config,
    open("template.jinja") as template,
    open("output.html", "w") as output,
):
    render(template.read(), config.read(), output)
```

### 锁

```python
import threading

lock = threading.Lock()

# 自动获取和释放锁
with lock:
    # 临界区代码
    do_something()
```

### 数据库事务

```python
import sqlite3

conn = sqlite3.connect("app.db")
with conn:
    # __exit__ 中自动 commit，异常时自动 rollback
    conn.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
```

### 临时目录/文件

```python
from tempfile import TemporaryDirectory, NamedTemporaryFile

with TemporaryDirectory() as tmpdir:
    # 离开 with 块后目录及内容自动删除
    ...

with NamedTemporaryFile(mode="w", suffix=".txt", delete=True) as tmp:
    tmp.write("hello")
    tmp.flush()
    process(tmp.name)
```

### 临时修改状态后自动恢复

一个特别实用的模式，用于测试或临时切换配置：

```python
import os
from contextlib import contextmanager

@contextmanager
def set_env(**kwargs):
    """临时设置环境变量，退出时自动恢复"""
    old = {k: os.environ.get(k) for k in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

with set_env(DEBUG="true", LOG_LEVEL="debug"):
    assert os.environ["DEBUG"] == "true"
# 这里 DEBUG 已经恢复
```

## contextlib 工具箱

### ExitStack：动态管理多个上下文

当你不知道运行时需要多少个上下文管理器时（Python 3.3+）：

```python
from contextlib import ExitStack

files_to_process = ["a.txt", "b.txt", "c.txt"]

with ExitStack() as stack:
    handles = []
    for name in files_to_process:
        # 逐个注册，ExitStack 保证所有资源都会被清理
        h = stack.enter_context(open(name))
        handles.append(h)

    # 所有文件都在这里打开
    for h in handles:
        process(h.read())
```

`ExitStack` 用栈管理上下文，出问题时按注册的逆序释放——后打开的先关，避免依赖问题。

### suppress：优雅地忽略特定异常

```python
from contextlib import suppress

# 取代 try/except pass
with suppress(FileNotFoundError):
    os.remove("/tmp/maybe_exists.txt")
```

比 `try/except pass` 更可读，而且明确表达了你只想忽略这个特定异常。

### redirect_stdout / redirect_stderr

捕获标准输出（Python 3.4+）：

```python
import io
from contextlib import redirect_stdout

f = io.StringIO()
with redirect_stdout(f):
    print("这条不会出现在终端")

assert f.getvalue() == "这条不会出现在终端\n"
```

### chdir：临时切换工作目录

```python
from contextlib import chdir  # Python 3.11+

with chdir("/tmp"):
    # 在这里工作目录是 /tmp
    ...
# 已自动恢复
```

### AbstractContextManager

如果想基于类和 `contextmanager` 结合，继承 `AbstractContextManager`（Python 3.6+）：

```python
from contextlib import AbstractContextManager

class Resource(AbstractContextManager):
    def __exit__(self, *args):
        self.close()
        return None
```

## async with：异步上下文管理器

（Python 3.5+，对应 PEP 492）

异步上下文管理器实现 `__aenter__` 和 `__aexit__`（返回 awaitable）：

```python
import asyncio

class AsyncConnection:
    async def __aenter__(self):
        print("打开连接...")
        await asyncio.sleep(0.1)  # 模拟 I/O
        return self

    async def __aexit__(self, *args):
        print("关闭连接...")
        await asyncio.sleep(0.05)

    async def query(self, sql):
        await asyncio.sleep(0.1)
        return f"结果: {sql}"

async def main():
    async with AsyncConnection() as conn:
        result = await conn.query("SELECT 1")
        print(result)
    # 退出 async with 时自动 await __aexit__

asyncio.run(main())
```

异步版本的 `ExitStack`（Python 3.7+）：

```python
from contextlib import AsyncExitStack

async def open_resources(urls):
    stack = AsyncExitStack()
    async with stack:
        sessions = []
        for url in urls:
            session = await stack.enter_async_context(create_session(url))
            sessions.append(session)
        # 使用所有会话...
```

`asynccontextmanager` 装饰器：

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_session(url):
    session = await create_session(url)
    try:
        yield session
    finally:
        await session.close()
```

## 自定义上下文管理器：有校验的临时文件

一个综合实战——创建一个带自动校验的临时文件管理器：

```python
import hashlib
import tempfile
from pathlib import Path

class VerifiedTempFile:
    """写入完成后自动校验 SHA-256"""

    def __init__(self, suffix=".txt"):
        self.tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)
        self.path = Path(self.tmp.name)

    def __enter__(self):
        return self.tmp

    def __exit__(self, *args):
        self.tmp.close()
        sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        print(f"SHA-256: {sha256}")
        self.path.unlink()  # 校验完再删
        return False

with VerifiedTempFile() as f:
    f.write(b"Hello, Python!")  # 退出时自动输出校验和并清理
```

## 版本速查

| 特性 | 最低版本 |
|------|----------|
| `with` 语句 | 2.5 (PEP 343) |
| 多上下文管理器（逗号） | 2.7 / 3.1 |
| `contextlib.contextmanager` | 2.5 |
| `contextlib.ExitStack` | 3.3 |
| `contextlib.redirect_stdout` | 3.4 |
| `async with` | 3.5 (PEP 492) |
| `contextlib.AbstractContextManager` | 3.6 |
| `contextlib.AsyncExitStack` | 3.7 |
| `contextlib.asynccontextmanager` | 3.7 |
| 括号化多行上下文 | 3.10 |
| `contextlib.chdir` | 3.11 |

## 要点

1. **资源管理、锁、状态恢复**——有「获取/释放」模式的地方就该用 with
2. **不要吞异常**，除非有明确理由
3. `ExitStack` 替代手写的动态资源管理，按逆序清理
4. `@contextmanager` 写简单管理器很顺手，但别忘了 try/finally
5. 异步资源用 `async with` + `AsyncExitStack`
