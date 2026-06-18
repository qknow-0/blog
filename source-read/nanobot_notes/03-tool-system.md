# nanobot 源码阅读（三）：Tool 系统——插件化的工具注册与执行

> 基于 nanobot v0.2.1。

## 问题：怎么让工具可以像插件一样加入和移除

nanobot 的内置工具有十几个：`read_file`、`write_file`、`edit_file`、`exec`、`web_search`、`web_fetch`、`grep`、`find_files`、`cron`、`spawn`（子 agent）、`generate_image`……还有用户通过 MCP 协议接入的外部工具。

设计目标：
1. **自动发现**：加一个 .py 文件就能注册新工具
2. **上下文注入**：工具需要知道当前 channel、session、workspace 等信息
3. **参数校验**：在调用前捕获参数错误，而不是等 LLM 收到错误结果再重试
4. **并发执行**：一个 LLM 返回多个 tool_call 时，可以并发执行

## Tool 基类

```python
# nanobot/agent/tools/base.py
class Tool(ABC):
    name: str                        # 工具名（暴露给 LLM）
    description: str                 # 工具描述
    parameters: dict[str, Any]       # JSON Schema 参数定义

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具，返回结果（字符串或可序列化对象）"""

    def to_schema(self) -> dict[str, Any]:
        """转为 OpenAI function 格式的 JSON Schema"""

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool:
        """是否应该注册此工具（默认为 True，子类可重写来按条件禁用）"""

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        """工厂方法：从 ToolContext 创建工具实例"""
```

最简洁的工具实现——`web_search`：

```python
class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web using DuckDuckGo"

    def __init__(self, config):
        self.max_results = config.web.max_results

    @tool_parameters(...)  # 声明式参数定义
    async def execute(self, query: str, max_results: int = 10) -> str:
        results = await search_web(query, max_results)
        return format_results(results)
```

## ToolLoader：自动发现

关键代码在 `ToolLoader.discover()`：

```python
# nanobot/agent/tools/loader.py
def discover(self) -> list[type[Tool]]:
    for _importer, module_name, _ispkg in pkgutil.iter_modules(self._package.__path__):
        if module_name.startswith("_") or module_name in _SKIP_MODULES:
            continue
        module = importlib.import_module(f".{module_name}", self._package.__name__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Tool)
                and attr is not Tool     # 跳过基类自身
                and not attr_name.startswith("_")
                and not getattr(attr, "__abstractmethods__", None)  # 跳过抽象类
                and getattr(attr, "_plugin_discoverable", True)     # 可选择性隐藏
            ):
                results.append(attr)
```

用 `pkgutil.iter_modules` 扫描 `nanobot/agent/tools/` 目录，然后对每个模块用 `dir()` 找出 `Tool` 的子类。零配置——新增一个 .py 文件，定义一个 `Tool` 子类，它就被自动注册了。

外部插件也支持：通过 Python 的 `entry_points` 机制（`nanobot.tools` group），第三方包可以注册自己的工具。

### 名字冲突处理

```python
# builtin 和 plugin 出现同名工具时的策略
if registry.has(tool.name):
    if is_plugin_source and tool.name in builtin_names:
        logger.warning("Plugin %s skipped: conflicts with built-in tool %s", ...)
        continue  # plugin 不能覆盖 builtin
    logger.warning("Tool name collision: %s overwrites existing", ...)
    # builtin 间冲突：后注册覆盖先注册
registry.register(tool)
```

## ToolRegistry：参数校验与执行

```python
# nanobot/agent/tools/registry.py
async def execute(self, name: str, params: Any) -> Any:
    tool, params, error = self.prepare_call(name, params)
    if error:
        return error + "\n\n[Analyze the error above and try a different approach.]"
    result = await tool.execute(**params)
    if isinstance(result, str) and result.startswith("Error"):
        return result + "\n\n[Analyze the error above and try a different approach.]"
    return result
```

注意 `prepare_call()` 做的事：
1. 按名字查找工具（找不到时给相似名字建议）
2. `_coerce_params()`——把字符串 JSON 解析为 dict（LLM 可能返回 JSON 字符串而不是 object）
3. `tool.cast_params()`——类型转换（Pydantic 模型验证）
4. `tool.validate_params()`——业务校验

所有错误都返回字符串 `"Error: ..."` 而不是抛异常——这让 LLM 能看到错误信息并尝试修正，而不是中断整个 turn。

### 定义缓存

```python
def get_definitions(self) -> list[dict[str, Any]]:
    if self._cached_definitions is not None:
        return self._cached_definitions
    # builtins 按名字排序作为稳定前缀，MCP 工具追加在后
    # 排序保证每次发给 LLM 的工具列表顺序一致 → 对 prompt cache 友好
```

每次 `register()`/`unregister()` 会让缓存失效，确保定义列表始终正确。

## 并发工具执行

AgentRunner 支持 `concurrent_tools=True`——当 LLM 一次返回多个 tool_call 时，可以并发执行它们：

```python
# nanobot/agent/runner.py（简化版）
async def _execute_tools(self, tool_calls, ...):
    if self.spec.concurrent_tools and len(tool_calls) > 1:
        results = await asyncio.gather(*[
            self.tools.execute(tc.name, tc.arguments)
            for tc in tool_calls
        ])
    else:
        results = [await self.tools.execute(tc.name, tc.arguments)
                   for tc in tool_calls]
```

## Shell 工具的安全边界

`exec` 工具是最危险的——用户可以让 LLM 运行任意 shell 命令。nanobot 有三层防护：

1. **Sandbox 包装**：`wrap_command()` 可以用 bubblewrap/firejail 等沙箱执行
2. **Allow/Deny 模式**：`allow_patterns` 和 `deny_patterns` 做命令白名单/黑名单
3. **Workspace 隔离**：`restrict_to_workspace` 防止命令访问 workspace 外的路径

```python
# nanobot/agent/tools/shell.py
# 跨 workspace 边界的操作被硬拒绝
_WORKSPACE_BOUNDARY_NOTE = (
    "\n\nNote: this is a hard policy boundary, not a transient failure. "
    "Do NOT retry with shell tricks (symlinks, base64 piping, ...)."
)
```

## ContextAware 接口：让工具知道"自己在哪里"

```python
# nanobot/agent/tools/context.py
class ContextAware(ABC):
    def set_context(self, ctx: RequestContext) -> None:
        """工具实例化后注入运行时上下文"""
```

每次 turn 开始前，AgentLoop 调用 `_set_tool_context()` 把所有已注册的 `ContextAware` 工具更新一遍——注入当前的 channel、chat_id、session_key 等信息。

## 小结

Tool 系统的设计要点：

| 机制 | 实现 |
|---|---|
| 自动发现 | `pkgutil.iter_modules` 扫描 + `entry_points` 插件 |
| 运行时上下文 | `ContextAware` + `set_context()` |
| 参数校验 | `prepare_call()` 链：查找→JSON 解析→类型转换→验证 |
| 并发执行 | `asyncio.gather` 并行执行多个 tool_call |
| 安全边界 | sandbox + allow/deny 模式 + workspace 隔离 |
| 错误处理 | 返回错误字符串而非抛异常，让 LLM 可自纠正 |

下一篇讲 Session 与 Memory——nanobot 如何持久化对话历史，以及 Dream 记忆巩固的工作原理。
