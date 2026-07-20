# Decorator 模式：给对象穿衣服——Rust 的 trait 组合与 `impl Trait`

> 基于 Rust 1.96。`impl Trait` 返回值自 1.26 稳定。

## 一个问题：怎么给一个功能"层层加码"

你有一个数据读取器，从文件读数据。后来你需要加缓存、加日志、加限流。最直接的做法——在 `read()` 方法里塞 if-else：

```rust
fn read(&self, key: &str) -> Option<String> {
    // 先查缓存
    if let Some(v) = self.cache.get(key) { return Some(v); }
    // 从文件读
    let v = self.file.read(key)?;
    // 记日志
    log::info!("read: {} -> {}", key, v);
    // 写缓存
    self.cache.set(key, &v);
    Some(v)
}
```

加了三个功能，`read()` 变成了一个大杂烩。再加一个限流？再来一个压缩？代码堆成山。Decorator 模式要解决的就是这个问题——**把每个附加功能变成独立的一层，像穿衣服一样套在原来的对象外面**。

```mermaid
flowchart LR
    CLIENT["调用方"] --> DECO3["限流层<br/>(最外层)"]
    DECO3 --> DECO2["日志层"]
    DECO2 --> DECO1["缓存层"]
    DECO1 --> CORE["文件读取器<br/>(核心)"]
```

## GoF 经典写法：trait + 组合

先定义核心 trait：

```rust
trait DataSource {
    fn read(&mut self, key: &str) -> Option<String>;
    fn write(&mut self, key: &str, value: &str);
}

// 核心实现：文件读取
struct FileSource {
    path: String,
}

impl DataSource for FileSource {
    fn read(&mut self, key: &str) -> Option<String> {
        std::fs::read_to_string(format!("{}/{}.txt", self.path, key)).ok()
    }
    fn write(&mut self, key: &str, value: &str) {
        let _ = std::fs::write(format!("{}/{}.txt", self.path, key), value);
    }
}
```

然后每层装饰器都**实现同一个 trait，并把调用转发给内层**：

```rust
// 缓存层——穿在文件外面
struct CacheDecorator<D: DataSource> {
    inner: D,
    cache: std::collections::HashMap<String, Option<String>>,
}

impl<D: DataSource> CacheDecorator<D> {
    fn new(inner: D) -> Self {
        Self { inner, cache: std::collections::HashMap::new() }
    }
}

impl<D: DataSource> DataSource for CacheDecorator<D> {
    fn read(&mut self, key: &str) -> Option<String> {
        // 先查缓存
        if let Some(v) = self.cache.get(key) {
            println!("[cache] hit: {}", key);
            return v.clone();
        }
        // 缓存没有 → 问内层
        let v = self.inner.read(key);
        self.cache.insert(key.to_string(), v.clone());
        println!("[cache] miss: {}", key);
        v
    }
    fn write(&mut self, key: &str, value: &str) {
        self.cache.insert(key.to_string(), Some(value.to_string()));
        self.inner.write(key, value);  // 写穿透
    }
}
```

日志层——同样的模式：

```rust
struct LogDecorator<D: DataSource> {
    inner: D,
}

impl<D: DataSource> DataSource for LogDecorator<D> {
    fn read(&mut self, key: &str) -> Option<String> {
        let start = std::time::Instant::now();
        let result = self.inner.read(key);
        println!("[log] read({}) -> {:?} ({:?})", key, result.is_some(), start.elapsed());
        result
    }
    fn write(&mut self, key: &str, value: &str) {
        println!("[log] write({}, {} chars)", key, value.len());
        self.inner.write(key, value);
    }
}
```

使用起来就是**层层嵌套**：

```rust
fn main() {
    // 文件 → 缓存 → 日志 → 限流，想怎么套怎么套
    let source = FileSource { path: "/data".into() };
    let cached = CacheDecorator::new(source);
    let mut logged = LogDecorator::new(cached);

    let _ = logged.read("user_123");  // 第一次：穿透缓存、记日志
    let _ = logged.read("user_123");  // 第二次：命中缓存、记日志
    // 输出：
    // [log] read(user_123) -> true (2.3ms)
    // [cache] miss: user_123
    // [log] read(user_123) -> true (0.1ms)
    // [cache] hit: user_123
}
```

核心规则：**每个 Decorator 实现同一个 trait，持有内层对象的引用，在转发前后加入自己的逻辑**。

## Rust 的两种实现方式

### 方式一：泛型 `T: Trait`（静态分发）

```rust
struct CacheDecorator<D: DataSource> { inner: D }
```

编译期就知道 `D` 的具体类型。每层嵌套生成一个新的具体类型——零虚表开销，但类型名会变长：

```
LogDecorator<CacheDecorator<FileSource>>
```

### 方式二：`Box<dyn Trait>`（动态分发）

```rust
struct CacheDecorator { inner: Box<dyn DataSource> }
```

运行时才知道内层是什么类型。有微小的虚表开销，但可以**在运行时动态组合装饰器**：

```rust
fn build_pipeline(enable_cache: bool, enable_log: bool) -> Box<dyn DataSource> {
    let mut source: Box<dyn DataSource> = Box::new(FileSource { path: "/data".into() });
    if enable_cache {
        source = Box::new(CacheDecorator { inner: source });
    }
    if enable_log {
        source = Box::new(LogDecorator { inner: source });
    }
    source  // 运行时决定的装饰器链条
}
```

### 选择标准

| | `T: Trait` | `Box<dyn Trait>` |
|---|---|---|
| 组合时机 | 编译期 | 运行时 |
| 性能 | 零开销 | 虚表查找 |
| 类型约束 | 每层有独立类型 | 统一 `Box<dyn Trait>` |
| 适用场景 | 固定 pipeline | 动态配置 |

## 和 Python 装饰器的对比

Python 的装饰器是**语法糖**——`@cache` 等价于 `fn = cache(fn)`，本质是**函数级别的包装**：

```python
@log
@cache
def read(key: str) -> str | None:
    return file_source.read(key)

# 等价于：read = log(cache(file_source.read))
```

Rust 的 Decorator 是**类型级别的包装**——`LogDecorator<CacheDecorator<FileSource>>` 是一个**新的类型**，编译器检查所有层的类型安全。Python 的装饰器链在运行时出错（比如 `@cache` 返回了 `int` 而不是 `str`），Rust 的Decorator 在编译期就会发现 `DataSource` trait 没实现。

## 实战：给 HTTP 客户端加重试 + 超时

```rust
use std::time::Duration;

trait HttpClient {
    fn get(&mut self, url: &str) -> Result<String, String>;
}

struct ReqwestClient;
impl HttpClient for ReqwestClient {
    fn get(&mut self, url: &str) -> Result<String, String> {
        reqwest::blocking::get(url)
            .map_err(|e| e.to_string())?
            .text()
            .map_err(|e| e.to_string())
    }
}

// 重试装饰器
struct RetryDecorator<C: HttpClient> {
    inner: C,
    max_retries: usize,
}

impl<C: HttpClient> HttpClient for RetryDecorator<C> {
    fn get(&mut self, url: &str) -> Result<String, String> {
        let mut last_err = String::new();
        for attempt in 1..=self.max_retries {
            match self.inner.get(url) {
                ok @ Ok(_) => return ok,
                Err(e) => {
                    println!("[retry] attempt {}/{}: {}", attempt, self.max_retries, e);
                    last_err = e;
                    std::thread::sleep(Duration::from_millis(100 * attempt as u64));
                }
            }
        }
        Err(format!("all {} retries failed: {}", self.max_retries, last_err))
    }
}

// 超时装饰器
struct TimeoutDecorator<C: HttpClient> {
    inner: C,
    timeout: Duration,
}

impl<C: HttpClient> HttpClient for TimeoutDecorator<C> {
    fn get(&mut self, url: &str) -> Result<String, String> {
        std::thread::spawn(move || {
            // 在另一个线程执行请求
        });
        todo!("实际实现用 tokio::time::timeout 更合适")
    }
}

// 自由组合
fn main() {
    let client = ReqwestClient;
    let client = RetryDecorator { inner: client, max_retries: 3 };
    let mut client = TimeoutDecorator { inner: client, timeout: Duration::from_secs(5) };
    // 类型：TimeoutDecorator<RetryDecorator<ReqwestClient>>
    let _ = client.get("https://api.example.com");
}
```

后来想加一个"把结果缓存到本地"的 `CacheDecorator`？在外面再套一层就行——不用改 `RetryDecorator` 和 `TimeoutDecorator` 的任何代码。

## 什么时候不该用 Decorator

```rust
// ❌ 过度装饰——一个功能只用了 2 行，没必要拆成独立 struct
struct TrimDecorator<S: DataSource> { inner: S }
impl<S: DataSource> DataSource for TrimDecorator<S> {
    fn read(&mut self, key: &str) -> Option<String> {
        self.inner.read(key).map(|s| s.trim().to_string())
    }
}
// → 这种简单的转换用普通的函数就行

// ❌ 装饰器之间有时序依赖——缓存必须在日志之前？
// → 如果需要保证顺序，用 Builder 模式明确链条
```

## 小结

Decorator 在 Rust 里的两种实现对应两个权衡：

| 方式 | 代价 | 收益 |
|---|---|---|
| `T: Trait` 泛型 | 类型名变长、不能运行时切换 | **零开销**、编译期安全 |
| `Box<dyn Trait>` | 虚表查找、需要堆分配 | **运行时组合**、统一类型 |
| Python 装饰器 | 无类型检查 | 语法极简 |

Rust 版本的 Decorator 不只是"把功能拆分"——它把**类型安全带入了装饰器链**。`TimeoutDecorator<RetryDecorator<ReqwestClient>>` 是编译器确认过的组合，不是运行时的隐式调用链。这是 Python 装饰器做不到的。
