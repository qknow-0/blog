# Factory Method 模式：用 trait 关联类型做对象创建

> 本文基于 Rust 1.95。

## 不用 Factory Method 的问题

假设你要支持两种支付渠道——支付宝和微信。最直接的写法是 `match`：

```rust
enum PaymentChannel {
    Alipay,
    Wechat,
}

fn process_payment(channel: PaymentChannel, amount: f64) -> Result<(), Error> {
    match channel {
        PaymentChannel::Alipay => {
            let client = AlipayClient::new("app_id", "private_key")?;
            client.pay(amount)
        }
        PaymentChannel::Wechat => {
            let client = WechatClient::new("mch_id", "api_key")?;
            client.pay(amount)
        }
    }
}
```

问题：每次加一个新渠道（比如 Apple Pay），你要在所有 `match` 上加一个新分支。忘了一处，编译器不报错——运行期才炸。

Factory Method 解决的就是这事：**把「创建什么对象」的决定从使用代码里抽出来，让每个具体类型自己决定怎么创建自己**。

## GoF 定义

```text
Factory Method：
  定义一个创建对象的接口，让子类决定实例化哪个类。

                     ┌──────────────┐
                     │   Creator    │
                     │ + create()   │  ← 工厂方法
                     │ + operate()  │  ← 使用产品的业务逻辑
                     └──────┬───────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
     ┌────────┴────────┐         ┌────────┴────────┐
     │ AlipayCreator   │         │ WechatCreator   │
     │ create() → AClient│       │ create() → WClient│
     └─────────────────┘         └─────────────────┘
```

Java/C++ 的实现需要继承——`AlipayCreator extends Creator`。Rust 没有继承，用 trait + 关联类型等价实现——而且编译期就保证类型安全。

## Rust 版：trait + 关联类型

```rust
// 产品——支付客户端的行为契约
trait PaymentClient {
    fn pay(&self, amount: f64) -> Result<(), String>;
}

// 具体产品
struct AlipayClient {
    app_id: String,
}
impl PaymentClient for AlipayClient {
    fn pay(&self, amount: f64) -> Result<(), String> {
        println!("[支付宝] app_id={} 支付 {:.2} 元", self.app_id, amount);
        Ok(())
    }
}

struct WechatClient {
    mch_id: String,
}
impl PaymentClient for WechatClient {
    fn pay(&self, amount: f64) -> Result<(), String> {
        println!("[微信] mch_id={} 支付 {:.2} 元", self.mch_id, amount);
        Ok(())
    }
}

// 工厂——trait 里的关联类型指向具体产品
trait PaymentFactory {
    type Client: PaymentClient;      // ← 关联类型：工厂产出什么

    fn create_client(&self) -> Result<Self::Client, String>;
}

// 具体工厂
struct AlipayFactory {
    app_id: String,
}
impl PaymentFactory for AlipayFactory {
    type Client = AlipayClient;     // ← 告诉编译器：我的产品是 AlipayClient

    fn create_client(&self) -> Result<Self::Client, String> {
        Ok(AlipayClient {
            app_id: self.app_id.clone(),
        })
    }
}

struct WechatFactory {
    mch_id: String,
}
impl PaymentFactory for WechatFactory {
    type Client = WechatClient;

    fn create_client(&self) -> Result<Self::Client, String> {
        Ok(WechatClient {
            mch_id: self.mch_id.clone(),
        })
    }
}
```

关键设计：**`type Client: PaymentClient` 关联类型**。它让编译器在编译期就知道每个工厂确切产出什么类型——不需要运行时类型转换，不需要 `Box<dyn>`，零开销。

## 用法：泛型消费工厂

```rust
// 业务代码只依赖 trait，不依赖具体工厂
fn process_payment<F: PaymentFactory>(factory: &F, amount: f64) -> Result<(), String> {
    let client = factory.create_client()?;  // 编译器推断出 client 的确切类型
    client.pay(amount)
}

fn main() -> Result<(), String> {
    let alipay = AlipayFactory { app_id: "20210001".into() };
    let wechat = WechatFactory { mch_id: "1900000109".into() };

    process_payment(&alipay, 100.0)?;
    process_payment(&wechat, 200.0)?;
    Ok(())
}
```

`process_payment::<F: PaymentFactory>` 是**泛型 + 静态分发**——编译器为每个具体工厂生成一份代码，调用 `create_client()` 是直接函数调用，没有虚表查表。

## 加新产品：只加代码，不改旧代码

```rust
// 1. 新产品——Apple Pay
struct ApplePayClient { merchant_id: String }
impl PaymentClient for ApplePayClient {
    fn pay(&self, amount: f64) -> Result<(), String> {
        println!("[Apple Pay] merchant={} 支付 {:.2} 元", self.merchant_id, amount);
        Ok(())
    }
}

// 2. 新工厂
struct ApplePayFactory { merchant_id: String }
impl PaymentFactory for ApplePayFactory {
    type Client = ApplePayClient;
    fn create_client(&self) -> Result<Self::Client, String> {
        Ok(ApplePayClient { merchant_id: self.merchant_id.clone() })
    }
}

// 3. 已有代码一行不用改——直接调用
let apple = ApplePayFactory { merchant_id: "merchant.com.example".into() };
process_payment(&apple, 300.0)?;
```

这就是开闭原则的核心：**对扩展开放，对修改关闭**。

## 关联类型的编译期安全

想象不用关联类型，用 trait object：

```rust
// ❌ 用 trait object 替代关联类型——失去了编译期类型信息
trait PaymentFactoryDyn {
    fn create_client(&self) -> Box<dyn PaymentClient>;
}
// 返回 Box<dyn> 意味着：
// - 堆分配
// - 动态分发（vtable）
// - 类型信息丢失——编译器不知道到底是 AlipayClient 还是 WechatClient
```

关联类型 `type Client: PaymentClient` 等价于：「每个 `impl PaymentFactory` 声明时，编译器就记录下 `Client` 的确切类型，后续所有使用 `Self::Client` 的地方都被替换成具体类型」。这是**编译期类型安全的工厂方法**——GoF 用继承做到的事，Rust 用 trait + 关联类型做到了，而且不需要运行时检查。

## 实际场景

Rust 标准库里 `Iterator` trait 就是工厂方法：

```rust
pub trait Iterator {
    type Item;  // ← 工厂方法的产品

    fn next(&mut self) -> Option<Self::Item>;
    //                     ^^^^^^^^^
    //                     next() 是工厂方法——每次调用产出一个 Self::Item
}
```

`map`、`filter`、`collect` 这些适配器之所以能保持零开销抽象，是因为关联类型在编译期就被消解成具体类型了。

## 什么时候用，什么时候不用

**用 Factory Method**：
- 对象创建逻辑复杂（要调多个 API、读配置、验证参数）
- 需要支持运行时或编译期切换产品族
- 创建过程有跨产品族的通用逻辑，但具体产品不同

**不用 Factory Method**：
- 直接 `new()` 就够了——不要为简单创建加一层抽象
- 只有一个产品变体——factory 的接口就是多余的空壳
- 能用闭包或函数指针代替时——Rust 里 `fn() -> T` 有时比定义一个 trait 更轻量

## 小结

- GoF 的 Factory Method 在 Rust 里等价于 **trait + 关联类型 + 泛型**
- `type Client: PaymentClient` 替代了继承关系
- `fn process_payment<F: PaymentFactory>` 替代了多态分发
- 编译期完成所有类型检查——没有虚表、没有堆分配、没有类型转换
- 加新产品 = 加代码，不碰已有代码——开闭原则

---

**返回：** [设计模式：Rust 视角](index.md)
