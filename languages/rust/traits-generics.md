# Rust Trait 与泛型：多态不只是继承

> 本文基于 Rust 1.85。

Java 教你用继承做多态——子类覆盖父类方法。Rust 走另一条路：**trait 定义行为，泛型提供复用，组合取代继承**。没有基类、没有虚表手动管理、没有运行时类型转换。编译期把所有抽象展开成具体代码，零运行时开销。

## Trait：行为的契约

```rust
trait Summary {
    fn summarize(&self) -> String;
}

struct Article {
    title: String,
    content: String,
}

impl Summary for Article {
    fn summarize(&self) -> String {
        format!("{} —— {}", self.title, &self.content[..50])
    }
}
```

和 Java 的 `interface` 像，但有两个根本区别：

**1. trait 可以不在类型定义时实现**

```rust
// 你定义的类型
struct Post { title: String }

// 别人库里的 trait
use std::fmt::Display;

// 给 Post 实现 Display——不需要改 Post 的定义
impl Display for Post {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> &std::fmt::Result {
        write!(f, "{}", self.title)
    }
}
```

Java 的 `implements` 必须在类定义时声明。Rust 的 `impl Trait for Type` 可以写在任何地方。这叫**孤儿规则**（orphan rule）——trait 或类型至少有一个必须在当前 crate 中定义，防止两个库给同一个类型实现同一个 trait。

**2. trait 可以有默认实现**

```rust
trait Summary {
    fn summarize(&self) -> String {
        String::from("(暂无摘要)")    // 默认实现
    }
}

struct Tweet { content: String }

impl Summary for Tweet {}  // 直接用默认实现
```

`Tweet` 不需要自己写 `summarize`——trait 已经给了默认行为。这比 Java 的 `default` 方法更早出现，而且可以在默认实现里调用其他 trait 方法。

## 泛型：零成本抽象

```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    for item in list {
        if item > largest {
            largest = item;
        }
    }
    largest
}
```

Java 的泛型在运行时擦除类型（type erasure），`List<Integer>` 和 `List<String>` 是同样的字节码。Rust 的泛型是**编译期单态化**（monomorphization）——编译器给每个具体类型生成独立代码：

```rust
// 你写的
largest(&[1, 2, 3]);      // T = i32
largest(&['a', 'b', 'c']);  // T = char

// 编译器生成
fn largest_i32(list: &[i32]) -> &i32 { /* ... */ }
fn largest_char(list: &[char]) -> &char { /* ... */ }
```

生成的机器码和手写 `largest_for_i32`、`largest_for_char` 完全一样——零运行时代价。代价是编译时间更长、二进制体积更大。

编译期单态化 + 无类型擦除解释了 Rust 的两个行为：编译时间比 Go 长，泛型错误信息可能是你能读到的最长的编译器输出。

## Trait Bound：约束泛型

`<T: PartialOrd>` 叫 trait bound——告诉编译器 T 必须能比较大小。这让你能在泛型函数里对 T 做特定操作：

```rust
use std::fmt::Display;

// 多个 bound 用 +
fn notify<T: Summary + Display>(item: &T) {
    println!("通知：{}", item.summarize());
    println!("显示：{item}");  // Display 给了这个能力
}

// 语法糖：where
fn notify<T, U>(t: &T, u: &U)
where
    T: Summary + Display,
    U: Clone + PartialOrd,
{
    // ...
}
```

和 Java 的 `<T extends Comparable & Serializable>` 等价，但 Rust 的 trait bound 在编译期解决而非靠虚表。

## impl Trait vs dyn Trait

这是 Rust 里最容易搞混的概念。一句话说清楚：**`impl Trait` 是编译期静态派发，`dyn Trait` 是运行时动态派发**。

**impl Trait（静态）**：

```rust
fn returns_summarizable() -> impl Summary {
    Article { /* ... */ }
}
```

调用者不知道返回的具体类型，但编译器知道。每个调用点生成一份代码——零运行时开销，但二进制会变大。

**dyn Trait（动态）**：

```rust
fn notify_all(items: &[Box<dyn Summary>]) {
    for item in items {
        println!("{}", item.summarize());  // 虚表调用
    }
}

let items: Vec<Box<dyn Summary>> = vec![
    Box::new(Article { /* ... */ }),
    Box::new(Tweet { /* ... */ }),
];
notify_all(&items);
```

`dyn Summary` 背后是虚表（vtable），和 C++ 的虚函数调用相似。代价很小——多一次指针跳转——但能把不同类型放进同一个集合里。这是 `impl Trait` 做不到的。

| | impl Trait | dyn Trait |
|------|:---:|:---:|
| 派发时机 | 编译期 | 运行时 |
| 开销 | 零（单态化） | 虚表跳转 |
| 二进制体积 | 每个类型一份代码 | 一份代码 |
| 集合中放不同类型 | ❌ | ✅（Box<dyn>） |
| 适用场景 | 大多数情况 | 需要异质集合时 |

Rust 社区约定：**默认用 impl Trait，需要运行时多态时才用 dyn——这是有意为之的谨慎**。

## 常见标准库 trait

这几个在 Rust 代码里出现频率最高，理解它们能读懂大部分接口：

```rust
// Clone：显式复制——调用者意识到复制成本
#[derive(Clone)]
struct Config { timeout: u64 }

// Copy：隐式位复制——仅用于栈上数据
#[derive(Copy, Clone)]
struct Point { x: f64, y: f64 } // 栈上的东西，拷贝无成本

// Drop：析构，离开作用域时自动调用
impl Drop for Connection {
    fn drop(&mut self) {
        self.close();  // RAII
    }
}

// From/TryFrom：类型转换
impl From<u64> for Duration {
    fn from(secs: u64) -> Duration { Duration::new(secs, 0) }
}
let d: Duration = 60.into();  // From 让 .into() 可用
```

## 常见的组合而非继承

Java 常见「Animal → Dog → Poodle」三层继承链。Rust 用 trait 组合：

```rust
// 不是「Poodle 继承 Dog 继承 Animal」
// 而是「Poodle 实现 Bark + Fetch + Walk trait」

trait Bark { fn bark(&self); }
trait Fetch { fn fetch(&self) -> bool; }
trait Walk { fn walk(&mut self, distance: f64); }

struct Poodle { name: String, position: f64 }

impl Bark for Poodle {
    fn bark(&self) { println!("{}: woof!", self.name); }
}
impl Fetch for Poodle {
    fn fetch(&self) -> bool { true }
}
impl Walk for Poodle {
    fn walk(&mut self, d: f64) { self.position += d; }
}
```

继承给了一个不需要的基类全部方法，组合只给需要的行为。一条拉布拉多犬可以加 `impl Swim`、`impl Guide` 而不用改 `Poodle` 的定义——这比在继承树里加中间类灵活得多。

继承最大的问题是强迫一个线性的分类体系。现实世界的对象往往同时属于多个维度——水生/陆生、食肉/食草、可驯化/野生。Trait 让你自由组合维度，继承锁死了一个维度。

## 总结

- **Trait 定义行为契约**——可以脱离类型定义实现，可以有默认实现
- **泛型是零成本抽象**——编译期单态化生成具体代码
- **impl Trait 静态、dyn Trait 动态**——默认用前者，异质集合用后者
- **孤儿规则保证 trait 实现全局唯一**
- **组合胜过继承**——多个 trait 拼出能力，不需要基类链

> 适合有 Java/C++ 多态基础，想理解 Rust 抽象机制的读者。
