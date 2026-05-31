# Python 闭包：函数为什么能“记住”外部变量

> 本文基于 Python 3.12。

很多人第一次接触闭包，是在装饰器、回调函数、工厂函数里。代码能跑，但心里总有个问号：**外层函数都执行完了，里面那个函数为什么还能访问外层变量？**

如果这个问题没想明白，闭包就会一直停留在“会用但不敢改”的阶段。理解闭包，本质上是在理解两件事：

1. Python 里的函数不是语法块，而是对象
2. 函数不只会执行代码，还会携带一部分定义时的环境

这篇文章就把这件事讲透。

## 先看一个最小例子

```python
def make_counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment

counter = make_counter()
print(counter())  # 1
print(counter())  # 2
print(counter())  # 3
```

乍看很反直觉：`make_counter()` 已经执行结束了，按常识它里面的局部变量 `count` 应该被销毁，但 `increment()` 每次调用仍然能读写它。

这就是闭包。**闭包不是“内部函数”本身，而是“函数 + 它捕获的外部变量环境”这个整体。**

## 为什么 Python 需要闭包

先别急着背定义，先想一个实际需求：你要给一批任务生成不同的告警函数。

```python
def make_alert(level):
    def alert(message):
        print(f"[{level}] {message}")
    return alert

info = make_alert("INFO")
error = make_alert("ERROR")

info("service started")
error("database unavailable")
```

如果没有闭包，你就只能：

- 每次调用时都把 `level` 再传一遍
- 或者把 `level` 存到全局变量里
- 或者定义一个类，专门保存状态

闭包的价值就在这里：**当你想生成一批“行为相同、配置不同”的函数时，闭包是最轻量的表达方式。**

它比全局变量安全，因为状态不会泄漏到外部；它比类更轻，因为你不需要为了一个小状态专门建类型。

## 理解闭包前，先理解函数是一等公民

在 Python 里，函数和整数、字符串一样，都是对象。可以赋值、传参、返回：

```python
def greet(name):
    return f"Hello, {name}"

say_hello = greet
print(say_hello("Python"))


def run(func, value):
    return func(value)

print(run(greet, "World"))


def choose(prefix):
    def formatter(name):
        return f"{prefix}: {name}"
    return formatter

fmt = choose("User")
print(fmt("Alice"))
```

闭包依赖的第一块地基，就是**函数可以被返回**。如果函数不能作为返回值，外层函数结束后，内部函数根本没有机会继续存在。

## 闭包到底“捕获”了什么

看这个例子：

```python
def make_multiplier(factor):
    def multiply(value):
        return value * factor
    return multiply

mul2 = make_multiplier(2)
mul5 = make_multiplier(5)

print(mul2(10))  # 20
print(mul5(10))  # 50
```

`multiply()` 没有自己的 `factor`，它访问的是外层 `make_multiplier()` 的局部变量。关键点在于：**Python 捕获的不是代码文本，而是变量绑定。**

也就是说，`mul2` 和 `mul5` 分别拿到了一份独立的外部环境：

```python
print(mul2.__closure__[0].cell_contents)  # 2
print(mul5.__closure__[0].cell_contents)  # 5
```

这里的 `__closure__` 会保存闭包捕获的变量单元。你平时开发几乎不需要直接操作它，但知道它存在很重要——它说明闭包不是魔法，而是 Python 解释器明确维护的一段状态。

## 闭包的形成条件

不是每个内部函数都算闭包。要形成闭包，通常要同时满足两个条件：

1. 有嵌套函数
2. 内部函数引用了外部函数作用域中的变量

例如：

```python
def outer():
    message = "hello"

    def inner():
        return message

    return inner
```

这里 `inner` 引用了 `message`，所以它是闭包。

但下面这个例子不是重点意义上的闭包：

```python
def outer():
    def inner():
        return "hello"

    return inner
```

虽然它也是返回内部函数，但 `inner` 没有使用外层局部变量，所以“函数记住环境”这件事并没有发生。

## LEGB：闭包为什么能找到那个变量

Python 查找变量遵循 LEGB 规则：

- `Local`：当前函数局部作用域
- `Enclosing`：外层嵌套函数作用域
- `Global`：模块全局作用域
- `Built-in`：内建作用域

闭包起作用，靠的就是中间这个 `Enclosing`。

```python
def outer():
    x = "outer"

    def inner():
        return x

    return inner
```

当 `inner()` 执行时：

1. 先找自己的局部变量，没有
2. 再找外层 `outer()` 的作用域，找到 `x`
3. 因为这个外层环境被闭包保留下来了，所以即使 `outer()` 早就返回，`x` 仍然可用

很多人第一次学闭包时，卡住的不是语法，而是这件事：**函数结束不等于其中所有局部变量一定立刻消失。只要还有对象引用着这些变量，它们就会继续活着。**

## 只读捕获 vs 可变状态

闭包最容易用顺手的场景是“读取配置”：

```python
def make_prefixer(prefix):
    def prefixer(text):
        return f"{prefix}{text}"
    return prefixer
```

但一旦你想在闭包里修改外部变量，就会碰到 `nonlocal`。

### 不加 `nonlocal` 会怎样

```python
def make_counter():
    count = 0

    def increment():
        count += 1
        return count

    return increment
```

这段代码会报错：

```python
UnboundLocalError: local variable 'count' referenced before assignment
```

原因不是 Python 笨，而是它看到了 `count += 1`，就认为 `count` 是 `increment()` 的局部变量。于是右边读取 `count` 时，发现这个局部变量还没初始化。

### `nonlocal` 的含义

```python
def make_counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment
```

`nonlocal` 的意思不是“去全局找”，而是：**这个变量不在当前局部作用域里创建，请去最近一层外部函数作用域里绑定它。**

它和 `global` 完全不是一回事：

- `global` 修改模块级变量
- `nonlocal` 修改外层函数变量

这两个关键字混淆，是 Python 作用域 bug 的高发区。

## 闭包最常见的实战价值

闭包的使用场景很多，但真正高频的其实就三类。

### 一类：函数工厂

这是闭包最经典也最自然的用途。

```python
def make_power(exponent):
    def power(base):
        return base ** exponent
    return power

square = make_power(2)
cube = make_power(3)

print(square(4))  # 16
print(cube(4))    # 64
```

这里 `square` 和 `cube` 的逻辑完全一样，区别只是各自闭合了不同的 `exponent`。

### 二类：带状态但不想上类

有些状态非常轻，专门写类会显得重。

```python
def make_running_average():
    total = 0
    count = 0

    def add(value):
        nonlocal total, count
        total += value
        count += 1
        return total / count

    return add

avg = make_running_average()
print(avg(10))  # 10.0
print(avg(20))  # 15.0
print(avg(30))  # 20.0
```

当状态只服务于一个小函数，并且外部不需要更多方法时，闭包通常比类更直接。

### 三类：装饰器的底层基础

如果你已经写过装饰器，其实你已经在使用闭包了。

```python
from functools import wraps


def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)

    return wrapper
```

这里 `wrapper` 能访问 `func`，就是因为它形成了闭包。

很多 Python 特性看起来各讲各的，实际上底层是连着的：**装饰器之所以成立，不是因为 `@` 有多神秘，而是因为闭包让“返回一个记住原函数的函数”成为可能。**

## 一个更贴近开发的实战场景：生成 SQL 查询函数

假设你在做一个很轻量的数据库访问层，不想每次都把表名硬编码在函数里重复写。

```python
def make_query_by_id(table_name):
    def query(record_id):
        sql = f"SELECT * FROM {table_name} WHERE id = %s"
        return sql, (record_id,)

    return query

query_user = make_query_by_id("users")
query_order = make_query_by_id("orders")

print(query_user(101))
print(query_order(202))
```

输出：

```python
('SELECT * FROM users WHERE id = %s', (101,))
('SELECT * FROM orders WHERE id = %s', (202,))
```

这个例子不复杂，但很能说明闭包的价值：

- 逻辑模板只有一份
- 配置参数 `table_name` 被固定下来
- 调用方拿到的是一个“已经配置好”的函数

为什么这比每次传 `table_name` 更好？因为它把“配置阶段”和“执行阶段”分开了。

- `make_query_by_id("users")` 是配置阶段
- `query_user(101)` 是执行阶段

这种拆分在 Web 框架、中间件、任务系统、装饰器里都非常常见。

## 闭包和类，到底怎么选

很多场景闭包和类都能做。比如计数器：

```python
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1
        return self.count
```

和闭包版本相比：

```python
def make_counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment
```

我的经验是这样分：

- **闭包适合**：状态很小、行为单一、只需要返回 1 个函数
- **类适合**：状态较多、需要多个方法、希望接口更显式

换句话说，闭包不是“比类高级”，而是“比类更轻”。一旦你发现自己想给闭包再挂 `reset()`、`peek()`、`dump()` 之类的方法，通常说明该上类了。

## 一个著名坑：循环里创建闭包

这是 Python 闭包最容易踩、也最容易在面试里被问到的坑。

```python
def create_multipliers():
    funcs = []
    for i in range(3):
        funcs.append(lambda x: x * i)
    return funcs

f0, f1, f2 = create_multipliers()
print(f0(10))
print(f1(10))
print(f2(10))
```

很多人以为输出会是：

```python
0
10
20
```

但实际是：

```python
20
20
20
```

### 为什么会这样

因为这些 lambda 没有在每次循环时“拍快照”保存 `i` 的值，它们捕获的是同一个变量绑定。等到真正调用时，循环早结束了，`i` 的最终值是 `2`，所以三个函数都用 `2`。

这说明 Python 闭包默认采用的是**延迟绑定**：调用时再去取变量当前值，而不是定义时立刻拷贝一份。

### 正确写法

最常见修复方式是把当前值变成默认参数：

```python
def create_multipliers():
    funcs = []
    for i in range(3):
        funcs.append(lambda x, i=i: x * i)
    return funcs
```

现在输出就是预期的：

```python
0
10
20
```

为什么默认参数能解决？因为默认参数在函数定义时求值，相当于在每一轮循环里把当时的 `i` 固定下来了。

如果你理解了这个坑，基本就真正理解了“闭包捕获变量绑定，而不是值拷贝”这件事。

## 闭包会带来什么代价

闭包很方便，但也不是零成本。

### 1. 隐式状态会降低可读性

闭包最大的优点是轻，最大的缺点也是轻——状态藏在函数环境里，不像类那样显式挂在 `self` 上。

如果闭包里捕获了很多变量，读代码的人会很难快速看出这个函数到底依赖哪些状态。

### 2. 生命周期会被拉长

只要返回的内部函数还活着，被捕获的外部变量就还活着。这有时是你想要的，有时也可能让一些对象比预期存活更久。

比如闭包里如果意外捕获了一个大对象、数据库连接、缓存句柄，就可能带来额外内存占用或资源生命周期混乱。

### 3. 调试时不如显式对象直观

类实例可以直接 `obj.__dict__` 看状态；闭包虽然也能通过 `__closure__` 看，但明显没那么直观，也不适合作为日常调试手段。

所以闭包适合“小而稳”的状态，不适合复杂对象模型。

## 怎么判断一段代码是不是闭包友好

一个很实用的判断标准：

如果你要表达的是“先配置一次，再反复调用”，闭包通常很合适。

比如：

- 固定日志前缀
- 固定重试次数
- 固定数据源或表名
- 固定权限检查规则
- 固定格式化模板

这类场景都有一个共同点：**有一部分上下文在创建函数时就已经确定，之后只是在不同输入上重复执行。**

这正是闭包最擅长的建模方式。

## 总结

闭包听起来像高级概念，其实核心非常朴素：**函数返回后，内部函数依然持有外层作用域中的变量，所以它“记住了”定义时的环境。**

可以把它记成一句话：

> 闭包 = 函数 + 被它捕获的外部状态

真正需要带走的不是术语，而是三个判断：

1. 当你想生成“配置不同、行为相同”的函数时，优先想到闭包
2. 当你需要在内部函数里修改外部变量时，用 `nonlocal`
3. 当闭包状态开始变复杂、需要多个操作入口时，别硬撑，改成类

理解了闭包，你再看装饰器、回调、函数工厂，会发现它们不是零散技巧，而是同一套机制在不同场景下的展开。 
