# Rust LazyLock：延迟初始化的标准答案

> 基于 Rust 1.95，`std::sync::LazyLock` 自 1.80 起稳定。

## 一个你肯定写过的模式

```rust
use std::collections::HashMap;

fn get_config() -> HashMap<String, String> {
    let content = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&content).unwrap()
}

fn lookup(key: &str) -> Option<String> {
    get_config().get(key).cloned()  // 每次调用都读文件、解析——浪费
}
```

你想要的是：**第一次访问时初始化，之后直接返回缓存值。** 在 `lazy_static!` 的时代你得引入外部 crate：

```rust
use lazy_static::lazy_static;

lazy_static! {
    static ref CONFIG: HashMap<String, String> = {
        let content = std::fs::read_to_string("config.toml").unwrap();
        toml::from_str(&content).unwrap()
    };
}
```

从 Rust 1.80 开始，标准库有了自己的答案：

```rust
use std::sync::LazyLock;

static CONFIG: LazyLock<HashMap<String, String>> = LazyLock::new(|| {
    let content = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&content).unwrap()
});

fn lookup(key: &str) -> Option<String> {
    CONFIG.get(key).cloned()  // 第一次调用初始化，之后直接返回
}
```

## LazyLock 与 OnceLock 的关系

很多人把 `LazyLock` 和 `OnceLock` 当成两个东西，但 `LazyLock` 就是 `OnceLock` + 闭包 + `Deref`：

```rust
// 核心逻辑等价于：
struct LazyLock<T, F = fn() -> T> {
    once: OnceLock<T>,
    init: UnsafeCell<Option<F>>,
}

impl<T, F: FnOnce() -> T> Deref for LazyLock<T, F> {
    type Target = T;
    fn deref(&self) -> &T {
        self.once.get_or_init(self.init.take().unwrap())
    }
}
```

`OnceLock` 先稳定（1.70），`LazyLock` 后稳定（1.80）。标准库的做法是吸收 `once_cell` crate（社区用了多年的方案）的设计。

选择哪一个取决于"谁控制初始化时机"：

```rust
// OnceLock：你决定什么时候初始化——初始化可能失败时可以重试
static DB: OnceLock<Database> = OnceLock::new();
fn init_db() -> Result<(), ConnectError> {
    let db = Database::connect()?;
    DB.set(db).map_err(|_| ConnectError::AlreadyInit)
}

// LazyLock：第一次访问时自动触发——不需要手动 init
static DB: LazyLock<Database> = LazyLock::new(|| Database::connect().unwrap());
```

## 三个关键行为

### 1. Deref 让你像用普通值一样用它

```rust
use std::sync::LazyLock;

static GREETING: LazyLock<String> = LazyLock::new(|| {
    println!("正在初始化...");
    "hello world".to_uppercase()
});

fn main() {
    println!("start");
    println!("{}", *GREETING);        // → 触发初始化，输出 "HELLO WORLD"
    println!("{}", GREETING.len());   // → Deref 自动解引用，不重复初始化
    println!("{}", &*GREETING);       // → 拿引用，不触发
}
```

输出：

```
start
正在初始化...
HELLO WORLD
11
HELLO WORLD
```

### 2. 线程安全——多线程同时访问只初始化一次

```rust
use std::sync::LazyLock;
use std::{sync::Barrier, thread};

static COUNTER: LazyLock<u64> = LazyLock::new(|| {
    println!("init by: {:?}", thread::current().id());
    42
});

fn main() {
    let barrier = Barrier::new(3);
    thread::scope(|s| {
        for _ in 0..3 {
            s.spawn(|| {
                barrier.wait();
                println!("value: {}", *COUNTER);
            });
        }
    });
}
```

三个线程同时访问 `*COUNTER`，`init` 只打印**一次**。其他线程在初始化完成前阻塞。

### 3. 初始化 panic 会"毒化"——和 OnceLock 不同

```rust
static BROKEN: LazyLock<u32> = LazyLock::new(|| panic!("崩了"));

// 每次访问 *BROKEN 都会重新 panic——不是只崩一次
```

如果你用 `OnceLock::set()`，panic 后 `set` 失败，锁保持未初始化，可以重试：

```rust
static RETRY: OnceLock<u32> = OnceLock::new();

fn try_set() -> Result<(), &'static str> {
    let val: u32 = some_fallible_op()?;
    RETRY.set(val).map_err(|_| "already set")
}
```

## 实战：编译一次 Regex

`LazyLock` 最典型的场景——编译期不可知的昂贵计算推迟到首次使用：

```rust
use regex::Regex;
use std::sync::LazyLock;

static EMAIL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap()
});

fn is_valid_email(s: &str) -> bool {
    EMAIL_RE.is_match(s)   // Regex 只编译一次，后续全是廉价匹配
}
```

## 实战：全局配置

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
    // 第一次访问时才读取环境变量——不是程序启动时
    println!("Starting on port {}", CONFIG.port);
}
```

## 什么时候不该用 LazyLock

| 场景 | 解决方案 |
|---|---|
| 初始化可能失败 | `OnceLock` + `set()` 返回 `Result` |
| 需要可变全局状态 | `LazyLock<Mutex<T>>` 或使用 `std::sync::Mutex` |
| 初始化时异步操作 | `tokio::sync::OnceCell` / `OnceLock` + 手动管理 |
| 多个 LazyLock 有顺序依赖 | 设置 `RUST_BACKTRACE=1` 检查死锁 |

## `lazy_static!` → `LazyLock` 的迁移

```rust
// 之前：外部 crate + 宏
lazy_static! {
    static ref DATA: Vec<String> = vec!["a".into(), "b".into()];
}

// 现在：标准库，不需要任何依赖
static DATA: LazyLock<Vec<String>> = LazyLock::new(|| vec!["a".into(), "b".into()]);
```

## 小结

`LazyLock` 是 Rust 对"全局延迟初始化"的标准答案。它替换了社区用了多年的 `lazy_static!` 和 `once_cell::sync::Lazy`，零依赖、零宏、零额外分配。

记住三点：它是 `OnceLock` + 闭包 + `Deref`；线程安全，初始化只跑一次；初始化可能失败时换 `OnceLock`。
