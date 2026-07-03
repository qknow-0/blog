# Rust Trait 与泛型：多态不只是继承

> 本文基于 Rust 1.96。

把 trait 想象成**招聘岗位的要求清单**。

一家公司要招人，先列一个清单：「需要会写 Excel」、「需要会做 PPT」、「需要会 Python」。这个清单就是 **trait**——它定义了这个岗位需要什么能力。应聘者往简历上打勾「我会 Excel」「我会 Python」——这就是 **impl Trait for Type**，某个具体类型实现了某个 trait。

## Trait：行为的契约——岗位要求清单

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

和 Java 的 `interface` 像，但有两个根本区别——也是这份「招聘要求」和 Java interface 不一样的地方：

**1. trait 可以不在类型定义时实现——岗位要求可以在招聘手册之外单独发布**

```rust
// 你定义的类型——你是求职者
struct Post { title: String }

// 别人库里的 trait——那是另一家公司的岗位要求
use std::fmt::Display;

// 给 Post 实现 Display——你对另一家公司的要求也打了勾
impl Display for Post {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> &std::fmt::Result {
        write!(f, "{}", self.title)
    }
}
```

Java 的 `implements` 必须在类定义时声明——就像你只能在一家公司填写它的入职表格。Rust 的 `impl Trait for Type` 可以写在任何地方——你可以拿着自己的简历对任何一家公司说「我会你们的技能」。这背后叫**孤儿规则**（orphan rule）——trait 或类型至少有一个必须在当前 crate 中定义，A 公司不能替 B 公司列招聘要求。

**2. trait 可以有默认实现——岗位提供培训**

```rust
trait Summary {
    fn summarize(&self) -> String {
        String::from("(暂无摘要)")    // 默认实现——公司提供培训手册
    }
}

struct Tweet { content: String }

impl Summary for Tweet {}  // 直接用默认实现——不需要额外培训
```

`Tweet` 不需要自己写 `summarize`——trait 已经给了默认行为，就像新员工入职后公司提供了一份现成的培训材料。这比 Java 的 `default` 方法更早出现，而且可以在默认实现里调用其他 trait 方法——培训材料里还引用了其他技能手册。

## 泛型：一个岗位要求，多家公司适用

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

Java 的泛型在运行时擦除类型（type erasure），`List<Integer>` 和 `List<String>` 是同样的字节码——就像两家公司的岗位要求描述完全一样、但实际做的工作不同，HR 把两份 JD 揉成了一看就皱巴巴的纸。Rust 的泛型是**编译期单态化**（monomorphization）——编译器给每个具体类型生成独立代码：

```rust
// 你写的——「需要会做 Excel」这个通用要求
largest(&[1, 2, 3]);      // T = i32 —— 甲公司招人
largest(&['a', 'b', 'c']);  // T = char —— 乙公司招人

// 编译器生成——每家公司的 JD 都印了一份独立的
fn largest_i32(list: &[i32]) -> &i32 { /* ... */ }
fn largest_char(list: &[char]) -> &char { /* ... */ }
```

生成的机器码和手写 `largest_for_i32`、`largest_for_char` 完全一样——零运行时代价，就像每个岗位 JD 都是独立印刷、不需要翻来覆去找同一页。代价是编译时间更长、二进制体积更大——印刷更多的纸。

## Trait Bound：硬性门槛

`<T: PartialOrd>` 叫 trait bound——告诉编译器 T 必须能比较大小，就像 JD 上写着「本科以上学历」，HR 先筛学历再往下走：

```rust
use std::fmt::Display;

// 多个 bound 用 +——要求同时具备多个能力
fn notify<T: Summary + Display>(item: &T) {
    println!("通知：{}", item.summarize());
    println!("显示：{item}");  // Display 给了这个能力
}

// 语法糖：where——把要求清单单独列一页
fn notify<T, U>(t: &T, u: &U)
where
    T: Summary + Display,    // T 必须会写摘要 + 会展示
    U: Clone + PartialOrd,   // U 必须能复制 + 能排序
{
    // ...
}
```

和 Java 的 `<T extends Comparable & Serializable>` 等价，但 Rust 的 trait bound 在编译期解决而非靠虚表——HR 在简历筛选阶段就把不合格的剔除了，不需要面试时才发现这人不行。

## impl Trait vs dyn Trait

这是 Rust 里最容易搞混的概念。用招聘来理解：**`impl Trait` 是公司内部定向招聘，`dyn Trait` 是公开社招**。

**impl Trait（静态）**——内推通道：

```rust
fn returns_summarizable() -> impl Summary {
    Article { /* ... */ }
}
```

调用者不知道返回的具体类型，但调用者不需要知道——HR 知道最终招的是个 `Article` 类型的人就行。每个调用点生成一份代码（每个部门招的人不同，HR 单独处理），零运行时开销，但二进制会变大（招聘材料跟人走）。

**dyn Trait（动态）**——统一社招通道：

```rust
fn notify_all(items: &[Box<dyn Summary>]) {
    for item in items {
        println!("{}", item.summarize());  // 虚表调用——按简历技能匹配
    }
}

let items: Vec<Box<dyn Summary>> = vec![
    Box::new(Article { /* ... */ }),
    Box::new(Tweet { /* ... */ }),
];
notify_all(&items);
```

`dyn Summary` 背后是虚表（vtable），和 C++ 的虚函数调用相似——HR 拿着「会写摘要」这个统一要求去匹配所有人。代价很小——多一次指针跳转，就像 HR 需要翻一下每个人的简历确认技能——但能把不同类型放进同一个集合里。这是 `impl Trait` 做不到的。

| | impl Trait | dyn Trait |
|------|:---:|:---:|
| 派发时机 | 编译期（内推定向） | 运行时（公开社招） |
| 开销 | 零（单态化） | 虚表跳转（翻简历一次） |
| 二进制体积 | 每个类型一份代码 | 一份代码 |
| 集合中放不同类型 | ❌ | ✅（Box\<dyn\>） |
| 适用场景 | 大多数情况（内部都知道） | 需要异质集合时（什么人都有） |

Rust 社区约定：**默认用 impl Trait，需要运行时多态时才用 dyn——先走内推，不行再社招**。

## 常见标准库 trait——各行各业的通用技能

这几个在 Rust 代码里出现频率最高，理解它们能读懂大部分接口：

```rust
// Clone：显式复制——你明确说「我要这个证的复印件」
#[derive(Clone)]
struct Config { timeout: u64 }

// Copy：隐式位复制——只需要看一眼就知道的，不需要复印
#[derive(Copy, Clone)]
struct Point { x: f64, y: f64 } // 栈上的东西，看一眼就知道了

// Drop：离职交接，离开岗位时自动做
impl Drop for Connection {
    fn drop(&mut self) {
        self.close();  // RAII——离职时还工卡
    }
}

// From/TryFrom：从 A 岗转到 B 岗
impl From<u64> for Duration {
    fn from(secs: u64) -> Duration { Duration::new(secs, 0) }
}
let d: Duration = 60.into();  // From 让 .into() 可用——转岗通道
```

## 组合而非继承——按技能拼团队，而不是按家谱招人

Java 常见「Animal → Dog → Poodle」三层继承链——就像家族企业：爷爷是家族创始人、爸爸继承、儿子再继承。Rust 用 trait 组合——像组建项目团队：

```rust
// 不是「Poodle 继承 Dog 继承 Animal」
// 而是「Poodle 实现 Bark + Fetch + Walk trait」
// 就像招一个同时会「吠叫」「捡球」「随行」三个技能的人

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

继承给了一个不需要的基类全部方法——就像世袭制下你继承了你爷爷的所有企业，包括他不赚钱的那条业务线。组合只给需要的行为——你说你「会吠叫」，我就只考察你的吠叫能力。一条拉布拉多犬可以加 `impl Swim`、`impl Guide` 而不需要修改 `Poodle` 的定义——比在继承树里加中间类灵活得多，就像你可以在项目需要时随时外聘一个会游泳的人。

继承最大的问题是强迫一个线性的分类体系——你爸是谁你就必须是谁。现实世界的对象往往同时属于多个维度——水生/陆生、食肉/食草、可驯化/野生。Trait 让你自由组合维度——你想会什么就自己打勾，不受出生限制。

## 总结

- **Trait 是岗位要求清单**——可以脱离类型定义实现（谁都能打勾），可以有默认实现（提供培训）
- **泛型是零成本抽象**——编译期单态化生成具体代码，像每个岗位独立印刷 JD
- **impl Trait 内推、dyn Trait 社招**——默认用前者，异质集合用后者
- **孤儿规则保证 trait 实现全局唯一**——A 公司不能替 B 公司列招聘要求
- **组合胜过继承**——多个 trait 拼出能力，不需要基类链，就像按技能组建项目团队而不是按家谱世袭

> 适合有 Java/C++ 多态基础，想理解 Rust 抽象机制的读者。

**返回：** [Rust 笔记](index.md)
