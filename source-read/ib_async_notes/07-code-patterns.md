# 关键代码模式

> 基于 [ib_async](https://github.com/ib-api-reloaded/ib_async) 源码分析。提炼 ib_async 中可复用的设计模式。

## 模式一：Facade 模式

### 问题

底层系统复杂（Client + Wrapper + Decoder），用户需要简单接口。

### 解法

IB 类作为 Facade，隐藏复杂性：

```python
class IB:
    def __init__(self):
        self._client = Client()      # TCP 连接
        self._wrapper = Wrapper()    # 回调处理
        self._decoder = Decoder()    # 消息解码

    # 简单接口
    def connect(self, host, port, clientId=1):
        self._client.connect(host, port, clientId)

    def reqMktData(self, contract):
        return self._wrapper.startTicker(contract)

    def placeOrder(self, contract, order):
        return self._wrapper.startTrade(contract, order)
```

### 适用场景

- 封装复杂子系统
- 提供统一入口
- 降低耦合度

## 模式二：Observer 模式

### 问题

状态变化需要通知多个监听者。

### 解法

eventkit 事件系统：

```python
class IB:
    events = Event.Group(
        orderEvent=Event(),
        pendingTickersEvent=Event(),
        positionEvent=Event(),
    )

# 订阅
ib.orderEvent += lambda trade: print(trade)

# 触发（内部）
self.ib.orderEvent.emit(trade)
```

### 适用场景

- 事件驱动架构
- 状态变化通知
- 解耦生产者和消费者

## 模式三：Value Object 模式

### 问题

数据需要在多个地方传递，但不应该被修改。

### 解法

Ticker、Trade、Position 等值对象：

```python
class Ticker:
    def __init__(self, contract):
        self.contract = contract
        self.bid = 0.0
        self.ask = 0.0
        self.last = 0.0
        self.volume = 0

class Trade:
    def __init__(self, contract, order):
        self.contract = contract
        self.order = order
        self.orderStatus = OrderStatus()
        self.fills = []
```

### 适用场景

- 数据传输对象
- 状态容器
- 领域模型

## 模式四：Factory Method 模式

### 问题

创建对象需要复杂配置。

### 解法

工厂方法简化创建：

```python
# 简化合约创建
Stock('AAPL', 'SMART', 'USD')  # 而非 Contract(symbol='AAPL', secType='STK', ...)
Forex('EURUSD')                 # 而非 Contract(symbol='EUR', secType='FOREX', ...)
Future('ES', '202412', 'CME')   # 而非 Contract(symbol='ES', secType='FUT', ...)

# 简化订单创建
MarketOrder('BUY', 100)         # 而非 Order(action='BUY', totalQuantity=100, orderType='MKT')
LimitOrder('BUY', 100, 150.0)   # 而非 Order(action='BUY', totalQuantity=100, orderType='LMT', lmtPrice=150)
```

### 适用场景

- 简化对象创建
- 预设默认值
- 类型安全

## 模式五：Length-Prefixed Framing

### 问题

TCP 是字节流，需要分隔消息边界。

### 解法

每条消息前 4 字节是长度：

```python
def send(self, data: bytes):
    length = len(data).to_bytes(4, 'big')
    self.socket.sendall(length + data)

def recv(self) -> bytes:
    length = int.from_bytes(self._recv_exact(4), 'big')
    return self._recv_exact(length)
```

### 适用场景

- TCP 通信
- 二进制协议
- 消息分帧

## 模式六：Context Manager

### 问题

资源需要正确释放（连接、文件等）。

### 解法

`with` 语句自动管理：

```python
# 同步
with IB() as ib:
    ib.connect('127.0.0.1', 7497)
    # 自动断开

# 异步
async with IB() as ib:
    await ib.connectAsync('127.0.0.1', 7497)
    # 自动断开
```

### 适用场景

- 资源管理
- 连接生命周期
- 异常安全

## 模式七：Fuzzy Matching

### 问题

用户输入不精确，需要模糊匹配。

### 解法

前缀匹配：

```python
def fuzzyMatch(query, candidates):
    query = query.upper()
    return [
        c for c in candidates
        if c.symbol.upper().startswith(query)
        or c.localSymbol.upper().startswith(query)
    ]
```

### 适用场景

- 用户输入匹配
- 搜索建议
- 自动补全

## 模式八：Event Sourcing

### 问题

状态变化需要完整记录。

### 解法

Trade 对象记录所有状态变化：

```python
class Trade:
    def __init__(self, contract, order):
        self.contract = contract
        self.order = order
        self.orderStatus = OrderStatus()
        self.fills = []        # 成交记录
        self.log = []          # 状态变更日志

    def _update(self, status):
        # 记录状态变化
        self.log.append((time.time(), status))
        # 更新当前状态
        self.orderStatus = status
```

### 适用场景

- 审计追踪
- 状态回放
- 交易记录

## 总结

ib_async 的代码模式可以提炼为八个核心模式：

| 模式 | 解决的问题 | 核心思想 |
|------|-----------|---------|
| Facade | 复杂子系统 | 统一入口隐藏复杂性 |
| Observer | 状态通知 | 事件驱动解耦 |
| Value Object | 数据传输 | 不可变值容器 |
| Factory Method | 对象创建 | 工厂方法简化配置 |
| Length-Prefixed Framing | TCP 分帧 | 长度前缀分隔消息 |
| Context Manager | 资源管理 | 自动释放资源 |
| Fuzzy Matching | 用户输入 | 前缀模糊匹配 |
| Event Sourcing | 状态记录 | 记录所有状态变化 |

这些模式不是 ib_async 独创的，但组合起来构建了一个完整的 IBKR 客户端库。
