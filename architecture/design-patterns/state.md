# State 模式 — Rust 设计模式系列

> 系列：用 Rust 的类型系统重新审视 GoF 23 个设计模式。本文基于 Rust 1.95 稳定版。

## 生活比喻：自动售货机

自动售货机有不同的状态：待机、已投币、出货中、缺货。每个状态下，同样的操作（按按钮、投币）行为完全不同：

- 待机时按按钮 → 没反应
- 已投币时按按钮 → 出货
- 缺货时投币 → 退币

状态不同，行为不同。State 模式就是**让对象在不同状态下表现出不同行为**。

## GoF 的做法：状态继承

GoF 用继承实现：定义一个 `State` 接口，每个状态是一个子类，运行时切换子类实例：

```rust
// GoF 风格：trait 对象 + 动态分发
trait VendingState {
    fn insert_coin(&self) -> Box<dyn VendingState>;
    fn press_button(&self) -> Box<dyn VendingState>;
    fn dispense(&self) -> Box<dyn VendingState>;
}

struct Idle;
struct HasCoin;
struct Dispensing;

impl VendingState for Idle {
    fn insert_coin(&self) -> Box<dyn VendingState> {
        println!("收到硬币");
        Box::new(HasCoin)
    }
    fn press_button(&self) -> Box<dyn VendingState> {
        println!("请先投币");
        Box::new(Idle)
    }
    fn dispense(&self) -> Box<dyn VendingState> {
        println!("请先投币");
        Box::new(Idle)
    }
}

struct Machine {
    state: Box<dyn VendingState>,
}

impl Machine {
    fn insert_coin(&mut self) {
        self.state = self.state.insert_coin();
    }
}
```

问题：

1. **每个状态都要实现所有方法**——即使大部分方法只是"没反应"
2. **`Box<dyn>` 堆分配**——状态切换每次都 alloc
3. **状态分散在多个文件里**——要理解整个状态机，得翻遍所有 State 子类

## Rust 的解法：enum + match

Rust 用 enum 表示状态，match 处理转换，所有逻辑集中在一个地方：

```rust
enum State {
    Idle,
    HasCoin,
    Dispensing,
    SoldOut,
}

struct Machine {
    state: State,
    stock: u32,
}

impl Machine {
    fn insert_coin(&mut self) {
        match &self.state {
            State::Idle => {
                println!("收到硬币");
                self.state = State::HasCoin;
            }
            State::HasCoin => println!("已经投过币了"),
            State::Dispensing => println!("正在出货，请稍候"),
            State::SoldOut => println!("已售罄，硬币退回"),
        }
    }

    fn press_button(&mut self) {
        match &self.state {
            State::Idle => println!("请先投币"),
            State::HasCoin => {
                if self.stock > 0 {
                    println!("出货中...");
                    self.stock -= 1;
                    self.state = State::Dispensing;
                } else {
                    println!("已售罄");
                    self.state = State::SoldOut;
                }
            }
            State::Dispensing => println!("正在出货，请稍候"),
            State::SoldOut => println!("已售罄"),
        }
    }

    fn dispense(&mut self) {
        match &self.state {
            State::Dispensing => {
                println!("请取货");
                self.state = if self.stock > 0 {
                    State::Idle
                } else {
                    State::SoldOut
                };
            }
            _ => {}
        }
    }
}
```

**好在哪：**

- **零堆分配**——enum 在栈上，状态切换只是改 tag，没有 `Box::new`
- **状态集中**——所有状态和转换在同一个 match 里，一目了然
- **编译器穷举检查**——新增状态时，每个 match 都会报错，不会漏掉

## 状态携带数据

enum 的杀手锏：每个状态可以携带不同的数据，编译器保证你不会在错误的状态下访问错误的数据：

```rust
enum OrderState {
    Pending {
        created_at: std::time::Instant,
    },
    Paid {
        amount: f64,
        paid_at: std::time::Instant,
    },
    Shipped {
        tracking_number: String,
        carrier: String,
    },
    Delivered {
        signed_by: String,
    },
    Cancelled {
        reason: String,
    },
}

struct Order {
    id: u64,
    state: OrderState,
}

impl Order {
    fn ship(&mut self, tracking: String, carrier: String) {
        match &self.state {
            OrderState::Paid { amount, .. } => {
                println!("订单 {} 已支付 {:.2}，发货", self.id, amount);
                self.state = OrderState::Shipped {
                    tracking_number: tracking,
                    carrier,
                };
            }
            _ => println!("只有已支付的订单才能发货"),
        }
    }

    fn tracking_info(&self) -> Option<(&str, &str)> {
        match &self.state {
            OrderState::Shipped { tracking_number, carrier } => {
                Some((tracking_number, carrier))
            }
            _ => None,
        }
    }
}
```

GoF 里要实现这个，需要在每个 State 子类里加字段，还得用 `downcast` 类型转换才能访问。Rust 里就是普通的 enum 字段访问。

## 实战：TCP 连接状态

TCP 协议本身就是状态机，用 Rust enum 实现非常自然：

```rust
#[derive(Debug)]
enum TcpState {
    Listen,
    SynReceived,
    Established,
    FinWait1,
    FinWait2,
    TimeWait,
    Closed,
}

#[derive(Debug)]
enum TcpEvent {
    Syn,
    SynAck,
    Ack,
    Fin,
    Timeout,
}

struct TcpConnection {
    state: TcpState,
}

impl TcpConnection {
    fn new() -> Self {
        Self { state: TcpState::Listen }
    }

    fn handle(&mut self, event: TcpEvent) {
        self.state = match (&self.state, event) {
            (TcpState::Listen, TcpEvent::Syn) => {
                println!("收到 SYN，回复 SYN-ACK");
                TcpState::SynReceived
            }
            (TcpState::SynReceived, TcpEvent::Ack) => {
                println!("三次握手完成");
                TcpState::Established
            }
            (TcpState::Established, TcpEvent::Fin) => {
                println!("收到 FIN，连接关闭中");
                TcpState::FinWait1
            }
            (TcpState::FinWait1, TcpEvent::Ack) => TcpState::FinWait2,
            (TcpState::FinWait2, TcpEvent::Fin) => {
                println!("收到对端 FIN");
                TcpState::TimeWait
            }
            (TcpState::TimeWait, TcpEvent::Timeout) => {
                println!("TIME_WAIT 超时，连接完全关闭");
                TcpState::Closed
            }
            (state, event) => {
                println!("无效转换: {state:?} + {event:?}");
                return;
            }
        };
        println!("当前状态: {:?}", self.state);
    }
}
```

**好在哪：**

- **无效转换不会 panic**——match 的兜底分支处理了所有非法组合
- **状态转换一目了然**——所有 `(当前状态, 事件) → 新状态` 的映射集中在一个 match 里
- **每个状态携带不同数据**——`Established` 可以有 `remote_addr`，`TimeWait` 可以有 `deadline`，编译器保证不会混用

## 对比：enum State vs trait State

| 维度 | enum + match | trait 对象 |
|------|-------------|-----------|
| 状态切换 | 改 enum tag，零开销 | `Box::new(新状态)`，堆分配 |
| 代码集中度 | 所有转换在一个 match 里 | 分散在多个 impl 块里 |
| 状态数据 | enum variant 携带，编译器检查 | 子类字段，需要 downcast |
| 新增状态 | 编译器报错提醒所有 match | 可能漏掉某个方法 |
| 开放性 | 封闭（加状态要改 enum） | 开放（加状态加新类型） |

Rust 的 enum State 是**封闭状态机**——状态集合在编译期确定。这对大多数场景是优势：编译器帮你检查所有分支，不会遗漏。如果你需要运行时动态添加状态（比如插件系统），trait 对象更合适。

## 什么时候该用 State

**适合的场景：**

- 状态数量固定且已知（订单、连接、游戏 AI）
- 不同状态下相同操作行为不同
- 状态之间有明确的转换规则

**不适合的场景：**

- 状态会动态增加（用 trait 对象）
- 只有 2-3 个状态，简单的 if-else 就够了
- 状态转换很复杂且需要回滚——考虑用 Memento 模式

## 骨架代码

```rust
#[derive(Debug, Clone)]
enum State {
    Idle,
    Active { started_at: u64 },
    Paused { remaining: u64 },
    Done,
}

struct Context {
    state: State,
}

impl Context {
    fn new() -> Self {
        Self { state: State::Idle }
    }

    fn start(&mut self) {
        self.state = match &self.state {
            State::Idle => {
                println!("启动");
                State::Active { started_at: 0 }
            }
            other => {
                println!("无法从 {other:?} 启动");
                return;
            }
        };
    }

    fn pause(&mut self) {
        self.state = match &self.state {
            State::Active { started_at } => {
                println!("暂停");
                State::Paused { remaining: 100 - started_at }
            }
            other => {
                println!("无法从 {other:?} 暂停");
                return;
            }
        };
    }

    fn resume(&mut self) {
        self.state = match &self.state {
            State::Paused { remaining } => {
                println!("恢复，剩余 {remaining}");
                State::Active { started_at: 100 - remaining }
            }
            other => {
                println!("无法从 {other:?} 恢复");
                return;
            }
        };
    }
}
```

## 总结

Rust 里 State 模式的最佳实践是 **enum + match**，而非 GoF 的 trait 继承。核心优势：

- **栈上零开销**——enum tag 切换，没有堆分配
- **编译器穷举检查**——新增状态时不会漏掉分支
- **状态携带数据**——每个 variant 可以有不同字段，类型安全

GoF 里需要一堆 State 子类 + downcast 的事情，在 Rust 里就是一个 enum 加一个 match。
