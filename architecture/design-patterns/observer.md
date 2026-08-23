# Observer 模式 — Rust 设计模式系列

> 系列：用 Rust 的类型系统重新审视 GoF 23 个设计模式。本文基于 Rust 1.95 稳定版。

## 生活比喻：小区快递柜

你网购了一个快递，快递到了小区快递柜，你收到一条短信通知。你不需要每隔 5 分钟去快递柜看一眼——快递柜会在"有新快递"时**主动通知你**。你只需要在下单时登记手机号（订阅），之后就等着被通知。

这就是 Observer 模式的核心：**对象状态变化时，自动通知所有订阅者**。

- 你 = Observer（观察者）
- 快递柜 = Subject（被观察对象）
- 登记手机号 = `subscribe()`
- 短信通知 = `notify()`

## 经典实现：回调地狱

GoF 的经典做法是维护一个观察者列表，状态变化时遍历调用：

```rust
trait Observer {
    fn on_event(&self, event: &str);
}

struct EventBus {
    listeners: Vec<Box<dyn Observer>>,
}

impl EventBus {
    fn subscribe(&mut self, observer: Box<dyn Observer>) {
        self.listeners.push(observer);
    }

    fn notify(&self, event: &str) {
        for listener in &self.listeners {
            listener.on_event(event);
        }
    }
}
```

问题显而易见：

1. **类型擦除**——`Box<dyn Observer>` 丢失了具体类型信息
2. **生命周期纠缠**——观察者的引用必须比 EventBus 活得久
3. **不可变借用冲突**——`notify` 借用 `self`，回调里想修改 EventBus 就死锁

## Rust 的解法：channel

Rust 标准库提供了 `mpsc::channel`（多生产者、单消费者）和 `tokio::sync::broadcast`（多生产者、多消费者），天然就是 Observer 模式：

```rust
use std::sync::mpsc;

// Subject：持有发送端
struct EventEmitter {
    sender: mpsc::Sender<String>,
}

impl EventEmitter {
    fn new() -> (Self, mpsc::Receiver<String>) {
        let (tx, rx) = mpsc::channel();
        (Self { sender: tx }, rx)
    }

    fn emit(&self, event: String) {
        self.sender.send(event).unwrap();
    }
}

// Observer：在另一个线程接收
fn main() {
    let (emitter, rx) = EventEmitter::new();

    // 订阅者在独立线程
    std::thread::spawn(move || {
        while let Ok(event) = rx.recv() {
            println!("收到事件: {event}");
        }
    });

    emitter.emit("用户登录".into());
    emitter.emit("订单创建".into());
}
```

**好在哪：**

- **所有权清晰**——发送端和接收端各自拥有通道的一端，没有共享可变状态
- **线程安全**——`mpsc::Sender` 实现了 `Clone`，多个 Subject 可以发送到同一个 Observer
- **生命周期解耦**——发送端被 drop 后，接收端的 `recv()` 自动返回 `Err`，优雅退出

## 异步场景：tokio::broadcast

同步 channel 是单消费者的——如果多个观察者都想收到同一个事件呢？`tokio::sync::broadcast` 解决了这个问题：

```rust
use tokio::sync::broadcast;

#[derive(Clone, Debug)]
enum Event {
    UserLogin(String),
    OrderCreated { id: u64, amount: f64 },
}

async fn run() {
    let (tx, _) = broadcast::channel::<Event>(16);

    // 观察者 A
    let mut rx_a = tx.subscribe();
    let handle_a = tokio::spawn(async move {
        while let Ok(event) = rx_a.recv().await {
            println!("[A] 收到: {event:?}");
        }
    });

    // 观察者 B
    let mut rx_b = tx.subscribe();
    let handle_b = tokio::spawn(async move {
        while let Ok(event) = rx_b.recv().await {
            println!("[B] 收到: {event:?}");
        }
    });

    // 发布事件
    tx.send(Event::UserLogin("alice".into())).unwrap();
    tx.send(Event::OrderCreated { id: 42, amount: 99.9 }).unwrap();

    drop(tx); // 关闭通道，观察者自动退出
    let _ = tokio::join!(handle_a, handle_b);
}
```

**好在哪：**

- **多播**——一个事件可以被多个观察者同时收到，不需要为每个观察者维护单独的通道
- **背压处理**——缓冲区满时，慢的观察者会丢失旧事件（`RecvError::Lagged`），快的观察者不受影响
- **drop 即取消订阅**——不需要显式 unsubscribe，drop receiver 就是取消订阅

## 对比：trait 回调 vs channel

| 维度 | trait 回调 | channel |
|------|-----------|---------|
| 耦合度 | Subject 持有 Observer 引用，强耦合 | 通过通道通信，完全解耦 |
| 线程安全 | 需要 `Arc<Mutex<dyn Observer>>` | `Sender` 本身就是 `Send + Sync` |
| 生命周期 | Observer 必须比 Subject 活得久 | 两端独立，通过 ownership 管理 |
| 取消订阅 | 需要手动从列表移除 | drop receiver 即可 |
| 多播 | 需要遍历 Vec | `broadcast::channel` 原生支持 |

## 实战：UI 事件系统

假设我们有一个简单的 UI 框架，按钮点击时需要通知多个组件更新：

```rust
use std::sync::mpsc;

#[derive(Debug)]
enum UiEvent {
    ButtonClicked(String),
    TextInput { field: String, value: String },
    WindowResized { width: u32, height: u32 },
}

struct EventBus {
    sender: mpsc::Sender<UiEvent>,
}

impl EventBus {
    fn new() -> (Self, mpsc::Receiver<UiEvent>) {
        let (tx, rx) = mpsc::channel();
        (Self { sender: tx }, rx)
    }

    fn emit(&self, event: UiEvent) {
        let _ = self.sender.send(event);
    }

    fn subscribe(&self) -> mpsc::Receiver<UiEvent> {
        // 多个订阅者需要 clone sender，但 mpsc 是单消费者
        // 实际项目中用 broadcast 更合适
        unimplemented!("用 broadcast::channel 替代")
    }
}

// 实际使用中，每个组件在自己的线程/任务里接收事件
fn status_bar(rx: mpsc::Receiver<UiEvent>) {
    while let Ok(event) = rx.recv() {
        match event {
            UiEvent::WindowResized { width, height } => {
                println!("状态栏更新: {width}x{height}");
            }
            _ => {}
        }
    }
}

fn button_handler(rx: mpsc::Receiver<UiEvent>) {
    while let Ok(event) = rx.recv() {
        if let UiEvent::ButtonClicked(name) = event {
            println!("按钮 {name} 被点击，执行业务逻辑");
        }
    }
}
```

## 什么时候该用 Observer

**适合的场景：**

- 事件驱动架构（GUI、消息系统、Webhook）
- 状态变化需要通知多个不相关的组件
- 发布者不需要知道订阅者是谁

**不适合的场景：**

- 只有一个观察者——直接函数调用更简单
- 需要同步返回结果——Observer 是"发射后不管"，不适合请求-响应模式
- 事件顺序很重要——多播 channel 不保证所有观察者看到相同的顺序

## 骨架代码

```rust
use tokio::sync::broadcast;

#[derive(Clone, Debug)]
struct Event {
    kind: String,
    payload: String,
}

struct EventEmitter {
    tx: broadcast::Sender<Event>,
}

impl EventEmitter {
    fn new(capacity: usize) -> Self {
        let (tx, _) = broadcast::channel(capacity);
        Self { tx }
    }

    fn emit(&self, event: Event) {
        let _ = self.tx.send(event);
    }

    fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.tx.subscribe()
    }
}

// 观察者：独立任务，只关心自己感兴趣的事件
async fn observer(name: String, mut rx: broadcast::Receiver<Event>) {
    while let Ok(event) = rx.recv().await {
        if event.kind == "order" {
            println!("[{name}] 处理订单: {}", event.payload);
        }
    }
}

#[tokio::main]
async fn main() {
    let emitter = EventEmitter::new(64);

    let rx1 = emitter.subscribe();
    let rx2 = emitter.subscribe();

    tokio::spawn(observer("订单服务".into(), rx1));
    tokio::spawn(observer("通知服务".into(), rx2));

    emitter.emit(Event {
        kind: "order".into(),
        payload: "order-123".into(),
    });
}
```

## Observer vs Pub/Sub：有区别吗

GoF 原文里，Pub/Sub 是 Observer 的别名（"别名：Dependents, Publish-Subscribe"）。但在工程实践中，两者有耦合差异：

- **Observer**：Subject **直接持有** Observer 引用，遍历列表逐个通知，两者互相知道对方
- **Pub/Sub**：Publisher 和 Subscriber **互不知道**，中间有一个 Broker/Channel 负责路由，按 topic 解耦

```rust
// Observer：Subject 直接调用 Observer 的方法
subject.observers.iter().for_each(|o| o.on_change(&data));

// Pub/Sub：Publisher 只管往 channel 发，不知道谁在收
tx.send(event).unwrap();
```

本文的实现都是 Pub/Sub 风格——通过 channel 通信，发布者和订阅者完全解耦。严格来说叫 "Pub/Sub" 更准确，但 GoF 把它们归为同一个模式，Rust 社区也习惯叫 Observer。

## 总结

Rust 里 Observer 模式的最佳实践是 **channel 而非 trait 回调**。标准库的 `mpsc` 适合单消费者场景，`tokio::sync::broadcast` 适合多播场景。核心优势是所有权模型带来的线程安全——不需要 `Arc<Mutex<>>` 包装，不需要手动管理订阅生命周期，drop 就是取消订阅。

GoF 里需要写一堆 boilerplate 的 Observer，在 Rust 里就是"开个 channel，spawn 个任务"。
