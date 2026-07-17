# MetaGPT 源码阅读（二）：Role 系统——一个 Agent 的内部运作

> 基于 MetaGPT 最新版本。

## Role 不只是"一个 Agent"

大多数 AI Agent 框架里的 Agent 就是一个 while 循环 + 工具调用。MetaGPT 的 Role 远不止于此——它是一个**有状态、有记忆、有自我认知、能自主决定下一步的完整实体**。

```python
class Role(BaseRole, SerializationMixin, ContextMixin, BaseModel):
    # 自我认知
    name: str = ""           # 我叫什么
    profile: str = ""        # 我的角色（"产品经理"）
    goal: str = ""           # 我的目标
    constraints: str = ""    # 我的限制条件
    
    # 能力
    actions: list[Action] = []   # 我会什么
    
    # 运行时状态
    rc: RoleContext = ...        # 上下文（消息缓冲、记忆、状态）
    react_mode: RoleReactMode    # 决策模式
    planner: Planner             # 规划器（PLAN_AND_ACT 模式用）
```

## RoleContext：运行时状态的容器

```python
class RoleContext(BaseModel):
    env: BaseEnvironment = None       # 我属于哪个 Environment
    msg_buffer: MessageQueue = ...    # 消息接收缓冲区（异步追加）
    memory: Memory = ...              # 持久记忆（保存到 storage）
    working_memory: Memory = ...      # 工作记忆（当前任务）
    state: int = -1                   # 当前状态（对应 actions 索引）
    todo: Action = None               # 当前要执行的 Action
    watch: set[str] = set()           # 我关注的消息类型
```

关键设计：

**① `msg_buffer` vs `memory`**

`msg_buffer` 是**接收缓冲区**——Environment 把消息推到这里。`memory` 是**持久记忆**——_observe 把消息从 buffer 搬到 memory 后，这些消息就"永久"留在对话历史里。两者分离的好处：接收和存储是两个独立的阶段，不会因为 memory 写入失败而丢消息。

**② `state` 映射到 `actions`**

```python
def _set_state(self, state: int):
    self.rc.state = state
    if state == -1:
        self.set_todo(None)       # 终止状态
    else:
        self.set_todo(self.actions[state])  # state → action
```

state 就是 actions 列表的索引。最简单的 Role 只有 1 个 action——永远在 state 0。复杂的 Role（如 Engineer）有 5+ 个 action——LLM 在 _think 中动态选择 state。

**③ `watch` 实现消息过滤**

```python
# Engineer 的 watch 集合
self._watch([WriteDesign, WriteTasks, FixBug, ...])
# 只有 cause_by 在这些类型里的消息才会被 _observe 接收
```

## 三种 React 模式：怎么决策"下一步做什么"

### REACT：让 LLM 动态选择

```python
# 默认模式。_think 用 LLM 选择下一个 state
async def _think(self) -> bool:
    prompt = STATE_TEMPLATE.format(
        history=self.rc.history,
        states="\n".join(self.states),      # ["0. WriteCode", "1. WriteTest", "2. DebugError"]
        n_states=len(self.states) - 1,
        previous_state=self.rc.state,
    )
    next_state = await self.llm.aask(prompt)
    self._set_state(int(next_state))
    return True
```

LLM 看到它的 actions 列表和历史对话，自己决定下一步该做什么。这相当于让 Agent **自己去判断"现在该写代码还是该修 bug"**。

### BY_ORDER：严格顺序执行

```python
if self.rc.react_mode == RoleReactMode.BY_ORDER:
    self._set_state(self.rc.state + 1)  # 直接下一个 state
```

不需要 LLM 决策——按 actions 的定义顺序逐个执行。适合流程固定、不需要动态决策的场景。

### PLAN_AND_ACT：先规划再执行

```python
async def _plan_and_act(self) -> Message:
    # 先制定计划
    goal = self.rc.memory.get()[-1].content
    await self.planner.update_plan(goal=goal)
    
    # 逐步执行计划中的每个任务
    while self.planner.current_task:
        task = self.planner.current_task
        task_result = await self._act_on_task(task)
        await self.planner.process_task_result(task_result)
    
    return self.planner.get_useful_memories()[0]
```

先让 LLM 制定一个完整计划（Task 列表），然后逐个执行。每个 Task 执行完后根据结果更新计划。

### 三种模式的适用场景

| 模式 | 适用场景 | LLM 调用开销 |
|---|---|---|
| REACT | 需要动态决策的复杂任务（写代码、修 bug） | 每步都调 LLM 选 action |
| BY_ORDER | 固定流程（先 A 再 B 再 C） | 零开销 |
| PLAN_AND_ACT | 多步骤任务、需要全局规划的（写完整项目） | 一次规划 + 逐步执行 |

## Engineer：最复杂的 Role（512 行）

```python
class Engineer(Role):
    name: str = "Alex"
    profile: str = "Engineer"
    goal: str = "Write elegant, maintainable code"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Engineer 拥有的 actions
        self._init_actions([
            WriteCode,
            WriteCodeReview,
            WriteTest,
            FixBug,
            SummarizeCode,
        ])
        self._watch([WriteTasks, WriteDesign, FixBug, ...])
```

Engineer 的 _think 覆盖了父类——它不只是让 LLM 选 state，而是复杂的条件判断：

```python
async def _think(self) -> bool:
    if self._has_bug_to_fix():
        self._set_state(FIX_BUG_STATE)
        return True
    if self._needs_code_review():
        self._set_state(CODE_REVIEW_STATE)
        return True
    # ... 更多条件判断
    # 最后才让 LLM 选
    return await super()._think()
```

这就是为什么 Engineer 有 512 行——它不只是"会写代码的 Role"，而是有一套**工程决策逻辑**（先修 bug？先审代码？先写新功能？）。

## Role 的序列化与恢复

`SerializationMixin` 让 Role 可以序列化自身——这意味着长时间运行的 Agent 任务可以在中断后恢复：

```python
class SerializationMixin(BaseModel):
    def model_dump(self, **kwargs) -> dict:
        """序列化 Role 为 dict"""
    
    @classmethod
    def model_load(cls, data: dict) -> "SerializationMixin":
        """从 dict 恢复 Role"""
```

结合 `recovered` 标志位，Role 在恢复后可以直接跳到上次中断的 state 继续执行。

## 小结

Role 系统的三个设计层次：

| 层次 | 做什么 | 谁负责 |
|---|---|---|
| 感知层 | 接收消息、过滤、存入记忆 | `_observe()` — 所有 Role 共用 |
| 决策层 | 决定下一步做什么 | `_think()` — 三种模式 + 子类覆盖 |
| 执行层 | 执行选中的 Action | `_act()` — Action.run() |

最值得学的设计：
- **Pydantic 做状态管理**——RoleContext 是 BaseModel，天然可序列化
- **模板方法模式**——observe/think/act 定义骨架，子类填空
- **策略模式**——REACT/BY_ORDER/PLAN_AND_ACT 是三种不同策略
- **watch 订阅模式**——Role 不轮询所有消息，只收自己关注的

下一篇讲 Environment 与消息系统——多 Agent 之间如何协作。
