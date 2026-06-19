# Abstract Factory 模式：用 trait 组合表达产品族

> 本文基于 Rust 1.95。

## Factory Method 解决不了的问题

Factory Method 让你能创建「一个产品」。但真实场景往往是**一组相关产品**。

你对接了三家短信供应商——阿里云、腾讯云、华为云。每家提供两个产品：

```text
阿里云:   短信客户端 + 发送报告解析器
腾讯云:   短信客户端 + 发送报告解析器
华为云:   短信客户端 + 发送报告解析器
```

用 Factory Method 的写法：

```rust
// ❌ 可以工作——但你保证不了阿里云的 Client 配了腾讯云的 Parser
let client = AliyunFactory::create_client()?;
let parser = TencentFactory::create_parser()?;  // ← 编译器不管，运行期才发现不匹配
```

Abstract Factory 解决的就是这个问题：**确保一个工厂产出的所有产品来自同一个产品族**。

## GoF 定义

```text
Abstract Factory：
  提供一个接口来创建一组相关或相互依赖的对象，而无需指定其具体类。

        ┌──────────────────────┐
        │    SmsFactory        │  ← 抽象工厂
        │ + create_client()    │
        │ + create_parser()    │
        └──────────┬───────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────┴────┐  ┌────┴────┐  ┌────┴────┐
│ Aliyun  │  │ Tencent │  │ Huawei  │
│ Factory │  │ Factory │  │ Factory │
└─────────┘  └─────────┘  └─────────┘
```

## Rust 版：trait 组合

```rust
// 产品 A——短信客户端
trait SmsClient {
    fn send(&self, phone: &str, content: &str) -> Result<String, String>;
}

// 产品 B——发送报告解析器
trait ReportParser {
    fn parse(&self, raw: &str) -> Result<SendReport, String>;
}

#[derive(Debug)]
struct SendReport {
    success: bool,
    message_id: String,
    fee: f64,
}

// 抽象工厂——一个 trait 里定义创建多个相关产品的方法
trait SmsFactory {
    type Client: SmsClient;    // ← 关联类型保证：这个工厂的 Client
    type Parser: ReportParser; //   和这个工厂的 Parser 来自同一套实现

    fn create_client(&self) -> Self::Client;
    fn create_parser(&self) -> Self::Parser;
}
```

关键：**两个关联类型在同一个 trait 里**。你没法「从这个工厂拿 Client、从那个工厂拿 Parser」——类型系统不让你混。

## 三家供应商的实现

```rust
// ═══════════ 阿里云 ═══════════
struct AliyunClient { access_key: String }
impl SmsClient for AliyunClient {
    fn send(&self, phone: &str, content: &str) -> Result<String, String> {
        Ok(format!("aliyun_msg_id_{}", phone))
    }
}

struct AliyunParser;
impl ReportParser for AliyunParser {
    fn parse(&self, raw: &str) -> Result<SendReport, String> {
        Ok(SendReport { success: true, message_id: raw.into(), fee: 0.045 })
    }
}

struct AliyunFactory { access_key: String }
impl SmsFactory for AliyunFactory {
    type Client = AliyunClient;   // ← 编译器：AliyunFactory 的 Client 是 AliyunClient
    type Parser = AliyunParser;   // ← 编译器：AliyunFactory 的 Parser 是 AliyunParser

    fn create_client(&self) -> Self::Client {
        AliyunClient { access_key: self.access_key.clone() }
    }
    fn create_parser(&self) -> Self::Parser {
        AliyunParser
    }
}

// ═══════════ 腾讯云 ═══════════
struct TencentClient { secret_id: String }
impl SmsClient for TencentClient {
    fn send(&self, phone: &str, content: &str) -> Result<String, String> {
        Ok(format!("tencent_sid_{}", phone))
    }
}

struct TencentParser;
impl ReportParser for TencentParser {
    fn parse(&self, raw: &str) -> Result<SendReport, String> {
        Ok(SendReport { success: true, message_id: raw.into(), fee: 0.038 })
    }
}

struct TencentFactory { secret_id: String }
impl SmsFactory for TencentFactory {
    type Client = TencentClient;
    type Parser = TencentParser;

    fn create_client(&self) -> Self::Client {
        TencentClient { secret_id: self.secret_id.clone() }
    }
    fn create_parser(&self) -> Self::Parser {
        TencentParser
    }
}
```

## 用法——泛型约束保证家族一致性

```rust
// process_batch 只知道「这是一个 SmsFactory」——不关心具体是阿里还是腾讯
fn process_batch<F: SmsFactory>(factory: &F, phones: &[&str], content: &str) -> Vec<SendReport> {
    let client = factory.create_client();
    let parser = factory.create_parser();

    phones.iter().map(|phone| {
        let raw = client.send(phone, content).unwrap();
        parser.parse(&raw).unwrap()
    }).collect()
}

fn main() {
    let aliyun = AliyunFactory { access_key: "LTAI5t...".into() };
    let tencent = TencentFactory { secret_id: "AKIDz8...".into() };

    let reports = process_batch(&aliyun, &["13800138000"], "您的验证码是1234");
    println!("{:?}", reports);

    let reports = process_batch(&tencent, &["13900139000"], "您的验证码是5678");
    println!("{:?}", reports);
}
```

编译期保证：**`client` 和 `parser` 来自同一个 `F: SmsFactory`**。不存在编译期允许阿里 Client + 腾讯 Parser 的情况。

## 选供应商——运行期决定

编译期不知道用哪家，需要运行期根据配置选：

```rust
enum Provider { Aliyun, Tencent }

fn create_factory(provider: Provider, config: &Config) -> Box<dyn SmsFactoryDyn> {
    match provider {
        Provider::Aliyun  => Box::new(AliyunFactory  { access_key: config.aliyun_key.clone() }),
        Provider::Tencent => Box::new(TencentFactory  { secret_id:  config.tencent_id.clone() }),
    }
}

// 运行期多态时退回到 trait object
trait SmsFactoryDyn {
    fn create_client(&self) -> Box<dyn SmsClient>;
    fn create_parser(&self) -> Box<dyn ReportParser>;
}

// 为所有实现了 SmsFactory 的 T 自动实现 SmsFactoryDyn
// （实际项目中这需要手动写，或者用 enum_dispatch 等 crate 优化）
```

两种分发的选择：

```text
编译期确定用哪家（绝大多数服务）  运行期切换（A/B 测试、灰度发布）
        ↓                                  ↓
 泛型 fn process<F: SmsFactory>       Box<dyn SmsFactoryDyn>
 零开销，内联友好                      有虚表查找，有堆分配
```

项目中更常见的做法是——**用 enum 替代 trait object**：

```rust
enum SmsProvider {
    Aliyun(AliyunFactory),
    Tencent(TencentFactory),
}

impl SmsProvider {
    fn send(&self, phone: &str, content: &str) -> Result<String, String> {
        match self {
            SmsProvider::Aliyun(f)  => f.create_client().send(phone, content),
            SmsProvider::Tencent(f) => f.create_client().send(phone, content),
        }
    }
}
```

enum 方案没有堆分配，没有虚表——只是把所有分支写在一个 match 里。供应商数量少（< 5 家）时，这比 trait object 更快、更简单。

## Factory Method vs Abstract Factory

| | Factory Method | Abstract Factory |
|---|---|---|
| 创建 | 一个产品 | 一组相关产品 |
| 产品数 | 1 个 trait | 多个 trait |
| 保证 | 单个对象的创建方式 | **同一族的对象不会被混用** |
| Rust 表达 | `trait + 1 个关联类型` | `trait + 多个关联类型` |
| 运行期切换 | enum 或 Box<dyn> | enum 或 Box<dyn> |

Abstract Factory 本质上就是**把 Factory Method 扩展到多个维度**——它保证的不是「怎么创建」，而是「哪些产品必须配套」。

## 什么时候用

**用 Abstract Factory**：
- 有多个产品族，每个族有多个相关产品——换一整个产品族应该只改一处
- 需要**编译期保证**产品族一致性——不允许混搭阿里 Client + 腾讯 Parser

**不用 Abstract Factory**：
- 只有一个产品——退回 Factory Method 或直接 `new()`
- 产品族之间没有配套关系——两个独立的 Factory Method 就够了
- 过度设计——如果只服务一家供应商，加抽象就是浪费

## 小结

- Abstract Factory 保证 **一组相关对象的创建一致性**
- Rust 用 **trait 内多个关联类型** 表达——`type Client` + `type Parser` 在同一 trait
- 编译器保证泛型函数内 `client` 和 `parser` 来自同一个工厂
- 运行期切换用 enum 分发——比 trait object 更快，不堆分配

---

**下一篇：** [Singleton 模式](singleton.md)
**返回：** [设计模式：Rust 视角](index.md)
