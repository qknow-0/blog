# Adapter 模式：newtype 模式 + trait 实现

> 本文基于 Rust 1.95。

## 不用 Adapter 的问题

你写了一个应用，定义了自己的日志接口：

```rust
trait Logger {
    fn info(&self, msg: &str);
    fn error(&self, msg: &str);
    fn warn(&self, msg: &str);
}
```

但团队决定用第三方日志库——比如 `slog` 或 `tracing`——它们的 API 长这样：

```rust
// 来自 third_party_log crate，你改不了它
impl ThirdPartyLogger {
    pub fn log(&self, level: LogLevel, message: &str) { /* ... */ }
}
```

你当然想直接 `impl Logger for ThirdPartyLogger`——但编译器不同意：

```rust
// ❌ 编译错误：孤儿规则！
// impl Logger for ThirdPartyLogger { }
// error[E0117]: only traits defined in the current crate
// can be implemented for arbitrary types
```

**孤儿规则（Orphan Rule）** 说：只有当 trait 或类型至少有一个在当前 crate 里定义时，才能写 impl。`Logger` 和 `ThirdPartyLogger` 都是外部的，这条路走不通。

你也不能把所有 `ThirdPartyLogger::log` 调用改成你的 `Logger` 方法——已经写到一半的代码到处都在用 `info!`、`error!` 宏。改接口意味着改调用方。

Adapter 模式解决的就是这个问题：**在不改 Adaptee 代码的前提下，让 Adaptee 的接口符合调用方的期望**。

## GoF 定义

```text
Adapter：
  将一个类的接口转换成客户期望的另一个接口。
  适配器让那些接口不兼容的类可以一起工作。

               ┌──────────────┐
               │   Client     │
               │ 期待 Target  │  ← 你的应用代码，调 Logger trait
               └──────┬───────┘
                      │
               ┌──────┴───────┐
               │   Target     │  ← Logger trait
               │ + info()     │
               │ + error()    │
               └──────┬───────┘
                      │
               ┌──────┴───────┐
               │   Adapter    │  ← LoggerAdapter
               │ + info()     │
               │ + error()    │  将 info/error 翻译为 .log(level, msg)
               └──────┬───────┘
                      │
               ┌──────┴───────┐
               │   Adaptee    │  ← ThirdPartyLogger
               │ + log()      │
               └──────────────┘
```

Client 持有 Target 的引用，Adapter 实现了 Target，Adapter 内部持有 Adaptee 并把 Target 方法的调用翻译成 Adaptee 的方法调用。

## Rust 版：newtype 模式 + trait 实现

Rust 的解答是 **newtype 模式**——用一个单字段元组结构体包裹第三方类型，然后为这个新类型实现目标 trait：

```rust
// 目标接口——你的应用需要的日志接口
trait Logger {
    fn info(&self, msg: &str);
    fn error(&self, msg: &str);
    fn warn(&self, msg: &str);
}

// 第三方日志库——你改不了的代码
struct ThirdPartyLogger {
    name: String,
}

impl ThirdPartyLogger {
    fn log(&self, level: u8, message: &str) {
        println!("[{}] level={}: {}", self.name, level, message);
    }
}

// ✅ Adapter: newtype 模式
// LoggerAdapter 是你定义的 → 你可以为它实现任何 trait
struct LoggerAdapter(ThirdPartyLogger);

impl Logger for LoggerAdapter {
    fn info(&self, msg: &str) {
        self.0.log(0, msg);  // 翻译：info 调用 level=0 的 log
    }
    fn error(&self, msg: &str) {
        self.0.log(1, msg);  // 翻译：error 调用 level=1 的 log
    }
    fn warn(&self, msg: &str) {
        self.0.log(2, msg);  // 翻译：warn 调用 level=2 的 log
    }
}
```

关键的两步：

1. `struct LoggerAdapter(ThirdPartyLogger);`——创建 newtype 包装
2. `impl Logger for LoggerAdapter { ... }`——为目标 trait 实现 Adapter

**这两步加在一起，就是 GoF 的 Object Adapter 在 Rust 里的等价实现**。Adapter 持有 Adaptee 的引用（`self.0`），并把 Target 的每个方法调用翻译成 Adaptee 的方法调用。

### 为什么需要 newtype：孤儿规则

更深层的问题是：**Rust 的孤儿规则（coherence）为什么存在？**

```text
孤儿规则（Orphan Rule）：
  你不能为外部类型实现外部 trait。
  只有 trait 或类型至少有一个在当前 crate 定义时，才能 impl。

为什么要有这个规则？
  - 两个 crate 都为同一个外部类型实现了同一个外部 trait → 歧义
  - 包管理没法判断哪个 impl 应该生效
  - 所以编译器强制：你至少要「拥有」trait 或者类型中的一个

怎么绕过？
  - newtype 模式：你定义了 LoggerAdapter → 你可以为它实现任何 trait
  - impl Logger for LoggerAdapter 是合法的
  - 然后通过 self.0 委托给内部的 ThirdPartyLogger
```

这不是 Rust 的限制，而是 Rust 的**设计选择**——用编译期的规则保证 impl 的唯一性，避免像 C++ 那样出现「谁先 include 谁生效」的隐式行为。

## 两种形式：Object Adapter vs Class Adapter

GoF 定义了两种 Adapter：

```text
Object Adapter（组合）：
  适配器持有 Adaptee 的实例，通过委托调用
  → Rust 有：newtype 模式就是组合

Class Adapter（继承）：
  适配器继承 Adaptee 的子类，同时实现 Target 接口
  → Rust 没有继承，这条路走不通
```

Rust 只有 Object Adapter 这一种形式——因为 Rust 没有类继承。但如果你需要一个适配多种 Adaptee 的通用适配器，可以用泛型：

```rust
// 泛型适配器——有点像「类适配器」的思路
struct GenericLoggerAdapter<L> {
    inner: L,
}

impl<L> Logger for GenericLoggerAdapter<L>
where
    L: HasLogMethod,  // 约束：任何有 log() 方法的类型
{
    fn info(&self, msg: &str) {
        self.inner.log(0, msg);
    }
    fn error(&self, msg: &str) {
        self.inner.log(1, msg);
    }
    fn warn(&self, msg: &str) {
        self.inner.log(2, msg);
    }
}
```

不过泛型 Adapter 在 Rust 实践中并不常见——更普遍的做法是直接为一个具体的新类型实现 trait。

## From / Into：自带转换的 Adapter

Adapter 不只是传递方法调用，还可以实现类型转换：

```rust
// 从 ThirdPartyLogger 无缝构造 LoggerAdapter
impl From<ThirdPartyLogger> for LoggerAdapter {
    fn from(logger: ThirdPartyLogger) -> Self {
        LoggerAdapter(logger)
    }
}

// 使用——直接 .into() 转换
fn setup_logger(logger: impl Into<LoggerAdapter>) {
    let adapter: LoggerAdapter = logger.into();
    // ...
}

let third = ThirdPartyLogger { name: "prod".into() };
setup_logger(third);  // ✅ 自动调用 From
```

`From` impl 让 Adapter 的创建变得透明——调用方不需要关心 newtype 的存在，`into()` 是零开销的。

## 实例：HTTP 客户端适配

更真实的场景——你的应用需要统一的 HTTP 接口：

```rust
use std::error::Error;

// 你的应用定义的 HTTP 接口
trait HttpClient {
    fn get(&self, url: &str) -> Result<String, Box<dyn Error>>;
}

// 假设使用 reqwest——但你的接口和 reqwest::Client 的 API 不一样
// reqwest::Client 的调用方式是 .get(url).send().await?.text().await?
// 你的接口只用 .get(url) 返回 String

struct ReqwestAdapter {
    client: reqwest::blocking::Client,
}

impl HttpClient for ReqwestAdapter {
    fn get(&self, url: &str) -> Result<String, Box<dyn Error>> {
        let resp = self.client.get(url).send()?;
        let body = resp.text()?;
        Ok(body)
    }
}

// 也可以适配其他 HTTP 库
struct UreqAdapter {
    agent: ureq::Agent,
}

impl HttpClient for UreqAdapter {
    fn get(&self, url: &str) -> Result<String, Box<dyn Error>> {
        let resp = self.agent.get(url).call()?;
        Ok(resp.into_string()?)
    }
}
```

Adapter 让整个应用只依赖 `HttpClient` trait。今天用 reqwest，明天换 ureq——只需要换一个 Adapter，应用代码一行不改。

## Deref 委托：省掉重复的方法转发

如果 Adaptee 有一些方法你不想隐藏，可以用 `Deref` 把方法调用自动委托过去：

```rust
use std::ops::Deref;

impl Deref for LoggerAdapter {
    type Target = ThirdPartyLogger;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

// 现在 LoggerAdapter 也能直接调用 ThirdPartyLogger 的方法了
let adapter = LoggerAdapter(ThirdPartyLogger { name: "dev".into() });
adapter.log(0, "这是 ThirdPartyLogger 的原生方法");
//        ^ 通过 Deref 自动解引用调用
```

但 `Deref` 滥用是个常见的 Rust anti-pattern。`Deref` 的本意是让智能指针（`Box<T>`、`Arc<T>`）能透明地像内部类型一样使用——不是为 Adapter 设计的。

```text
⚠️ Deref 做适配的陷阱：
  - Deref 会模糊类型边界——调用方不知道自己在用 LoggerAdapter 还是 ThirdPartyLogger
  - 如果后续 ThirdPartyLogger 增加了一个同名方法，Deref 可能引入意外的行为覆盖
  - 推荐：只在「Adapter 是 Adaptee 的真实增强」时才用 Deref
  - 单纯的「接口翻译」场景——不用 Deref，显式转发每个方法
```

大多数 Adapter 不需要 Deref。显式转发虽然多写几行，但每个方法的行为都明确声明了。

## 函数适配：轻量级方案

不是每个接口不匹配都需要 newtype。有时一个函数或闭包就够了：

```rust
// Adaptee 的函数签名
fn third_party_log(level: u8, msg: &str) { /* ... */ }

// 你的 Logger trait 需要一个 &self 方法——但你可能只是简单的日志输出
// 一个闭包包装就够了
fn make_logger() -> impl Fn(&str) {
    |msg| third_party_log(0, msg)
}

// 甚至直接传函数指针
fn info_adapter(msg: &str) {
    third_party_log(0, msg);
}
fn error_adapter(msg: &str) {
    third_party_log(1, msg);
}
```

什么时候用函数适配：

```text
函数适配：   接口差异就是「少几个参数 / 参数顺序不同」
newtype 适配：接口差异涉及状态、生命周期、错误类型转换
```

## Adapter vs Decorator vs Facade

这三个模式都涉及「包装」，但意图完全不同：

| 模式 | 意图 | Rust 表达 | 类比 |
|------|------|-----------|------|
| **Adapter** | 接口转换——让 A 能用 B | newtype + trait impl | 电源转换插头 |
| **Decorator** | 接口增强——在 A 上加功能 | trait 包装 + 方法委托 + 额外逻辑 | 给手机加手机壳 |
| **Facade** | 接口简化——把多个 B 揉成一个界面 | 模块级 `pub` 函数 + 内部类型隐藏 | 遥控器（隐藏内部电路） |

Rust 里的实际区别：

```rust
// Adapter: 翻译接口，不改行为
struct LoggerAdapter(ThirdPartyLogger);
impl Logger for LoggerAdapter {
    fn info(&self, msg: &str) {
        self.0.log(0, msg);  // 只是翻译，不加行为
    }
}

// Decorator: 增强行为——加缓存、加重试、加指标
struct CachingHttpClient<C: HttpClient> {
    inner: C,
    cache: HashMap<String, String>,
}
impl<C: HttpClient> HttpClient for CachingHttpClient<C> {
    fn get(&self, url: &str) -> Result<String, Box<dyn Error>> {
        if let Some(cached) = self.cache.get(url) {
            return Ok(cached.clone());
        }
        let result = self.inner.get(url)?;  // 委托 + 增强
        // ... 写入缓存
        Ok(result)
    }
}

// Facade: 隐藏多个子系统的复杂性
// 不需要 newtype——用 pub(crate) 控制可见性就够了
mod sms {
    pub fn send(phone: &str, msg: &str) -> Result<(), Error> {
        let client = get_client()?;
        let formatted = format_message(msg);
        client.deliver(phone, &formatted)
    }
    // 内部细节完全隐藏
    fn get_client() -> Result<InternalClient, Error> { /* ... */ }
    fn format_message(msg: &str) -> String { /* ... */ }
}
```

## 什么时候用，什么时候不用

**用 Adapter**：
- 第三方库的接口和你需要的接口不匹配，而且你改不了第三方代码
- 孤儿规则阻止你直接 `impl Target for ThirdPartyType`
- 你在多处使用同一个不兼容接口，需要统一适配——避免重复写转换代码
- 需要在多个第三方实现之间切换（比如你能换日志库、换 HTTP 库）

**不用 Adapter**：
- 你能直接改源码——加一个 `impl Target for Self` 就够了
- 接口差异很小——一个函数或闭包就能解决
- 你需要的是功能增强而不是接口翻译——那是 Decorator 的职责
- 你需要的是一组子系统的简化接口——那是 Facade 的职责
- 只有一个使用点——在调用处直接转换比引入新类型更简单

## 小结

- Adapter 解决的是 **「代码已经有现成的，但接口不对，又改不了」** 的问题
- Rust 的实现 = **newtype 模式 + trait 实现**
- **孤儿规则（coherence）** 是为什么你需要 newtype 的根本原因——编译器强制 impl 唯一性，newtype 创建了你「拥有」的类型
- Rust 只有 **Object Adapter（组合）** 形式——没有类继承，也就没有 Class Adapter
- `From`/`Into` impl 让 Adapter 的创建更自然、零开销
- `Deref` 能减少重复代码，但容易模糊类型边界——显式转发通常是更好的选择
- 不是每个接口不匹配都需要完整的 newtype——函数适配（闭包、函数指针）是更轻量的选择
- Adapter 和 Decorator、Facade 在 Rust 里有清晰的区分：**翻译 vs 增强 vs 聚合**

```text
Adapter = newtype + trait impl
        = Rust 对「不兼容接口」的编译期安全回答
```

---

**上一篇：** [Prototype 模式](prototype.md)
**返回：** [设计模式：Rust 视角](index.md)
