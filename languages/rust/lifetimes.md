# Rust 生命周期：'a 不是魔法，是停车票上的有效期

> 本文基于 Rust 1.96（2024 edition）。

Rust 初学者过了所有权这关之后，第二个卡住的地方就是生命周期。

`fn foo<'a>(x: &'a str) -> &'a str`——每个教程都说 `'a` 是生命周期标注，但很少有人用一个你每天都会遇到的东西来比喻它：**停车票**。

`'a` 就是一张停车票。停车票上写着你的车最晚什么时候必须开走。你不能用一张已经过期的停车票继续停车——就像你不能用一个已经释放的变量的引用。

## 生命周期标注不改变代码行为

最重要的概念放在最前面：

**生命周期标注不改变程序运行时行为。它只是告诉停车场管理员「这辆车和那辆车停在同一个收费时段」，管理员验证你说得对不对。**

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

`'a` 不是在延长什么的生命周期——它只是给三辆车（x、y、返回值）贴上了同一张停车票，管理员检查「贴同一张票的车，最晚不能超过票上写的到期时间」。

编译通过的条件：
- 返回值 `&'a str` 的任意使用点，必须早于 x 的停车到期时间
- 也早于 y 的停车到期时间
- 也就是说：返回值不能比 x 和 y 中停得最短的那辆车开得更久

如果通不过——停车票被管理员没收，重写。通过了——不会有车停在过道上挡路。这就是 Rust 的承诺。

## 什么时候需要标注

三条规则覆盖 90% 的情况。想象停车场管理员有三个自动规则：

**规则一：每辆车都有自己的停车票。**

```rust
fn foo(x: &str, y: &str) {}
// 等价于
fn foo<'a, 'b>(x: &'a str, y: &'b str) {}
```

**规则二：如果只有一辆车进来停车，它的停车票有效期就是管理员给你的默认时长。**

```rust
fn first_word(s: &str) -> &str {}
// 等价于
fn first_word<'a>(s: &'a str) -> &'a str {}
```

**规则三：如果 `&self` 是参数之一，它的停车票时效覆盖所有输出。**

```rust
impl Parser {
    fn parse(&self, input: &str) -> &str {}
}
// 等价于
impl<'a> Parser {
    fn parse(&'a self, input: &str) -> &'a str {}
}
```

这三条规则被称为**生命周期省略规则**（lifetime elision）。只有管理员没法自动推断时才需要手动标注——也就是上面三条规则都不匹配时。`longest` 有两辆车进来却没有 `&self`，管理员不知道该用哪辆车的停车票时间来算，所以你必须手动贴一张共同的票。

## 从报错倒推理解

管理员拦下你的时候，他在说什么？拿一个典型场景来看：

```rust
fn return_short_lived() -> &str {
    let s = String::from("hello");
    &s   // ❌ error[E0515]: cannot return reference to local variable `s`
}
```

这就像你在停车场里找了辆别人的车，说要开走——管理员直接拦住你：这辆车根本不是你的，你还没进来它就要被拖走了。`s` 在函数结束时就被拖走（drop），你返回的指向它的引用就是一张过期的停车票。

再看需要手动贴票的场景：

```rust
fn pick<'a>(first: &'a str, _second: &str) -> &'a str {
    first  // 只返回 first，和 _second 无关
}
```

`'a` 只贴在 `first` 和返回值上，`_second` 用独立的隐式停车票。管理员不需要两辆车停一样久——他只关心你开走的那辆车不能比 `first` 的停车到期时间晚。

这就是生命周期标注的精确性：**不是粗暴地让所有引用活一样久，而是精确地描述「谁和谁的停车票绑在一起」。**

## 结构体里的生命周期

当结构体持有引用时，必须标注——因为结构体的存续时间不能长于它引用的数据的存续时间。这就像停车场的管理室不能比停车场本身拆得晚：

```rust
struct Excerpt<'a> {
    text: &'a str,        // Excerpt 的停车时间不能比 text 长
}

impl<'a> Excerpt<'a> {
    fn announce_and_return(&self, announcement: &str) -> &str {
        println!("{}", announcement);
        self.text            // 规则三：用 &self 的停车票
    }
}
```

关键理解：**`Excerpt<'a>` 的实例不能比它引用的 `str` 停得更久**。编译器强制这个约束：

```rust
let novel = String::from("Call me Ishmael...");
let excerpt = Excerpt { text: &novel };
drop(novel);                    // ❌ error: cannot move out of `novel`
println!("{}", excerpt.text);   //    because it is borrowed
```

`excerpt` 停在 `novel` 的车位上，所以 `novel` 在 `excerpt` 开走之后才能被拖走。这个逻辑和普通停车规则完全一致——生命周期标注只是让这个约束在结构体层面显式化了。

### 逐步拆解一个更复杂的例子

上面的 `Excerpt` 很简单——只有一个车位、一张停车票。来看一个涉及两个车位和保安亭的场景，分步理解管理员在每一步做什么。

**第一步：建一个更大的停车场**

```rust
#[derive(Debug)]
struct Document<'a> {
    title: &'a str,     // 文档里有一辆 title 车
    body: &'a str,      // 文档里有一辆 body 车
}
// 'a 的意思是：这个停车场不能比停在这里的 title 和 body 中
// 走得最早的那辆车更晚关门
```

**第二步：开一个入口闸机**

```rust
impl<'a> Document<'a> {
    fn new(title: &'a str, body: &'a str) -> Document<'a> {
        Document { title, body }
    }
}
// 参数 title 和 body 都贴了 'a 票
// 返回值 Document<'a> 也贴了 'a 票
// 管理员验证：停车场关门前，title 和 body 都在里面
// → title 和 body 都停至少 'a 那么久 → 成立 ✅
```

**第三步：正确停车**

```rust
fn main() {
    let title = String::from("深入理解 Rust 生命周期");
    let body = String::from("生命周期标注不是魔法...");

    let doc = Document::new(&title, &body);
    // doc 停车场里停了 title 和 body 两辆车
    // doc 的关门时间 ≤ title 和 body 中最早开走的那辆

    println!("{:?}", doc);
    // doc 停车场用完了——关门

    drop(body);   // ✅ body 可以开走——停车场已经关了
    drop(title);  // ✅ title 也可以开走
}
```

关键：`doc` 的使用范围被管理员精确追踪。`println!` 之后，`doc` 不再被使用，管理员认为停车场在此关门。之后 `drop(body)` 和 `drop(title)` 都是合法操作。

**第四步：错误停车**

```rust
fn main() {
    let doc;  // 画个停车场图纸——还没建

    let title = String::from("深入理解 Rust 生命周期");
    let body = String::from("生命周期标注不是魔法...");

    doc = Document::new(&title, &body);

    drop(body);   // ❌ error[E0505]: cannot move out of `body`
    //             因为 doc 停车场还没关门，body 还在里面

    println!("{:?}", doc);
}
```

管理员的分析逻辑：

```
1. doc = Document::new(&title, &body)
   → doc 停车场停了 title 和 body
   → doc 的关门时间 ≤ title 的停车到期时间
   → doc 的关门时间 ≤ body 的停车到期时间

2. drop(body)
   → body 想提前开走
   → doc 停车场还开着（后面有 println!）
   → doc 里还有 body 的车位
   → body 开走后车位空了，但 doc 还在用它
   → 不通过 ❌
```

**第五步：修复——提前关停车场**

```rust
fn main() {
    let title = String::from("深入理解 Rust 生命周期");
    let body = String::from("生命周期标注不是魔法...");

    {
        let doc = Document::new(&title, &body);
        println!("{:?}", doc);
    }  // ← doc 停车场在这里关门

    drop(body);   // ✅ 停车场已经关了，可以拖走 body
    drop(title);  // ✅ 同理
}
```

花括号画了一个临时停车区。`doc` 在这个小区域里建和拆。离开花括号后，`doc` 不存在了，它对 `title` 和 `body` 的占用也跟着结束。之后想怎么拖车都行。

**核心认知**：`'a` 标注在 struct 上不是「让车停更久」的魔法——它是让管理员能**追踪每张停车票的有效期**。struct 持有引用 = struct 占用了车位 = 占用的车在占用期间不能被拖走。标注让这个占用关系对管理员可见。

## 静态生命周期

```rust
fn static_str() -> &'static str {
    "hello"  // 字符串字面量：整个停车场运营期间它都在
}
```

`'static` 意味着「停车场永久车位」。不是说你主动让什么车停成永久——只有从建场就在的固定设施（字符串字面量、`const` 值）和主动 `Box::leak` 出来的车才真正是 `'static`。

**不要用 `'static` 来「修」生命周期报错。** 如果你在某个地方贴了 `'static` 永久票只为了通过管理员检查，那你在用一个错误的标签掩盖真实的停车关系。正确的做法是：理解你的车到底谁停的、谁开走、谁会比谁先走，然后贴上合适的停车票。

## 实际场景

### 场景一：代客泊车——返回引用避免挪车

```rust
struct CsvRow<'a> {
    raw: &'a str,
}

impl<'a> CsvRow<'a> {
    fn field(&self, index: usize) -> Option<&'a str> {
        self.raw.split(',').nth(index)
    }
}

// 使用
let csv_data = String::from("Alice,30,Engineer\nBob,25,Designer");
for line in csv_data.lines() {
    let row = CsvRow { raw: line };
    if let Some(name) = row.field(0) {
        println!("Name: {}", name);  // 零挪车——name 直接指向 csv_data 内部
    }
}
```

`CsvRow` 不拥有车辆——它只是 `csv_data` 停车场里的一个指引牌。所有 `field()` 返回的 `&str` 都直接指向原始停车场内部，零调度、零挪车。`'a` 保证了只要这些指引牌还在，`csv_data` 停车场就不能关门。

### 场景二：多层停车场——多重引用的生命周期

```rust
struct Config<'a> {
    path: &'a str,
}

struct App<'a> {
    config: &'a Config<'a>,
}

fn create_app(config_path: &str) -> App<'_> {
    // 实际中 Config 通常从文件读取并拥有数据
    // 这里展示嵌套引用的标注方式
    todo!()
}
```

`App<'a>` 的 `'a` 被用在两处：`&'a Config<'a>`。这意味着 `App` 不能比它引用的 `Config` 楼层关得早，而且 `Config` 的 `'a` 和 `App` 的 `'a` 是同一张停车票——它们引用同一辆底层车。标注精确表达了「App 和 Config 共用同一个停车场的同一张票」。

### 场景三：自动缴费机——最常碰到但不需要手写的生命周期

```rust
let text = String::from("hello world");
let first_word = text
    .split_whitespace()   // split_whitespace<'a>(&'a self) -> SplitWhitespace<'a>
    .next()               // next(&'a mut self) -> Option<&'a str>
    .unwrap();            // first_word: &str ——指向 text 内部

println!("{first_word}"); // "hello"
drop(text);               // ❌ 不行——first_word 还在用停车场
// println!("{first_word}");
```

自动缴费机里大量的停车票都在机器自己的说明书里写好了——你不需要手动贴票，但理解它们在做什么能少踩坑。`split_whitespace` 返回的缴费凭条不拥有车辆，它持有对原停车场的引用。所以凭条存在期间，原停车场不能被修改或关门。

## 三个心智模型

**模型一：车票上的截止时间**

生命周期不是「你能停多久」，而是「管理员能证明你至少可以停到什么时候」。`'a` 的实际含义是「在这段代码中，这个引用可以安全使用的最晚时间」。

```rust
fn demo() {
    let x = String::from("long");  // 停了一辆能停很久的车
    let result;
    {
        let y = String::from("short");  // 这辆车只能停一小会儿
        // y 的停车截止时间到此花括号结束
        // 如果 result 停到了 y 的车位，管理员会在这里报错
        result = &x;  // 只是占 x 的车位，OK
    }
    println!("{result}");  // result 停的是 x 的车位——x 还在，没问题
}
```

**模型二：标注是对管理员说「我保证」**

你写 `fn foo<'a>(x: &'a str, y: &'a str) -> &'a str`，是在对管理员说：「我保证开走的那辆车不会比 x 和 y 中停得最短的那辆更晚。你帮我检查这个承诺。」

管理员在每一个出口逐一验证你的承诺。如果某处 `y` 的停车时间确实比 `x` 短，而开走的那辆车在 `y` 被拖走之后还想用——拒绝出场。

**模型三：停车票是在做减法，不是加法**

`'a` 不会让任何车停得更久。它只是限制了你能用那辆车做什么——你不能把它停在比 `'a` 更晚关门的地方。标注越精确，管理员给你的灵活度越大。

## 常见疑问

**为什么有些函数有两辆车进来却不需要标注？**

```rust
fn no_lifetime_needed(x: &str, _y: &i32) -> &str {
    x  // 规则一 + 规则二自动推断：只有一辆车对应出口
}
```

**为什么 trait object 需要 `'a`？**

```rust
trait Animal {}
fn zoo<'a>(animals: &[Box<dyn Animal + 'a>]) {}  // Box<dyn Animal> 默认是 'static
```

`Box<dyn Animal>` 默认隐含 `'static` 永久车位——意味着这个车位上不能停任何临时车。加 `+ 'a` 放宽这个限制。

**为什么闭包有时候需要标注生命周期？**

闭包捕获引用时，编译器自动推断捕获的引用的生命周期。如果你的闭包被存到了结构体里，结构体就需要标注生命周期来覆盖闭包可能的借用。但日常 `.map()`, `.filter()` 的闭包不需要关心这些——编译器会处理好。

## 总结

```
生命周期不做什么：不延长引用的存活时间、不改变运行时行为

生命周期做什么：  给引用贴停车票 → 管理员检查票面日期 →
                  保证开走的那辆车不会比车位本身活得久

什么时候手写：    两辆以上车进来、没有 &self（自己的车）、
                  管理员猜不出哪辆车对应哪个出口
```

学生命周期的正确路径不是背所有语法——是理解**管理员在检查什么**。大多数场景下管理员自动推断就够了，剩下需要手写的时候，问自己：「出口那辆车依赖哪辆进来的车？它们的最短停车时间能覆盖出口的使用时间吗？」

回答这个问题，`'a` 自然就会贴了。

**返回：** [Rust 笔记](index.md)
