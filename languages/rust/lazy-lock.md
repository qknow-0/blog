# Rust LazyLock：酒店式延迟初始化

> 本文基于 Rust 1.96。`std::sync::LazyLock` 自 1.80 起稳定。

你有一个全局配置，但你不想程序启动时就加载——想等到**第一次有人真正用到它的时候**才初始化。这就跟**酒店入住**的逻辑一模一样：酒店（程序）开门营业时，不会把所有房间都提前布置好，而是等客人到了才办理入住。

## 一个你肯定写过的模式：每次客人来了都重新调档

```rust
use std::collections::HashMap;

fn get_config() -> HashMap<String, String> {
    let content = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&content).unwrap()
}

fn lookup(key: &str) -> Option<String> {
    get_config().get(key).cloned()  // 每次客人都重新调档——浪费
}
```

这段代码的问题是：每次调用 `lookup` 都重新读取配置文件——就像酒店前台每次有客人来都打电话给总部重新调取客人档案，从不缓存。你真正想要的是：**第一位客人入住时登记一次，之后所有客人直接刷脸入住。**

## `lazy_static!` 时代：外包给第三方入住系统

在标准库提供方案之前，你得引入外部 crate：

```rust
use lazy_static::lazy_static;

lazy_static! {
    static ref CONFIG: HashMap<String, String> = {
        let content = std::fs::read_to_string("config.toml").unwrap();
        toml::from_str(&content).unwrap()
    };
}
```

这叫 `lazy_static!`，能用，但就像酒店把入住登记外包给第三方公司——多一个依赖，多一个宏，多一份风险。标准库有了自己的方案后，这些第三方 crate 可以光荣退休了。

## 标准的 LazyLock：酒店自建智能前台

从 Rust 1.80 开始，标准库内置了答案：

```rust
use std::sync::LazyLock;

static CONFIG: LazyLock<HashMap<String, String>> = LazyLock::new(|| {
    let content = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&content).unwrap()
});

fn lookup(key: &str) -> Option<String> {
    CONFIG.get(key).cloned()  // 第一次调用时自动初始化，之后直接返回缓存值
}
```

`LazyLock::new(|| ...)` 相当于装了一套**智能前台系统**——客人第一次踏进大门（第一次解引用）时，系统自动办理入住（执行闭包，初始化值）。后面再来客人，直接报房间号就行。

## LazyLock 与 OnceLock 的关系：自动入住 vs 手动入住

很多人把 `LazyLock` 和 `OnceLock` 当成两个东西，但实际上 `LazyLock` 就是 `OnceLock` + 闭包 + `Deref`：

```rust
// 核心逻辑等价于：
struct LazyLock<T, F = fn() -> T> {
    once: OnceLock<T>,           // 这间房
    init: UnsafeCell<Option<F>>, // 入住手续（办完就扔掉）
}

impl<T, F: FnOnce() -> T> Deref for LazyLock<T, F> {
    type Target = T;
    fn deref(&self) -> &T {
        self.once.get_or_init(self.init.take().unwrap())
        // 房间里没人 → 执行入住手续 → 入住
        // 房间里有人 → 直接告诉房间号
    }
}
```

`OnceLock` 先稳定（1.70），`LazyLock` 后稳定（1.80）。标准库的做法相当于：先装了**手动入住系统**（前台办入住 → `OnceLock::set`），再升级到**自动入住系统**（进门自动触发 → `LazyLock`）。

选择哪一个取决于「谁控制初始化时机」：

```rust
// OnceLock：前台手动办理——初始化可能失败，可以重试
static DB: OnceLock<Database> = OnceLock::new();
fn init_db() -> Result<(), ConnectError> {
    let db = Database::connect()?;
    DB.set(db).map_err(|_| ConnectError::AlreadyInit)
    // 前台：客人到了，手动办入住。如果房间已有人，告诉前台「已经住了」
}

// LazyLock：客人进门自动触发——不需要手动办理
static DB: LazyLock<Database> = LazyLock::new(|| Database::connect().unwrap());
```

## 三个关键行为

### 1. Deref：入住后直接用房卡

```rust
use std::sync::LazyLock;

static GREETING: LazyLock<String> = LazyLock::new(|| {
    println!("正在办理入住...");
    "hello world".to_uppercase()
});

fn main() {
    println!("start");
    println!("{}", *GREETING);        // → 触发办理入住，输出 "HELLO WORLD"
    println!("{}", GREETING.len());   // → Deref 自动解引用，不再办第二次
    println!("{}", &*GREETING);       // → 拿门卡看看，也不触发
}
```

输出：

```
start
正在办理入住...
HELLO WORLD
11
HELLO WORLD
```

一旦入住办完（初始化完成），之后所有操作都不需要再去前台——`Deref` 自动帮你处理。

### 2. 线程安全：多人同时抢同一间房

```rust
use std::sync::LazyLock;
use std::{sync::Barrier, thread};

static COUNTER: LazyLock<u64> = LazyLock::new(|| {
    println!("办理入住：{:?}", thread::current().id());
    42
});

fn main() {
    let barrier = Barrier::new(3);
    thread::scope(|s| {
        for _ in 0..3 {
            s.spawn(|| {
                barrier.wait();
                println!("房间号：{}", *COUNTER);
            });
        }
    });
}
```

三个客人同时冲向前台，同时喊「我要这间房」。前台只让**一个人**办入住（`init` 只打印**一次**），其他人在门口等着。等第一个人办好，所有人拿到的都是同一个房间号。

### 3. 初始化 panic：第一个客人入住发现房间塌了

```rust
static BROKEN: LazyLock<u32> = LazyLock::new(|| panic!("房间塌了"));

// 每次访问 *BROKEN 都会重新 panic——不是只崩一次
```

这跟真实酒店一样：第一个客人办入住时发现房间塌了（panic），但酒店系统不会自动修复——它不知道是该重修还是该换房，只会机械地重试。之后每个客人去敲门，前台都会再次尝试办理入住，然后再次发现房间塌了。**永远 panic，永远好不了。**

如果你用 `OnceLock::set()`，panic 后 `set` 失败，锁保持未初始化——可以换个方案重试：

```rust
static RETRY: OnceLock<u32> = OnceLock::new();

fn try_set() -> Result<(), &'static str> {
    let val: u32 = some_fallible_op()?;
    RETRY.set(val).map_err(|_| "already set")
    // 前台：先试试这间房能不能住，不行就换一间
}
```

## 实战：编译一次 Regex（酒店会议室）

`LazyLock` 最典型的场景——编译期不可知的昂贵计算推迟到首次使用：

```rust
use regex::Regex;
use std::sync::LazyLock;

static EMAIL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap()
});

fn is_valid_email(s: &str) -> bool {
    EMAIL_RE.is_match(s)   // Regex 只编译一次
}
```

酒店有一个会议室，但不会在开业前就布置完毕——太占地方，万一没人用就白布置了。等有人第一次说「我要用会议室」时，才去摆桌椅、装投影（编译 Regex）。之后每次使用都是现成的。

## 实战：全局配置（旅游信息手册）

```rust
use std::env;
use std::sync::LazyLock;

#[derive(Debug)]
struct AppConfig {
    database_url: String,
    redis_url: String,
    port: u16,
}

static CONFIG: LazyLock<AppConfig> = LazyLock::new(|| {
    AppConfig {
        database_url: env::var("DATABASE_URL")
            .unwrap_or_else(|_| "postgres://localhost:5432/app".into()),
        redis_url: env::var("REDIS_URL")
            .unwrap_or_else(|_| "redis://localhost:6379".into()),
        port: env::var("PORT")
            .ok()
            .and_then(|p| p.parse().ok())
            .unwrap_or(8080),
    }
});

fn main() {
    // 第一次有人问「酒店有什么服务」时才去读取环境变量——不是开业时
    println!("Starting on port {}", CONFIG.port);
}
```

酒店的旅游信息手册，不是开业当天就印好的——等第一个客人问「附近有什么好玩的」时才去编印。如果根本没人问，就不浪费纸。

## 什么时候不该用 LazyLock（什么情况下不适合自动入住）

| 场景 | 解决方案 |
|---|---|
| 初始化可能失败（客人入住手续可能办不下来） | `OnceLock` + `set()` 返回 `Result`（前台手动处理异常） |
| 需要可变全局状态（客人需要调整房间设施） | `LazyLock<Mutex<T>>` 或 `std::sync::Mutex`（配一个管家） |
| 初始化需要异步操作（客人预约了网上办理） | `tokio::sync::OnceCell` / `OnceLock` + 手动管理 |
| 多个 LazyLock 有顺序依赖（A 客房要等 B 宴会厅先布置好） | 设置 `RUST_BACKTRACE=1` 检查死锁 |

## `lazy_static!` → `LazyLock` 的迁移

```rust
// 之前：外包给第三方入住系统 + 宏
lazy_static! {
    static ref DATA: Vec<String> = vec!["a".into(), "b".into()];
}

// 现在：酒店自建前台，零依赖、零宏
static DATA: LazyLock<Vec<String>> = LazyLock::new(|| vec!["a".into(), "b".into()]);
```

## 小结

`LazyLock` 是 Rust 对「全局延迟初始化」的标准答案。它替换了社区用了多年的 `lazy_static!` 和 `once_cell::sync::Lazy`，零依赖、零宏、零额外分配。

记住三点：它是 `OnceLock` + 自动办理入住 + `Deref` 刷脸进；线程安全，初始化只跑一次；初始化可能失败时换手动入住（`OnceLock`）。

**返回：** [Rust 笔记](index.md)
