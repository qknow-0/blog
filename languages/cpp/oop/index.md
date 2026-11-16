# C++ 面向对象系列

C++ 的面向对象不只是 `class` 加继承。真正难的是三件事：怎么把不变量守住、什么时候该用继承、以及怎么让自定义类型用起来像内置类型。

本目录六篇文章按阅读顺序统一编号，从类和对象出发，经过封装、继承、多态和对象语义，最后落到运算符重载。所有示例基于 C++23。

## 阅读顺序

1. **[（一）类与对象：把状态和行为装进同一个盒子](01-basics-classes.md)** — 2026-10-27
   - 构造函数、`const` 成员、`static` 成员、拷贝与移动的默认行为

2. **[（二）封装与接口：把“能做什么”和“怎么做”分开](02-encapsulation.md)** — 2026-11-16
   - 不变量与访问控制、接口设计、pimpl 编译防火墙、NVI（public 非虚 / private 虚）

3. **[（三）继承的边界：is-a 不是万能钥匙](03-inheritance.md)** — 2026-11-16
   - 三种继承方式、构造/析构顺序、名字隐藏、多重继承与菱形、组合优于继承、LSP

4. **[（四）虚函数：一张 vtable 背后的点菜流程](04-virtual-functions.md)** — 2026-10-27
   - 运行期多态、vtable、虚析构、对象切片、CRTP 与 `std::variant`

5. **[（五）拷贝控制：Rule of 0/3/5 与被省掉的拷贝](05-copy-control.md)** — 2026-11-16
   - 特殊成员函数、深拷贝/浅拷贝、移动构造、拷贝消除

6. **[（六）运算符重载：让自定义类型说人话](06-operator-overloading.md)** — 2026-11-16
   - 成员 vs 非成员、算术运算符、C++20 比较运算符、流运算符、转换运算符、常见坑

## 前置知识

- [C++ 基础语法：变量、类型与初始化](../basics-types.md)
- [C++ 基础语法：指针与引用](../basics-pointers-references.md)
- [C++ 基础语法：vector、string、map 与标准库入门](../basics-stl.md)

## 和已有文章的关系

本系列讲「怎么设计类型」，其他文章讲「类型背后的机制」：

| 主题 | 本系列 | 深入阅读 |
|:-----|:-------|:---------|
| 类的语法与不变量 | [类与对象](01-basics-classes.md) | [封装与接口](02-encapsulation.md) |
| 运行期多态 | [虚函数](04-virtual-functions.md) | [继承的边界](03-inheritance.md) |
| 对象拷贝与移动 | [拷贝控制](05-copy-control.md) | [移动语义](../move-semantics.md) |
| 资源所有权 | [封装与接口](02-encapsulation.md) | [RAII](../raii.md)、[智能指针](../smart-pointers.md) |
| 构造失败与析构 | [继承的边界](03-inheritance.md) | [异常安全](../exception-safety.md) |
| 运算符与函数对象 | [运算符重载](06-operator-overloading.md) | [Lambda 表达式](../lambda-expressions.md) |
