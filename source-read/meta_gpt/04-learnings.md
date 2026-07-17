# MetaGPT 源码阅读（四）：值得学的 8 个设计

> 基于 MetaGPT 最新版本。

前三篇分析了 MetaGPT 的 Role-Action-Environment 架构。这一篇从代码层面提炼出值得学习的**设计模式、编码习惯、工程实践**。不只是"MetaGPT 做了什么"——是"你写 Python 项目时可以怎么借鉴"。

## 1. Pydantic 驱动一切：声明式优于命令式

MetaGPT 里几乎所有核心类都是 Pydantic `BaseModel`：

```python
class Role(BaseModel): ...
class Action(BaseModel): ...
class Memory(BaseModel): ...
class Message(BaseModel): ...
class RoleContext(BaseModel): ...
class LLMConfig(BaseModel): ...
```

这意味着：
- **类型安全**：所有字段自动校验。`Role(name=123)` 会报错，不需要手写 `isinstance` 检查。
- **自动序列化**：`model_dump()` 和 `model_load()` 开箱即用。Role 的序列化/恢复不需要手写 JSON 序列化。
- **默认值声明式**：`Field(default=..., description=...)` 一目了然，不需要在 `__init__` 里写 `self.x = x or default`。

**你可以这么用**：任何涉及配置、数据模型的 Python 项目，用 Pydantic 替代手写的 dataclass 或 dict。类型校验、序列化、文档生成一次搞定。

```python
# 不要这样
class Config:
    def __init__(self, host=None, port=None):
        self.host = host or "localhost"
        self.port = port or 8080
        if not isinstance(self.port, int):
            raise TypeError("port must be int")

# 这样
from pydantic import BaseModel, Field
class Config(BaseModel):
    host: str = Field(default="localhost", description="服务器地址")
    port: int = Field(default=8080, ge=1, le=65535)
```

## 2. 模板方法模式：框架定义骨架，用户填空

Role 的 `react()` 方法定义了 Agent 生命周期，但具体的观察、思考、执行逻辑由子类提供：

```python
# 框架定义骨架（Role）
async def react(self) -> Message:
    while True:
        await self._observe()     # 子类可覆盖
        has_todo = await self._think()  # 子类可覆盖
        if not has_todo: break
        await self._act()         # 子类可覆盖
```

Engineer 覆盖了 `_think()` 加入 bug 检查逻辑，覆盖了 `_init_actions()` 注册工程相关技能。QAEngineer 覆盖为测试相关逻辑。但循环结构不变。

**你可以这么用**：当你发现自己在多个类似的类中重复相同的控制流时——提取模板方法。父类定义"先做什么、后做什么"，子类只实现"具体怎么做"。

## 3. 策略模式：三种 React 模式可插拔

```python
# 策略接口（RoleReactMode 枚举）
class RoleReactMode(str, Enum):
    REACT = "react"
    BY_ORDER = "by_order"
    PLAN_AND_ACT = "plan_and_act"

# Context（Role.react）
async def react(self) -> Message:
    if self.rc.react_mode == RoleReactMode.REACT:
        rsp = await self._react()          # 策略 1
    elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
        rsp = await self._plan_and_act()   # 策略 2
    # ... 加新策略只需要加一个 elif
```

三种策略在 Role 中随时切换——不需要改 Role 的代码，只需要改 `react_mode` 字段。这是开闭原则（对扩展开放、对修改关闭）的教科书实现。

**你可以这么用**：当一段代码里有多个 `if mode == "A"` 的分支且每个分支实现完全不同时——把这些分支提取为策略类或策略方法。加新模式不需要改调用方。

## 4. Observer 模式 + 消息类型系统

```python
# 订阅（Observer 注册）
engineer._watch([WriteDesign, WriteTasks, FixBug])

# 通知（Subject 广播）
environment.publish_message(msg)  # → 所有 Role 的 msg_buffer

# 过滤（Observer 自行判断是否感兴趣）
self.rc.news = [
    n for n in news 
    if n.cause_by in self.rc.watch   # "这条消息和我有关吗？"
]
```

关键是 `cause_by` 不是字符串匹配，是**类型引用**。如果手误写了 `WirteDesign`（拼写错误），IDE 和类型检查器会直接报错——不会出现"静默忽略消息"的 bug。

**你可以这么用**：不要用字符串做消息类型标签。用类引用（`WriteDesign` 而不是 `"write_design"`）——编译期安全，IDE 有跳转和自动补全。

## 5. Action-as-Data：Action 不是函数调用

传统的 Agent 框架里，"写代码"是一个函数：

```python
def write_code(requirement: str) -> str:
    prompt = build_prompt(requirement)
    return llm.call(prompt)
```

MetaGPT 里它是一个 Pydantic model：

```python
class WriteCode(Action):
    name: str = "WriteCode"
    prefix: str = "You are a professional engineer."
    i_context: CodingContext = None   # 输入 Schema
    node: ActionNode = None           # 输出 Schema
    
    async def run(self, history, **kwargs) -> ActionOutput:
        prompt = self._build_prompt(history)
        return await self.llm.aask(prompt)
```

区别在哪：
- Action 可以**序列化**、**传输**、**延迟执行**（函数不能）
- Action 自带**元数据**（name、desc、prefix）——给其他 Agent 或 SkillManager 用的
- Action 的输入/输出通过 `ActionNode` **Schema 化**——LLM 的返回可以被强制格式化为 JSON

**你可以这么用**：当"一个操作"有元数据（名称、描述、示例）、有可配置参数、需要被调度或序列化时——把它建模为对象而不是函数。

## 6. tenacity 重试：指数退避 + 随机抖动

MetaGPT 的 LLM 调用全部用 `tenacity` 包了重试：

```python
from tenacity import (
    retry, stop_after_attempt, wait_random_exponential,
    retry_if_exception_type, after_log
)

@retry(
    stop=stop_after_attempt(3),           # 最多 3 次
    wait=wait_random_exponential(min=1, max=60),  # 1s → 2s → 4s ± 随机抖动
    retry=retry_if_exception_type(openai.RateLimitError),  # 只在限流时重试
    after=after_log(logger, logging.WARNING)  # 重试时打日志
)
async def aask(self, messages, ...):
    return await self.aclient.chat.completions.create(...)
```

关键设计：`wait_random_exponential` 不是固定 `[1, 2, 4]` 秒——加了**随机抖动**（jitter）。这防止了多个并发请求在同一毫秒重试，导致"惊群效应"（thundering herd）——所有请求都在第 4 秒同时重试，再次触发限流。

**你可以这么用**：任何涉及外部 API 调用的代码，都应该有用 tenacity 的重试。三个核心参数：最多试几次、退避策略（指数+抖动）、重试条件（只在特定异常时重试）。

## 7. 消息去重：不要信外部输入

```python
class Memory(BaseModel):
    def add(self, message: Message):
        if message in self.storage:   # ← 关键：去重
            return
        self.storage.append(message)
```

如果你依赖 `id` 做去重：

```python
if message.id not in self.seen_ids:
    self.seen_ids.add(message.id)
    self.storage.append(message)
```

MetaGPT 用了值比较（`message in self.storage`）而不是 id 比较——因为同一个消息可能被多个 Environment 多次推送。这是防御性编程：**永远假设消息可能被重复投递**。

**你可以这么用**：在处理外部输入（消息队列、API 回调、事件流）时，永远加去重逻辑。至少一次投递（at-least-once delivery）是分布式系统的常态。

## 8. 配置的分层加载

```python
# 优先级：环境变量 > YAML 配置文件 > 默认值
class LLMConfig(BaseModel):
    api_key: str = Field(default="")
    model: str = Field(default="gpt-4")
    base_url: str = Field(default="https://api.openai.com/v1")
    
    def __init__(self, **kwargs):
        # 环境变量覆盖
        kwargs.setdefault("api_key", os.environ.get("OPENAI_API_KEY", ""))
        super().__init__(**kwargs)
```

配置有三个来源，优先级清晰：命令行参数 > 环境变量 > 配置文件 > 默认值。字段通过 Pydantic 的 `Field(default=...)` 定义默认值，YAML 文件通过 `config2.yaml` 加载，环境变量在 `__init__` 中注入。

**你可以这么用**：任何有配置的项目，用 Pydantic Settings（`pydantic-settings`）管理配置分层：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {"env_prefix": "APP_", "env_file": ".env"}
    
    database_url: str = "postgres://localhost:5432/app"
    port: int = 8080
    debug: bool = False
```

## 全局架构选择：Pydantic 的分寸

MetaGPT 的一个值得讨论的架构选择：**Pydantic 用得很重**。Role、Action、Memory、Message 全是 BaseModel——这意味着每次创建对象都有 Pydantic 的校验开销。对于高性能场景（如实时推理），这可能是个瓶颈。

但对于这个项目的场景（LLM 调用的延迟是秒级），Pydantic 的开销完全可以忽略——而它带来的类型安全、序列化、文档生成的价值远大于性能损失。

**判断标准**：如果 I/O 延迟（LLM 调用、数据库查询）是你的系统瓶颈，Pydantic 的开销可以忽略。如果计算密集型且对象创建频率极高（每秒百万次），裸 dataclass 或 namedtuple 更合适。

## 小结：8 个你能直接用的

| # | 模式 | 一句话 | 适用场景 |
|---|---|---|---|
| 1 | Pydantic 建模 | 用 BaseModel 替代手写 dataclass | 任何有配置/模型的 Python 项目 |
| 2 | 模板方法 | 父类定义流程，子类实现细节 | 多个类共享相同控制流 |
| 3 | 策略模式 | 枚举 + 方法分支切换行为 | 运行时可切换的行为 |
| 4 | Observer + 类型标签 | `cause_by` 用类引用不用字符串 | 消息订阅、事件驱动 |
| 5 | Action-as-Data | 把操作建模为对象而非函数 | 需要序列化/调度/描述的操作用 |
| 6 | tenacity 退避 | `wait_random_exponential` | 所有外部 API 调用 |
| 7 | 消息去重 | 值比较优于 id 比较 | 消息队列、事件驱动 |
| 8 | 配置分层 | 命令行 > 环境变量 > YAML > 默认值 | 所有需要配置的项目 |

---

## 系列回顾

| 篇 | 内容 | 核心收获 |
|---|---|---|
| 一 | 架构总览 | Role → _observe → _think → _act 三角 |
| 二 | Role 系统 | 三种 react 模式 + RoleContext 状态管理 |
| 三 | 消息系统 | cause_by 类型标签 + watch 订阅模式 |
| 四 | 好代码分析 | 8 个设计模式 + 编码实践 |

MetaGPT 最核心的设计哲学：**把 Agent 做成 Pydantic model——类型安全、可序列化、声明式配置、自带文档**。这个哲学贯穿了整个 22 万行代码。
