# Strategy 模式 — Rust 设计模式系列

> 系列：用 Rust 的类型系统重新审视 GoF 23 个设计模式。本文基于 Rust 1.95 稳定版。

## 生活比喻：导航 App 的路线选择

你用导航 App 导航，它给你三条路线：

- **最快路线**——走高速，绕远但快
- **最短路线**——走直线，近但红绿灯多
- **不走高速**——避开收费站

目的地相同，**策略不同**。你选哪条，App 就按哪个策略规划。这就是 Strategy 模式——**同一接口，不同算法实现**。

## GoF 的做法：接口 + 运行时选择

GoF 定义一个 Strategy 接口，每个策略是一个实现类，运行时注入：

```rust
// GoF 风格：trait 对象
trait RouteStrategy {
    fn calculate(&self, from: &str, to: &str) -> Route;
}

struct FastestRoute;
struct ShortestRoute;
struct NoHighwayRoute;

impl RouteStrategy for FastestRoute {
    fn calculate(&self, from: &str, to: &str) -> Route {
        // 走高速算法
        Route { distance: 120, time: 60 }
    }
}

struct Navigator {
    strategy: Box<dyn RouteStrategy>,
}

impl Navigator {
    fn navigate(&self, from: &str, to: &str) -> Route {
        self.strategy.calculate(from, to)
    }
}
```

## Rust 的解法：泛型静态分发

Rust 用泛型替代 `Box<dyn>`，编译期确定策略，零开销：

```rust
trait RouteStrategy {
    fn calculate(&self, from: &str, to: &str) -> Route;
}

struct FastestRoute;
struct ShortestRoute;

impl RouteStrategy for FastestRoute {
    fn calculate(&self, from: &str, to: &str) -> Route {
        Route { distance: 120, time: 60 }
    }
}

impl RouteStrategy for ShortestRoute {
    fn calculate(&self, from: &str, to: &str) -> Route {
        Route { distance: 80, time: 90 }
    }
}

// 泛型：编译期确定策略
struct Navigator<S: RouteStrategy> {
    strategy: S,
}

impl<S: RouteStrategy> Navigator<S> {
    fn navigate(&self, from: &str, to: &str) -> Route {
        self.strategy.calculate(from, to)
    }
}

// 使用
let nav = Navigator { strategy: FastestRoute };
let route = nav.navigate("家", "公司");
```

**好在哪：**

- **零开销**——泛型单态化，没有 `Box::new`，没有虚函数调用
- **编译器优化**——策略代码被内联，比 `dyn Trait` 快
- **类型安全**——编译期检查策略是否实现了 trait

## 对比：泛型 vs trait 对象

```rust
// 泛型：编译期确定，零开销
fn navigate<S: RouteStrategy>(strategy: S, from: &str, to: &str) -> Route {
    strategy.calculate(from, to)
}

// trait 对象：运行时确定，有开销
fn navigate(strategy: &dyn RouteStrategy, from: &str, to: &str) -> Route {
    strategy.calculate(from, to)
}
```

| 维度 | 泛型 `S: Trait` | trait 对象 `dyn Trait` |
|------|----------------|----------------------|
| 分发方式 | 编译期单态化 | 运行时虚表 |
| 开销 | 零（内联） | 一次间接调用 |
| 策略切换 | 编译期固定 | 运行时可换 |
| 代码膨胀 | 每个策略一份代码 | 共享一份代码 |
| 适用场景 | 策略固定 | 策略动态选择 |

**选择依据：** 策略在编译期就知道用哪个 → 泛型；需要运行时切换 → trait 对象。

## 闭包作为 Strategy

Rust 的闭包天然就是轻量级策略——不需要定义 struct 和 impl：

```rust
fn sort_by_strategy<T, F>(data: &mut [T], strategy: F)
where
    F: Fn(&T, &T) -> std::cmp::Ordering,
{
    data.sort_by(strategy)
}

// 使用
let mut users = vec![...];
sort_by_strategy(&mut users, |a, b| a.age.cmp(&b.age));     // 按年龄
sort_by_strategy(&mut users, |a, b| a.name.cmp(&b.name));   // 按姓名
sort_by_strategy(&mut users, |a, b| b.score.cmp(&a.score)); // 按分数降序
```

**好在哪：**

- **内联定义**——不需要额外的 struct
- **捕获环境**——闭包可以捕获外部变量
- **零开销**——`Fn` 泛型，编译期单态化

## 实战：排序策略

```rust
use std::cmp::Ordering;

struct Sorter<T> {
    data: Vec<T>,
}

impl<T: Ord> Sorter<T> {
    fn new(data: Vec<T>) -> Self {
        Self { data }
    }

    // 策略一：标准排序
    fn sort_default(mut self) -> Vec<T> {
        self.data.sort();
        self.data
    }

    // 策略二：自定义比较函数
    fn sort_by<F>(mut self, cmp: F) -> Vec<T>
    where
        F: Fn(&T, &T) -> Ordering,
    {
        self.data.sort_by(cmp);
        self.data
    }

    // 策略三：按 key 排序
    fn sort_by_key<K, F>(mut self, key: F) -> Vec<T>
    where
        K: Ord,
        F: Fn(&T) -> K,
    {
        self.data.sort_by_key(key);
        self.data
    }
}

// 使用
let sorted = Sorter::new(users)
    .sort_by_key(|u| u.name.clone());  // 按姓名排序
```

## 实战：验证策略

```rust
trait Validator {
    fn validate(&self, input: &str) -> Result<(), String>;
}

struct EmailValidator;
struct PhoneValidator;
struct MinLengthValidator(usize);

impl Validator for EmailValidator {
    fn validate(&self, input: &str) -> Result<(), String> {
        if input.contains('@') { Ok(()) } else { Err("Invalid email".into()) }
    }
}

impl Validator for PhoneValidator {
    fn validate(&self, input: &str) -> Result<(), String> {
        if input.chars().all(|c| c.is_ascii_digit()) { Ok(()) }
        else { Err("Invalid phone".into()) }
    }
}

impl Validator for MinLengthValidator {
    fn validate(&self, input: &str) -> Result<(), String> {
        if input.len() >= self.0 { Ok(()) }
        else { Err(format!("Min length {}", self.0)) }
    }
}

// 泛型：编译期确定验证器
fn validate<V: Validator>(validator: V, input: &str) -> Result<(), String> {
    validator.validate(input)
}

// 使用
validate(EmailValidator, "test@example.com")?;
validate(MinLengthValidator(8), "short")?;
```

## 实战：压缩策略

```rust
use std::io::{self, Read, Write};

trait Compressor {
    fn compress(&self, data: &[u8]) -> io::Result<Vec<u8>>;
    fn decompress(&self, data: &[u8]) -> io::Result<Vec<u8>>;
}

struct Gzip;
struct Zstd;
struct Lz4;

impl Compressor for Gzip {
    fn compress(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        // gzip 压缩
        Ok(data.to_vec())
    }
    fn decompress(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        Ok(data.to_vec())
    }
}

impl Compressor for Zstd {
    fn compress(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        // zstd 压缩
        Ok(data.to_vec())
    }
    fn decompress(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        Ok(data.to_vec())
    }
}

// 泛型存储：编译期确定压缩算法
struct Storage<C: Compressor> {
    compressor: C,
}

impl<C: Compressor> Storage<C> {
    fn save(&self, key: &str, data: &[u8]) -> io::Result<()> {
        let compressed = self.compressor.compress(data)?;
        // 保存 compressed
        Ok(())
    }

    fn load(&self, key: &str) -> io::Result<Vec<u8>> {
        // 读取 compressed
        let compressed = vec![];
        self.compressor.decompress(&compressed)
    }
}

// 使用
let storage = Storage { compressor: Zstd };
storage.save("data", b"hello")?;
```

## 骨架代码

```rust
// 泛型 Strategy（编译期固定）
trait Strategy {
    type Output;
    fn execute(&self, input: &str) -> Self::Output;
}

struct Context<S: Strategy> {
    strategy: S,
}

impl<S: Strategy> Context<S> {
    fn run(&self, input: &str) -> S::Output {
        self.strategy.execute(input)
    }

    // 切换策略需要重新创建 Context
    fn with_strategy<T: Strategy>(self, strategy: T) -> Context<T> {
        Context { strategy }
    }
}

// 闭包 Strategy（更轻量）
fn run_with_strategy<F>(strategy: F, input: &str) -> String
where
    F: Fn(&str) -> String,
{
    strategy(input)
}

// trait 对象 Strategy（运行时切换）
fn run_dynamic(strategy: &dyn Strategy<Output = String>, input: &str) -> String {
    strategy.execute(input)
}
```

## 什么时候该用 Strategy

**适合的场景：**

- 同一接口有多种算法实现
- 算法需要独立于使用它的客户端变化
- 需要在运行时切换算法

**不适合的场景：**

- 策略很少变化——直接 if-else 更简单
- 策略数量固定且已知——enum + match 更 Rust
- 只有一两种策略——过度设计

## 总结

Rust 里 Strategy 模式有三种实现方式：

| 方式 | 适用场景 | 开销 |
|------|---------|------|
| 泛型 `S: Trait` | 策略编译期固定 | 零（单态化） |
| 闭包 `Fn` | 轻量策略，内联定义 | 零（内联） |
| trait 对象 `dyn Trait` | 策略运行时切换 | 一次间接调用 |

GoF 的 Strategy 在 Rust 里可以是泛型、闭包、或 enum + match——取决于你需要编译期固定还是运行时切换。大多数场景下，泛型或闭包就够了。
