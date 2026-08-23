# Client 与 IBKR 二进制协议

> 基于 [ib_async](https://github.com/ib-api-reloaded/ib_async) 源码分析。

## 生活比喻：电报通信

IBKR API 的通信像电报——用二进制编码发送消息，每个字段有固定格式。Client 是发报员，负责把你的请求编码成二进制发给 TWS；Decoder 是收报员，把 TWS 发回的二进制解码成 Python 对象。

## Client 类

Client 类（1183 行）负责 TCP 连接和消息发送。核心职责：

1. **建立 TCP 连接**
2. **序列化请求**——把 Python 参数编码成 IBKR 二进制格式
3. **发送消息**——通过 socket 发送
4. **接收响应**——从 socket 读取字节

```python
# client.py（简化）
class Client:
    def connect(self, host, port, clientId):
        self.socket = socket.socket()
        self.socket.connect((host, port))
        self._send_connect_params(clientId)

    def reqMktData(self, reqId, contract, genericTickList):
        # 序列化
        msg = self._encode('reqMktData', reqId, contract, genericTickList)
        # 发送
        self._send(msg)

    def placeOrder(self, orderId, contract, order):
        msg = self._encode('placeOrder', orderId, contract, order)
        self._send(msg)
```

## IBKR 二进制协议

IBKR API 使用自定义的二进制协议，所有字段用 `\0`（null 字节）分隔：

```python
# 消息格式
# [字段1]\0[字段2]\0[字段3]\0...\0

# 示例：reqMktData 消息
# "1\01\0AAPL\0STK\0\0\00\0\0\0\0"
#  ↑ ↑  ↑    ↑    ↑ ↑ ↑ ↑
#  | |  |    |    | | | └ genericTickList
#  | |  |    |    | | └ exchange
#  | |  |    |    | └ currency
#  | |  |    |    └ strike
#  | |  |    └ secType
#  | |  └ symbol
#  | └ reqId
#  └ 消息类型
```

## 消息编码

Client 内部有编码器，把 Python 对象转成二进制：

```python
def _encode(self, *fields) -> bytes:
    # 所有字段转字符串，用 \0 分隔
    parts = []
    for field in fields:
        if isinstance(field, bool):
            parts.append('1' if field else '0')
        elif isinstance(field, (int, float)):
            parts.append(str(field))
        elif isinstance(field, str):
            parts.append(field)
        elif field is None:
            parts.append('')
        elif isinstance(field, Contract):
            parts.extend(self._encode_contract(field))
        elif isinstance(field, Order):
            parts.extend(self._encode_order(field))
    return '\0'.join(parts).encode('ascii') + b'\0'
```

## 消息解码

Decoder 类（1370 行）负责把 TWS 发回的二进制解码成 Python 对象：

```python
# decoder.py（简化）
class Decoder:
    def __init__(self, wrapper):
        self.wrapper = wrapper

    def decode(self, data: bytes):
        fields = data.split(b'\0')
        msg_type = int(fields[0])

        if msg_type == 1:  # tickPrice
            self._decode_tick_price(fields)
        elif msg_type == 2:  # tickSize
            self._decode_tick_size(fields)
        elif msg_type == 3:  # orderStatus
            self._decode_order_status(fields)
        # ... 更多消息类型

    def _decode_tick_price(self, fields):
        reqId = int(fields[1])
        tickType = int(fields[2])
        price = float(fields[3])
        # 调用 Wrapper 的回调
        self.wrapper.tickPrice(reqId, tickType, price)
```

## 连接握手

连接建立时，Client 和 TWS 有一个握手过程：

```python
def _send_connect_params(self, clientId):
    # 发送版本号
    self._send(b'v100..176')

    # 发送连接参数
    # [clientId]\0[optionalCapabilities]\0
    msg = f'{clientId}\0\0'.encode('ascii')
    self._send(msg)

    # 等待 TWS 响应
    data = self._recv()
    # 解析服务器版本和连接时间
```

## 心跳机制

Client 定期发送心跳保持连接：

```python
async def _heartbeat_loop(self):
    while self.isConnected():
        await asyncio.sleep(30)  # 每 30 秒
        self.reqCurrentTime()    # 发送心跳请求
```

## 优秀代码：消息帧处理

### 源码

```python
# client.py（简化）
class Client:
    def _recv(self) -> bytes:
        # 读取消息长度（4 字节）
        length_bytes = self._recv_exact(4)
        length = int.from_bytes(length_bytes, 'big')

        # 读取消息体
        data = self._recv_exact(length)
        return data

    def _recv_exact(self, n: int) -> bytes:
        # 确保读取恰好 n 个字节
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError('Connection closed')
            data += chunk
        return data
```

### 好在哪

1. **长度前缀**——每条消息前 4 字节是长度，避免粘包问题
2. **精确读取**——`_recv_exact` 确保读取恰好 n 字节，不多不少
3. **错误处理**——连接关闭时抛出异常

### 模式

**Length-Prefixed Framing**——用长度前缀分隔消息帧，TCP 通信的标准做法。

### 骨架代码

```python
# 你的项目中：用同样的模式处理 TCP 消息
class MessageFramer:
    def __init__(self, socket):
        self.socket = socket

    def send(self, data: bytes):
        # 发送：长度前缀 + 消息体
        length = len(data).to_bytes(4, 'big')
        self.socket.sendall(length + data)

    def recv(self) -> bytes:
        # 接收：先读长度，再读消息体
        length_bytes = self._recv_exact(4)
        length = int.from_bytes(length_bytes, 'big')
        return self._recv_exact(length)

    def _recv_exact(self, n: int) -> bytes:
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError('Connection closed')
            data += chunk
        return data
```

## 消息类型

IBKR API 定义了 100+ 种消息类型，每种有唯一的数字 ID：

| 消息类型 | ID | 方向 | 说明 |
|---------|-----|------|------|
| `reqMktData` | 1 | Client→TWS | 请求行情 |
| `tickPrice` | 1 | TWS→Client | 行情价格 |
| `tickSize` | 2 | TWS→Client | 行情数量 |
| `placeOrder` | 3 | Client→TWS | 下单 |
| `orderStatus` | 3 | TWS→Client | 订单状态 |
| `reqExecutions` | 7 | Client→TWS | 请求成交记录 |
| `execDetails` | 11 | TWS→Client | 成交详情 |

## 总结

Client 和 Decoder 是 ib_async 的通信层——Client 负责编码和发送，Decoder 负责接收和解码。核心设计：

- **二进制协议**——所有字段用 `\0` 分隔，紧凑高效
- **长度前缀**——4 字节长度头，避免 TCP 粘包
- **消息类型 ID**——每种消息有唯一数字 ID
- **回调分发**——Decoder 解码后调用 Wrapper 的对应方法
