# nanobot 源码阅读（五）：Channel 系统——15+ 平台的统一抽象

> 基于 nanobot v0.2.1。

## 问题：Telegram 和 Discord 的 API 完全不同，怎么统一

nanobot 支持 Telegram、Discord、Slack、Feishu（飞书）、WeChat（微信）、QQ、DingTalk（钉钉）、WhatsApp、Signal、Matrix、Email、MS Teams、MoChat、WebSocket（WebUI）——超过 15 个平台。

每个平台的 SDK 不同、消息格式不同、streaming 支持不同。nanobot 的设计是：**每个平台只实现三个方法**——`start()`、`stop()`、`send()`。

## BaseChannel 接口

```python
# nanobot/channels/base.py
class BaseChannel(ABC):
    name: str = "base"
    display_name: str = "Base"

    # 可选覆盖的布尔标记
    send_progress: bool = True       # 是否发送工具进度通知
    send_tool_hints: bool = False    # 是否发送工具提示
    show_reasoning: bool = True      # 是否显示思考过程

    @abstractmethod
    async def start(self) -> None:
        """连接平台，开始监听消息"""

    @abstractmethod
    async def stop(self) -> None:
        """断开连接，清理资源"""

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """发送一条消息"""

    # 可选覆盖的方法
    async def send_delta(self, chat_id, delta, metadata=None) -> None:
        """发送流式文本片段"""
        pass  # 默认 no-op，不支持 streaming

    async def send_reasoning_delta(self, chat_id, delta, metadata=None) -> None:
        """发送思考过程片段"""
        pass  # 默认 no-op
```

注意 `send_delta` 和 `send_reasoning_delta` 默认都是 no-op——不是所有平台都支持 streaming。Channel 自己决定要不要支持。

### 怎么判断是否支持 streaming

```python
@property
def supports_streaming(self) -> bool:
    cfg = self.config
    streaming = cfg.get("streaming", False) if isinstance(cfg, dict) else getattr(cfg, "streaming", False)
    return bool(streaming) and type(self).send_delta is not BaseChannel.send_delta
```

两个条件：配置文件开了 `streaming: true` **且** 子类重写了 `send_delta`。配置文件可以关掉 streaming（比如某些企业微信通道不支持），但即使开了，如果子类没实现 `send_delta`，也不会尝试。

## 消息入口：`_handle_message()`

每个 Channel 子类在自己的 `start()` 循环中收到消息后，调用基类的 `_handle_message()`：

```python
async def _handle_message(
    self, sender_id, chat_id, content, media=None, metadata=None, ...
) -> None:
    # 1. 权限检查
    if not self.is_allowed(sender_id):
        if is_dm:
            # DM 里发送配对码
            code = generate_code(self.name, str(sender_id))
            await self.send(OutboundMessage(
                channel=self.name, chat_id=str(chat_id),
                content=format_pairing_reply(code),
                metadata={PAIRING_CODE_META_KEY: code},
            ))
        return

    # 2. 如果 channel 支持 streaming，标记 _wants_stream
    meta = metadata or {}
    if self.supports_streaming:
        meta = {**meta, "_wants_stream": True}

    # 3. 封装 InboundMessage，发到 MessageBus
    msg = InboundMessage(
        channel=self.name,
        sender_id=str(sender_id),
        chat_id=str(chat_id),
        content=content,
        media=media or [],
        metadata=meta,
    )
    await self.bus.publish_inbound(msg)
```

### 权限模型：星号 > allowlist > pairing store

```python
def is_allowed(self, sender_id: str) -> bool:
    allow_list = ...  # config 中的 allow_from
    if "*" in allow_list:
        return True         # 所有人允许
    if str(sender_id) in allow_list:
        return True         # 在允许列表里
    if is_approved(self.name, str(sender_id)):
        return True         # 之前配对过
    return False
```

不在 allowlist 里的用户发 DM 会收到一个配对码——用户把配对码发回给 bot 就完成了配对（和 Telegram bot 的 `/start` 类似）。

## ChannelManager：协调者

```python
# nanobot/channels/manager.py
class ChannelManager:
    def __init__(self, config, bus, ...):
        self.channels: dict[str, BaseChannel] = {}
        self._init_channels()       # 初始化所有 enabled channel

    def _init_channels(self):
        # 1. 用 pkgutil 发现所有已注册的 channel 模块
        names = discover_channel_names()
        # 2. 只导入 enabled=True 的 channel
        for name, cls in discover_enabled(enabled_names).items():
            channel = cls(section, self.bus)
            self.channels[name] = channel
```

和 Tool 系统一样的自动发现模式——`pkgutil.iter_modules` 扫描 `nanobot/channels/`，找出所有 `BaseChannel` 子类。

### 出站分发：`_dispatch_outbound()`

```python
async def _dispatch_outbound(self):
    while True:
        msg = await self.bus.consume_outbound()

        # 1. reasoning 消息单独路由
        if msg.metadata.get("_reasoning_delta"):
            channel = self.channels.get(msg.channel)
            if channel and channel.show_reasoning:
                await self._send_with_retry(channel, msg)
            continue

        # 2. progress 消息检查 send_progress / send_tool_hints
        if msg.metadata.get("_progress"):
            if not self._should_send_progress(msg.channel, ...):
                continue  # 静默丢弃

        # 3. stream delta 合并
        if msg.metadata.get("_stream_delta"):
            msg, extra = self._coalesce_stream_deltas(msg)

        # 4. 发送
        channel = self.channels.get(msg.channel)
        if channel:
            await self._send_with_retry(channel, msg)
```

### Stream Delta 合并

LLM 生成速度快于网络发送速度时，队列里会积压多个 delta。`_coalesce_stream_deltas()` 把同一个 `(channel, chat_id)` 的连续 delta 合并成一条消息——减少 API 调用次数：

```python
def _coalesce_stream_deltas(self, first_msg):
    combined = first_msg.content
    while True:
        next_msg = self.bus.outbound.get_nowait()
        if same_target and next_msg.metadata.get("_stream_delta"):
            combined += next_msg.content
            if next_msg.metadata.get("_stream_end"):
                break  # stream 结束
        else:
            # 遇到非 delta 消息，停止合并
            non_matching.append(next_msg)
            break
    return merged, non_matching
```

### 发送重试

```python
_SEND_RETRY_DELAYS = (1, 2, 4)  # 指数退避

async def _send_with_retry(self, channel, msg):
    for attempt in range(max_attempts):
        try:
            await self._send_once(channel, msg)
            return
        except Exception as e:
            await asyncio.sleep(_SEND_RETRY_DELAYS[attempt])
    logger.exception("Failed to send after {} attempts", max_attempts)
```

## WebSocket Channel：WebUI 的特殊通道

WebSocket channel 是所有 channel 里最复杂的——它不仅传递文本消息，还要传递：

- 文件编辑事件（`_file_edit_events`）
- Token 用量统计
- Session 列表更新
- 运行时模型切换通知

这些通过 `OutboundMessage.metadata` 中的 `_agent_ui` 键传递结构化 payload：

```python
# nanobot/bus/events.py
OUTBOUND_META_AGENT_UI = "_agent_ui"
# WebUI client 解析这个键来渲染富 UI 组件
```

## 小结

Channel 系统的设计哲学是**最小接口 + 可选能力发现**：

| 机制 | 作用 |
|---|---|
| `start/stop/send` | 必须实现的三个方法 |
| `send_delta` 默认 no-op | streaming 是可选能力 |
| `send_reasoning_delta` 默认 no-op | 思考过程展示是可选能力 |
| `supports_streaming` 属性 | 运行时能力发现 |
| `_coalesce_stream_deltas` | 吞吐优化 |
| `_send_with_retry` | 发送可靠性 |

加一个新平台只需要：创建一个 `BaseChannel` 子类、实现三个方法、在 config 里加一行——不用改 AgentLoop、不用改 Tool、不用改其他 Channel。

下一篇讲 WebUI 与 Gateway——前后端 WebSocket 多路复用协议。
