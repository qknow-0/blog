# Python 面向对象（二）：封装与属性——Python 的数据隐藏之道

> 本文基于 Python 3.12，涉及语法特性会标注最低支持版本。

上一篇讲了 class 和对象的基本模型。这一篇讲封装——Python 没有 Java 式的 `private` 关键字。它是怎么在不破坏灵活性的前提下，保护数据不被随意篡改的？

## Python 的封装哲学：「我们都是成年人」

```python
class BankAccount:
    def __init__(self):
        self._balance = 0        # 约定：别碰
        self.__secret = "xyz"    # name mangling：变成 _BankAccount__secret

a = BankAccount()
print(a._balance)                # 0——可以访问，约定不保证
print(a._BankAccount__secret)    # "xyz"——name mangling 也不保证
```

Python 只有两种级别的「私有」：

| 机制 | 写法 | 实际效果 |
|------|------|---------|
| 约定私有 | `_single_leading_underscore` | `from module import *` 不导入。IDE 提示。大家约定不碰 |
| name mangling | `__double_leading_underscore` | 编译器重命名为 `_ClassName__attr`。防止子类无意覆盖 |

**没有机制能阻止你访问任何属性**。这是故意的——Guido 的原话是 "We're all consenting adults here"。Python 信任程序员：你知道自己在做什么，如果你非要碰下划线开头的东西，你的代码出问题自己负责。

## name mangling 的真正用途

name mangling 常常被误解成「Python 的 private」。它不是。它的真正目的是**防止子类无意覆盖父类的内部属性**：

```python
class Tokenizer:
    def __init__(self):
        self.__cache = {}    # 内部缓存——不希望被子类覆盖

    def tokenize(self, text):
        if text in self.__cache:
            return self.__cache[text]
        tokens = self._do_tokenize(text)
        self.__cache[text] = tokens
        return tokens

class FancyTokenizer(Tokenizer):
    def __init__(self):
        super().__init__()
        self.__cache = []    # 这是 _FancyTokenizer__cache
                             # 不会覆盖父类的 _Tokenizer__cache ✅
```

如果没有 name mangling，子类的 `self.__cache = []` 会直接把父类的 `self.__cache` 覆盖掉——两个类使用相同的属性名，互相踩脚。Name mangling 让两个 `__cache` 变成不同的属性名，互不干扰。

它**不是**安全机制——不是为了防黑客，是为了防「意外」：

```python
a = BankAccount()
# 如果你真的想访问，Python 不会阻止你
print(a._BankAccount__secret)  # "xyz"——直接访问 mangled 后的名字就行
```

## `@property`——把方法伪装成属性

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        """读——像属性一样访问"""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        """写——带验证"""
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度")
        self._celsius = value

    @property
    def fahrenheit(self):
        """计算属性——不存，每次算"""
        return self._celsius * 9/5 + 32

t = Temperature(25)
print(t.celsius)      # 25    ——不用写 ()
print(t.fahrenheit)   # 77.0  ——计算属性
t.celsius = 30        # 赋值触发 setter 验证
# t.celsius = -500    # ❌ ValueError: 温度不能低于绝对零度
```

核心价值在于**统一访问原则（Uniform Access Principle）**：

```python
# 一开始：简单属性就够了
class Person:
    def __init__(self, name):
        self.name = name

p = Person("Alice")
p.name = "Bob"    # 调用方：直接赋值

# 后来：需要加验证。改成 property ——调用方代码零改动
class Person:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value.strip():
            raise ValueError("名字不能为空")
        self._name = value

# 调用方代码完全不需要改
p = Person("Alice")
p.name = "Bob"    # 同样是赋值语法，但经历了 setter 验证
```

所有调用 `p.name = ...` 的代码都不需要改动——从直接赋值变成了带验证的赋值，对调用方完全透明。这就是 property 的关键价值。

## property 底层：descriptor protocol

`@property` 是怎么工作的？它背后是 descriptor protocol：

```python
class MyProperty:
    """@property 的简化实现"""
    def __init__(self, fget=None, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def setter(self, fset):
        return type(self)(self.fget, fset)
```

当你写 `t.celsius` 时，Python 发现 `Temperature.celsius` 是一个 descriptor（有 `__get__` 方法），就调用 `celsius.__get__(t, Temperature)`——返回值是 `t._celsius`。同理，`t.celsius = 30` 触发 `celsius.__set__(t, 30)`。

## 什么时候应该添加 setter

并非所有 property 都需要 setter：

```python
class Order:
    def __init__(self, items):
        self._items = list(items)

    @property
    def items(self):
        """订单项——只读"""
        return self._items.copy()   # 返回副本，防止外部修改内部状态

    @property
    def total(self):
        """总价——计算属性，只读"""
        return sum(item.price for item in self._items)
```

只读 property 是防御性编程的利器——外部只能 `order.total` 读，没法 `order.total = 0` 改。比 `get_total()` 方法更 Pythonic。

## 总结

Python 的封装靠三层：

1. **约定**（`_`）：大部分场景足够了——大家都是成年人
2. **name mangling**（`__`）：防止子类意外覆盖——不是安全机制
3. **property**：让方法看起来像属性——调用方不需要知道你背后有验证或计算

第三篇进入继承体系——`super()` 到底做了什么、多继承为什么不会乱。

→ [（三）继承与 MRO：super() 和多继承的底层逻辑](03-inheritance.md)
