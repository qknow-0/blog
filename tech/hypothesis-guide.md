# Hypothesis：让测试替你找 bug

假设你写了一个 `sort` 函数。传统测试怎么写？

```python
def test_sort():
    assert sort([3, 1, 2]) == [1, 2, 3]
    assert sort([]) == []
    assert sort([1]) == [1]
```

三个 case，测了三个你手工想出来的输入。问题是——**你怎么知道这三个 case 够**？sort 的输入空间是「任意长度的任意整数列表」，三个 case 连冰山一角都算不上。如果有人在 sort 里不小心写了 `if len(lst) == 42: crash()`，你的测试永远发现不了。

Hypothesis 的方案是：你描述**属性**，它负责生成输入。

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_idempotent(lst):
    assert sort(sort(lst)) == sort(lst)

@given(st.lists(st.integers()))
def test_sort_preserves_elements(lst):
    assert sorted(sort(lst)) == sorted(lst)

@given(st.lists(st.integers()))
def test_sort_preserves_length(lst):
    assert len(sort(lst)) == len(lst)
```

三条属性定义了 sort 的正确性：排序两次结果不变、元素集合不动、长度不变。Hypothesis 会生成数百个随机列表——空列表、单元素、全相同、极值、已有序列、倒序——去验证。它会在输入空间里挖出你完全想不到的 corner case。

## Shrinking：最值钱的能力

Hypothesis 的杀手特性不是随机生成，是**缩小**。测试失败时，它不会把那个随机输入丢给你就完事了——它会自动把输入缩小到**能复现失败的最小形式**。

举个例子。写了一个有 bug 的解析器，hypothesis 生成了一个 200 字符的输入触发了 bug。你拿到的错误报告不会是那个 200 字符的随机串，而是：

```
Falsifying example: test_parser(
    text='<a></b>',
)
```

它把 200 字符缩减到了 8 个字符。这让你一眼就能看出问题：标签不匹配。

缩小过程是全自动的：一旦发现失败的输入，hypothesis 就开始「能不能更简单一点？」——删掉一些字符、减少列表长度、缩小数值、简化嵌套结构。每简化一次就重新跑一次，直到找到「删掉任何一个元素 bug 就消失了」的最小反例。

没有 shrinking，属性测试的体验是「某个随机输入挂了，但你看不懂」。有了 shrinking，「哦，这对不匹配的标签挂了」。差距就是这么大。

## Strategies：描述你的输入

`st.integers()` 生成任意整数，`st.text()` 生成任意字符串。更多常用 strategies：

```python
# 数值
st.integers(min_value=0, max_value=100)   # 0-100 的整数
st.floats(min_value=0, exclude_min=True)  # 正浮点数
st.decimals()                             # 高精度 decimal

# 文本（默认生成各种 Unicode，专测编码 bug）
st.text(min_size=1, max_size=50)
st.from_regex(r"^\d{4}-\d{2}-\d{2}$")    # 匹配正则的字符串
st.emails()                               # 看起来像邮箱的字符串

# 容器
st.lists(st.integers(), min_size=1, max_size=10)
st.dictionaries(st.text(), st.integers())
st.tuples(st.text(), st.integers())

# 组合
st.one_of(st.integers(), st.text())       # 二选一
st.sampled_from(["GET", "POST", "PUT"])   # 枚举值
st.builds(MyClass, name=st.text(), age=st.integers())  # 构造对象
```

strategy 可以无限组合。一个用户对象的 strategy：

```python
user_strategy = st.builds(
    User,
    name=st.text(min_size=1, max_size=30),
    email=st.emails(),
    age=st.integers(min_value=0, max_value=150),
    role=st.sampled_from(["admin", "user", "guest"]),
)
```

Hypothesis 会生成各种 User 实例——空名字、超长名字、零岁、150 岁、每个角色。不用手写 fixture。

## 和 pytest 的集成

Hypothesis 和 pytest 深度集成，不需要额外配置：

```bash
pip install hypothesis
pytest                    # hypothesis 测试自动发现
```

`@h_settings` 控制测试行为：

```python
from hypothesis import settings

@given(st.lists(st.integers()))
@settings(max_examples=200)      # 跑 200 个例子（默认 100）
def test_slow(lst):
    ...

@given(st.text())
@settings(deadline=500)          # 单例超时 500ms
def test_fast(text):
    ...

@given(st.lists(st.integers(), min_size=1000))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_intensive(lst):          # 数据量大，允许慢
    ...
```

## 什么时候用 Hypothesis

不是所有测试都要属性测试。一个简单的原则：

| 场景 | 用什么 |
|------|--------|
| HTTP 接口的特定参数组合 | 传统单测 |
| 排序、解析、序列化、编码 | Hypothesis |
| 数据库 constraint（UNIQUE、NOT NULL） | Hypothesis |
| 配置校验（env 覆盖、默认值） | Hypothesis |
| 算法正确性（排序、搜索、压缩） | Hypothesis |
| Mock 外部服务的集成测试 | 传统单测 + Mock |

规则是：**输入空间越大、越结构化、越容易用属性描述的越适合 Hypothesis。输入空间小、手工枚举就够了的不需要。**

## 实战：Sequoia-X 怎么用的

前面源码阅读系列分析的量化选股系统 Sequoia-X，它的测试全是 Hypothesis 写的：

```python
@given(
    symbol=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    trade_date=st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)),
)
@h_settings(max_examples=50, deadline=None)
def test_unique_symbol_date_constraint(symbol, trade_date):
    """任一 6 位股票代码 + 任一日期，插入两次后 count 为 1。"""
    ...
```

50 个随机 symbol + 50 个随机日期 = 2500 个组合，但每个 symbol 和每个日期独立验证。不用 Hypothesis 的话，没人会手写 50 个股票代码的测试。

> 仓库：[https://github.com/HypothesisWorks/hypothesis](https://github.com/HypothesisWorks/hypothesis)
> 文档：[https://hypothesis.readthedocs.io/](https://hypothesis.readthedocs.io/)
