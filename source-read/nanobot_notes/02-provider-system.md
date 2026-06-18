# nanobot 源码阅读（二）：Provider 系统——一套接口支持十几个 LLM

> 基于 nanobot v0.2.1。

## 问题：怎么让用户随意换模型而不改代码

nanobot 支持的 LLM 后端超过 10 个：

```
Anthropic (Claude)  → 直接 SDK 集成
OpenAI Compat       → 任何兼容 OpenAI API 的服务
OpenAI Codex        → OpenAI Codex CLI 接口
Azure OpenAI        → 微软 Azure
AWS Bedrock         → Amazon Bedrock
GitHub Copilot      → Copilot Chat API
```

用户还要能配置 `fallback_models`——主模型挂了自动切备用模型。每个 provider 还有不同的 generation 参数（max_tokens、temperature、reasoning_effort）。

nanobot 的解法分三层：

1. **LLMProvider 基类**——定义统一接口
2. **Factory + Registry**——从 config 创建 provider，支持插件扩展
3. **FallbackProvider**——透明 failover wrapper

## LLMProvider 基类

```python
# nanobot/providers/base.py
class LLMProvider(ABC):
    def __init__(self, api_key=None, api_base=None):
        self.api_key = api_key
        self.api_base = api_base
        self.generation = GenerationSettings()  # max_tokens, temperature 等

    @abstractmethod
    async def chat(
        self, model, messages, tools=None, tool_choice=None, ...
    ) -> LLMResponse:
        """发送消息到 LLM，返回 LLMResponse"""

    # 可选覆盖
    async def stream(self, ...):
        """流式聊天，默认 fallback 到 chat()"""

    def get_default_model(self) -> str:
        """返回此 provider 的默认模型名"""
```

所有 provider 只实现 `chat()` 一个核心方法。输入是标准化的 `messages` 列表（OpenAI 格式），输出是统一的 `LLMResponse`：

```python
@dataclass
class LLMResponse:
    content: str | None                    # 文本回复
    finish_reason: str                     # "completed" | "tool_call" | "error"
    tool_calls: list[ToolCallRequest]      # 工具调用请求
    usage: dict[str, int]                  # token 用量
    reasoning_content: str | None          # 推理内容（DeepSeek-R1 等）
```

`stream()` 默认 fallback 到 `chat()`——不需要每个 provider 都实现流式。AnthropicProvider 重写了它来用 SSE streaming，OpenAICompatProvider 也有自己的 stream 实现。

## Factory：从 config 到 provider 实例

`make_provider()` 是整个系统的唯一入口：

```python
# nanobot/providers/factory.py
def make_provider(config, *, preset_name=None, preset=None, model=None) -> LLMProvider:
    resolved = _resolve_model_preset(config, preset_name=preset_name, preset=preset)
    provider = _make_provider_core(config, preset=preset)  # 创建核心 provider
    fallback_presets = _resolve_fallback_presets(config, resolved)

    if fallback_presets:
        # 有 fallback → 包一层 FallbackProvider
        provider = FallbackProvider(
            primary=provider,
            fallback_presets=fallback_presets,
            provider_factory=lambda fb: _make_provider_core(config, preset=fb),
        )
    return provider
```

核心决策在 `_make_provider_core()`，通过一个 `backend` 分发：

```python
if backend == "anthropic":
    provider = AnthropicProvider(api_key=..., api_base=..., default_model=model)
elif backend == "azure_openai":
    provider = AzureOpenAIProvider(...)
elif backend == "bedrock":
    provider = BedrockProvider(...)
else:
    provider = OpenAICompatProvider(...)  # 兜底
```

注意 else 分支的处理——任何未知的 provider 名（包括用户自定义的 OpenAI-compatible endpoint）都走 `OpenAICompatProvider`。这大大降低了添加新后端的门槛。

## Registry：provider 插件发现

```python
# nanobot/providers/registry.py
# 内置 provider 注册表
_builtin_providers = {
    "openai": ProviderSpec(backend="openai_compat", ...),
    "anthropic": ProviderSpec(backend="anthropic", ...),
    "azure": ProviderSpec(backend="azure_openai", ...),
    "bedrock": ProviderSpec(backend="bedrock", ...),
    "github_copilot": ProviderSpec(backend="github_copilot", ...),
    # ... 更多
}
```

`find_by_name()` 先查内置表，查不到就尝试动态创建一个 `ProviderSpec`——这使得用户只需在 config 里写 `provider: "my_custom_endpoint"` + `api_base: "https://..."` 就能接入任意兼容 OpenAI API 的服务。

## FallbackProvider：透明故障转移

这是 nanobot 最巧妙的设计之一。`FallbackProvider` 本身实现了 `LLMProvider` 接口，但对调用方完全透明：

```python
# nanobot/providers/fallback_provider.py
class FallbackProvider(LLMProvider):
    def __init__(self, primary, fallback_presets, provider_factory):
        self._primary = primary
        self._fallback_presets = fallback_presets
        self._factory = provider_factory  # 懒创建 fallback provider
        self._primary_failure_count = 0
        self._primary_cooldown_until = 0
```

### 故障分类

不是所有错误都该 failover。认证失败、权限错误不应该切模型——那是配置问题，切了也没用：

```python
_FALLBACK_ERROR_KINDS = {"timeout", "connection", "server_error", "rate_limit", "overloaded"}
_NON_FALLBACK_ERROR_KINDS = {"authentication", "auth", "permission", "content_filter", "refusal"}
```

### Circuit Breaker

主模型连续失败 3 次后，进入 60 秒冷却期——这期间请求直接走 fallback，不给主模型试了：

```python
_PRIMARY_FAILURE_THRESHOLD = 3
_PRIMARY_COOLDOWN_S = 60

async def chat(self, model, messages, ...):
    if self._primary_in_cooldown():
        return await self._try_fallback(...)  # 直接跳过主模型

    try:
        return await self._primary.chat(model, messages, ...)
    except Exception as e:
        if self._is_fallbackable(e):
            self._primary_failure_count += 1
            return await self._try_fallback(...)
        raise  # 不可 fallback → 向上抛
```

### 流式 timeout 的特殊处理

如果主模型已经开始 streaming 内容了才 timeout，failover 后不应该把流了一半的内容再发一遍。`FallbackProvider` 的做法是：结束当前 stream segment，在新的 segment 里继续 failover 后的内容。

## ProviderSnapshot：热切换模型的机制

回顾第一篇文章里 AgentLoop 的 `_refresh_provider_snapshot()`：

```python
# nanobot/providers/factory.py
@dataclass(frozen=True)
class ProviderSnapshot:
    provider: LLMProvider
    model: str
    context_window_tokens: int
    signature: tuple[object, ...]   # 用于判断配置是否变化
```

`signature` 是一个 tuple，编码了所有影响 provider 行为的配置字段。`_refresh_provider_snapshot()` 周期性地用 `signature` 比对来判断配置是否变了——变了就热切换 provider，不需要重启。

```python
# nanobot/agent/loop.py
def _refresh_provider_snapshot(self) -> None:
    snapshot = self._provider_snapshot_loader()
    if snapshot.signature == self._provider_signature:
        return  # 没变，什么都不做
    self._apply_provider_snapshot(snapshot)  # 热切换
```

## GenerationSettings：统一 generation 参数

```python
# nanobot/providers/base.py
@dataclass
class GenerationSettings:
    max_tokens: int = 4096
    temperature: float | None = None
    top_p: float | None = None
    reasoning_effort: str | None = None
    min_p: float | None = None
    top_k: int | None = None
```

每个 provider 在 `chat()` 时自己决定如何使用这些参数——Anthropic 用 `max_tokens`，OpenAI 也用 `max_tokens`，但实现细节不同。`GenerationSettings` 只是配置的容器，不强制行为。

## 小结

Provider 系统的设计哲学是**最小接口 + 组合优于继承**：

| 机制 | 作用 |
|---|---|
| LLMProvider 基类 | 统一 `chat()` 接口 |
| Factory + Registry | 声明式创建，支持动态扩展 |
| FallbackProvider | 透明 failover + circuit breaker |
| ProviderSnapshot | 零停机热切换模型 |
| GenerationSettings | 统一参数，各 provider 自行解释 |

下一篇讲 Tool 系统——nanobot 如何自动发现、注册、执行工具，以及并发工具调用的实现。
