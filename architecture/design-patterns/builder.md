# Builder 模式：Rust 里最自然的构造方式

> 本文基于 Rust 1.78+，涉及特性标注最低支持版本。

## 构造函数的参数地狱

配置一个 HTTP 客户端，要设置超时、重试、代理、TLS、连接池……参数多到构造函数签不下去：

```rust
struct HttpClient {
    base_url: String,
    timeout: Duration,
    max_retries: u32,
    proxy: Option<String>,
    tls_verify: bool,
    pool_size: usize,
}

// 调用者必须记住每个参数的顺序，可选参数也得传 None
let client = HttpClient::new(
    "https://api.example.com".to_string(),
    Duration::from_secs(30),
    3,
    None,
    true,
    10,
);
```

在 Python 里你可以用默认参数：`def __init__(self, base_url, timeout=30, max_retries=3, ...)`,在 Java 里你可以重载多个构造函数。但 Rust 两者都没有——没有默认参数，没有构造函数重载，没有函数可选参数。

Rust 社区的答案只有一个：**Builder 模式**。

## 基础 Builder

```rust
#[derive(Debug)]
struct HttpClient {
    base_url: String,
    timeout: Duration,
    max_retries: u32,
    proxy: Option<String>,
    tls_verify: bool,
    pool_size: usize,
}

struct HttpClientBuilder {
    base_url: String,
    timeout: Option<Duration>,
    max_retries: Option<u32>,
    proxy: Option<String>,
    tls_verify: Option<bool>,
    pool_size: Option<usize>,
}

impl HttpClientBuilder {
    fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            timeout: None,
            max_retries: None,
            proxy: None,
            tls_verify: None,
            pool_size: None,
        }
    }

    fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    fn max_retries(mut self, retries: u32) -> Self {
        self.max_retries = Some(retries);
        self
    }

    fn proxy(mut self, proxy: impl Into<String>) -> Self {
        self.proxy = Some(proxy.into());
        self
    }

    fn tls_verify(mut self, verify: bool) -> Self {
        self.tls_verify = Some(verify);
        self
    }

    fn pool_size(mut self, size: usize) -> Self {
        self.pool_size = Some(size);
        self
    }

    fn build(self) -> HttpClient {
        HttpClient {
            base_url: self.base_url,
            timeout: self.timeout.unwrap_or(Duration::from_secs(30)),
            max_retries: self.max_retries.unwrap_or(3),
            proxy: self.proxy,
            tls_verify: self.tls_verify.unwrap_or(true),
            pool_size: self.pool_size.unwrap_or(10),
        }
    }
}

// 使用——只设置关心的参数
let client = HttpClientBuilder::new("https://api.example.com")
    .timeout(Duration::from_secs(60))
    .max_retries(5)
    .build();

println!("{client:?}");
// HttpClient { base_url: "https://api.example.com", timeout: 60s, max_retries: 5, proxy: None, tls_verify: true, pool_size: 10 }
```

调用方只写需要的参数，其余用默认值。`HttpClient` 本身不需要知道默认值是什么——默认值集中在 `build()` 里。

## `build(self)` 而不是 `build(&self)`

注意 `build` 的签名：`fn build(self)`——它消费 builder，不是借用。

```rust
let builder = HttpClientBuilder::new("https://api.example.com");
let client1 = builder.build();  // builder 被 move 了
let client2 = builder.build();  // ❌ 编译错误：builder 已被移动
```

这不是 bug，这是设计。如果 `build` 借用 builder，你可以反复调用 `build()` 创建多个实例——但 builder 里可能有只初始化了一半的字段，两次 build 的结果可能不一致。**消费 builder 是 Rust 给你的编译期保证：一个 builder 只能产出一次结果。**

## Type State：让编译器替你检查必填字段

基础 Builder 有一个问题：`base_url` 是必填的，但如果有人忘了设呢？

```rust
let client = HttpClientBuilder::new(/* 忘了传 base_url */)
    .timeout(Duration::from_secs(60))
    .build();  // unwrap_or 给了默认值——但 base_url 不该有默认值
```

更严重的场景：`Server` 必须绑定端口，忘了设端口不应该编译通过。Rust 用 **type state 模式**解决这个问题——让 builder 的类型编码它的状态：

```rust
use std::marker::PhantomData;

// 状态标记——空结构体，编译期消除，零运行时开销
struct NoPort;
struct HasPort;

#[derive(Debug)]
struct Server {
    host: String,
    port: u16,
    workers: usize,
}

// Builder 的泛型参数 P 编码"端口有没有设"
struct ServerBuilder<P = NoPort> {
    host: String,
    port: Option<u16>,
    workers: usize,
    _state: PhantomData<P>,  // 编译期标记，不占空间
}

impl ServerBuilder<NoPort> {
    fn new(host: impl Into<String>) -> Self {
        Self {
            host: host.into(),
            port: None,
            workers: 4,
            _state: PhantomData,
        }
    }

    // 设了端口之后，类型从 NoPort 变成 HasPort
    fn port(self, port: u16) -> ServerBuilder<HasPort> {
        ServerBuilder {
            host: self.host,
            port: Some(port),
            workers: self.workers,
            _state: PhantomData,
        }
    }
}

impl ServerBuilder<HasPort> {
    fn workers(mut self, workers: usize) -> Self {
        self.workers = workers;
        self
    }

    fn build(self) -> Server {
        Server {
            host: self.host,
            port: self.port.unwrap(),  // 安全：只有 HasPort 能调用 build
            workers: self.workers,
        }
    }
}

// ✅ 正确：设了端口才能 build
let server = ServerBuilder::new("0.0.0.0")
    .port(8080)
    .workers(8)
    .build();

// ❌ 编译错误：NoPort 没有 build 方法
// let broken = ServerBuilder::new("0.0.0.0").build();
// error[E0599]: no method named `build` found for `ServerBuilder<NoPort>`
```

```mermaid
stateDiagram-v2
    [*] --> NoPort: ServerBuilder::new()
    NoPort --> HasPort: .port(8080)
    HasPort --> HasPort: .workers(8)
    HasPort --> Server: .build()
    NoPort --> Server: ✗ 编译错误
```

**编译器成了你的代码审查员**——忘设端口不是运行时 panic，而是编译不过。`PhantomData` 不占任何运行时空间，这些类型标记在编译后全部擦除。

## 实战：HTTP 客户端配置

把 type state 应用到之前的 `HttpClient`，让 `base_url` 在编译期强制必填：

```rust
use std::marker::PhantomData;
use std::time::Duration;

struct NoUrl;
struct HasUrl;

#[derive(Debug)]
struct HttpClient {
    base_url: String,
    timeout: Duration,
    max_retries: u32,
    proxy: Option<String>,
    tls_verify: bool,
}

struct HttpClientBuilder<U = NoUrl> {
    base_url: Option<String>,
    timeout: Duration,
    max_retries: u32,
    proxy: Option<String>,
    tls_verify: bool,
    _state: PhantomData<U>,
}

// 起始状态：没有 URL
impl HttpClientBuilder<NoUrl> {
    pub fn new() -> Self {
        Self {
            base_url: None,
            timeout: Duration::from_secs(30),
            max_retries: 3,
            proxy: None,
            tls_verify: true,
            _state: PhantomData,
        }
    }

    /// 设置基础 URL——必须调用，否则无法 build
    pub fn base_url(self, url: impl Into<String>) -> HttpClientBuilder<HasUrl> {
        HttpClientBuilder {
            base_url: Some(url.into()),
            timeout: self.timeout,
            max_retries: self.max_retries,
            proxy: self.proxy,
            tls_verify: self.tls_verify,
            _state: PhantomData,
        }
    }
}

// URL 已设置：可以继续配置，也可以 build
impl HttpClientBuilder<HasUrl> {
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn max_retries(mut self, retries: u32) -> Self {
        self.max_retries = retries;
        self
    }

    pub fn proxy(mut self, proxy: impl Into<String>) -> Self {
        self.proxy = Some(proxy.into());
        self
    }

    pub fn tls_verify(mut self, verify: bool) -> Self {
        self.tls_verify = verify;
        self
    }

    pub fn build(self) -> HttpClient {
        HttpClient {
            base_url: self.base_url.unwrap(),
            timeout: self.timeout,
            max_retries: self.max_retries,
            proxy: self.proxy,
            tls_verify: self.tls_verify,
        }
    }
}

// 使用
let client = HttpClientBuilder::new()
    .base_url("https://api.example.com")
    .timeout(Duration::from_secs(60))
    .proxy("http://proxy.internal:3128")
    .build();

// 忘设 base_url → 编译错误
// let broken = HttpClientBuilder::new().build();
```

## 和 Python / Java Builder 的对比

| | Python | Java | Rust |
|---|---|---|---|
| 默认参数 | ✅ 原生支持 | ❌ | ❌ 用 Builder 替代 |
| 忘设必填参数 | 运行时 TypeError | 运行时异常 / null | **编译错误** |
| Builder 可复用 | 可以 | 可以 | 不行（`build(self)` 消费） |
| 类型状态 | 不可能 | 需要泛型（笨重） | 惯用法，零开销 |
| 链式调用 | 需要返回 self | 需要返回 this | `self` 所有权天然支持 |

Python 不需要 Builder——有默认参数和关键字参数就够了。Java 的 Builder 主要是解决"可选参数太多"的问题，但防不了"忘设必填参数"。**Rust 的 Builder 不只是语法糖，而是利用类型系统把"调用顺序正确"变成了编译期不变量。**

## 小结

Builder 在 Rust 里不是"可选的设计模式"——它是 Rust 没有"默认参数"之后的必然选择，也是社区最广泛使用的构造方式。它的三层递进：

1. **基础 Builder**：解决参数太多、可选参数的问题
2. **`build(self)` 消费**：防止 builder 被重复使用，一次构建一次消费
3. **Type State**：编译期强制必填字段，把"忘设参数"从运行时错误变成编译错误

标准库里随处可见——`std::thread::Builder`、`std::process::Command`、`std::fs::OpenOptions`——都是 Builder。当你发现构造函数的参数超过 3 个，或者有必填/可选的区分，Builder 就是 Rust 的答案。
