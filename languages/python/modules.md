# Python 模块系统：每一个 import 背后发生了什么

> 本文基于 Python 3.12。

Python 的 `import` 看起来简单——写 `import requests` 就把整个库拉进来了。但背后 `sys.path` 怎么搜索、`__init__.py` 为什么存在、相对导入为什么偶尔爆炸——理解这些，你不会再被 `ModuleNotFoundError` 困住。

## 一个 import 的一生

当你写下 `import numpy` 时，Python 按顺序做三件事：

1. **搜索** — 在 `sys.path` 中查找名为 `numpy` 的模块或包
2. **加载** — 找到后创建 module 对象，执行模块中的代码
3. **缓存** — 把 module 对象存入 `sys.modules`

```python
import sys
print(sys.path[:3])
# ['', '/usr/lib/python312.zip', '/usr/lib/python3.12']
```

第一个元素是空字符串——代表当前目录。这意味着**如果你在当前目录下放了一个 `json.py`，`import json` 会加载你的文件而不是标准库**。这是 Python 最常见也最隐蔽的坑之一。

`sys.modules` 是已加载模块的全局缓存。同一个模块 import 两次不会重复执行：

```python
import json
print(id(json))

import json           # 第二次，直接从缓存返回
print(id(json))       # 相同——模块是单例
```

## `__name__` 和 `if __name__ == '__main__'`

这是 Python 里被误解最多的双下划线。当文件直接运行 `python foo.py` 时，`__name__` 是 `'__main__'`。当文件被 import 时，`__name__` 是这个模块的实际名称。

```python
# utils.py
def helper():
    return "useful"

print(f"utils.py: __name__ = {__name__}")

if __name__ == "__main__":
    print("直接运行 utils 的测试代码")
```

```bash
$ python utils.py
utils.py: __name__ = __main__
直接运行 utils 的测试代码

$ python -c "import utils"
utils.py: __name__ = utils
```

`if __name__ == '__main__'` 模式的价值：同一个文件可以同时被 import 和被直接运行——import 时不执行测试代码，直接运行时执行。

## `__init__.py` 的三个作用

十年前 `__init__.py` 是包的标志——没有它 Python 不认为这是包。Python 3.3 引入了隐式命名空间包，`__init__.py` 不再是硬性要求。

**作用 1：初始化包**

```python
# mylib/__init__.py
print("mylib 被导入")

from .core import Engine     # 把子模块提升到包级别
from .utils import setup
```

提升后使用者可以直接 `from mylib import Engine` 而非 `from mylib.core import Engine`——内部结构对外透明。

**作用 2：定义 `__all__`**

```python
# mylib/__init__.py
__all__ = ["Engine", "setup", "Config"]
```

`from mylib import *` 只会导入 `__all__` 里列出的名字。没定义 `__all__` 的话，`import *` 导入所有不以下划线开头的公共名称。

**作用 3：控制包的延迟加载**

```python
# mylib/__init__.py
def __getattr__(name):
    if name == "heavy_module":
        import mylib.heavy_module as mod
        return mod
    raise AttributeError(name)
```

`heavy_module` 只在第一次访问 `mylib.heavy_module` 时才加载——不是 import 时就加载。大型库的启动时间从 300ms 降到 30ms 的核心技巧。

## 绝对导入 vs 相对导入

这一节值一个小时的 debug 时间。

**绝对导入** — 从包的根路径开始：

```python
# mylib/sub/api.py
from mylib.core import Engine      # ✅ 简洁
from mylib.utils.logger import log  # ✅ 明确
```

**相对导入** — 从当前文件位置开始：

```python
# mylib/sub/api.py
from . import models               # ✅ 同级目录
from ..core import Engine           # ✅ 上一级
from ..utils.logger import log      # ✅ 上一级的 utils
```

相对导入只在包内部有效——直接 `python api.py` 运行包含相对导入的文件报 `ImportError: attempted relative import with no known parent package`。

面试和 PR Review 中最常见的 Python 导入问题：用相对导入的脚本不能在命令行直接运行。理解 `__name__` 和 `__package__` 立刻破解——当文件作为脚本运行时，`__package__` 为 None，相对导入无处可'相对'。

## 循环导入

A 导入 B，B 导入 A——Python 能处理但不代表你该这样做：

```python
# a.py
import b
def func_a():
    return b.func_b()

# b.py
import a
def func_b():
    return a.func_a()
```

Python 处理循环导入的策略是「部分加载」——当 B 尝试 import A 时，A 已经被加到 `sys.modules` 但可能还没完全初始化。这意味着 `a.func_a` 可能还不存在。

三种解法：

**1. 延迟导入** — 把 import 放在函数内部：

```python
def func_a():
    import b        # 延迟到运行时
    return b.func_b()
```

**2. 重构** — 抽出第三方公共模块 C，A 和 B 都只依赖 C

**3. 换个设计** — 循环导入通常是抽象边界画错了的信号。如果 A 需要 B、B 需要 A，它们可能应该属于同一个模块

## `__init__.py` 不再必需的影响

Python 3.3 引入的隐式命名空间包允许跨多个目录的包合并命名空间。这对大型 monorepo 极有用：

```
repo/
├── team_a/
│   └── myapp/
│       ├── pay/
│       │   └── __init__.py
│       │   └── payment.py
│       └── core/
│           └── __init__.py
│           └── engine.py
├── team_b/
│   └── myapp/
│       └── notif/
│           └── __init__.py
│           └── email.py
```

把 `repo/team_a` 和 `repo/team_b` 都加到 `sys.path`，`import myapp.pay` 和 `import myapp.notif` 都能工作——两个团队独立维护同一个命名空间的不同子包。

命名空间包不是所有场景都适用。常规项目中仍保留轻量 `__init__.py`（哪怕只是空文件）是推荐的——显式比隐式好。

> 适合有 Python 基础，想在项目中组织大型代码库的读者。
