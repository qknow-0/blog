# 关键代码模式

> 基于 [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 源码分析。提炼 dsh 中可复用的设计模式。

## 模式一：Service Locator

### 问题

插件之间需要通信，但不能硬编码依赖（否则换实现就得改代码）。

### 解法

通过 Context 注册和查找服务，用 key 而非具体类型：

```typescript
// 注册
ctx.provide('logger', new FileLogger())

// 查找（通过 key）
const logger = ctx.logger  // 不 import FileLogger
```

### 好在哪

- **松耦合**——插件只依赖接口，不依赖具体实现
- **可替换**——换实现只需要重新注册，不需要改使用方
- **类型安全**——TypeScript 声明合并保证类型

### 适用场景

- 插件系统
- 依赖注入
- 测试 mock

## 模式二：Event Sourcing

### 问题

状态分散在各处，不一致时难以排查。

### 解法

所有状态变化都记录为事件，状态从事件派生：

```typescript
// 事件是唯一的事实来源
const events = [
  { type: 'user/message', content: 'hello' },
  { type: 'assistant/message', content: 'hi' },
  { type: 'tool/call', tool: 'read_file', args: { path: '...' } },
]

// 状态从事件派生
const history = events
  .filter(e => isModelVisible(e))
  .map(e => toMessage(e))
```

### 好在哪

- **单一数据源**——事件是唯一的事实来源
- **可重放**——从事件可以重建任何时刻的状态
- **可审计**——完整的操作历史

### 适用场景

- 会话系统
- 协作编辑
- 金融交易

## 模式三：Waterfall 中间件

### 问题

请求处理需要经过多个步骤，每个步骤可能修改或短路。

### 解法

waterfall 模式——每个处理器接收 `(value, next)`，调用 `next()` 委托，不调用短路：

```typescript
ctx.waterfall('agent/pre-step', messages, next => {
  // 修改消息
  const filtered = messages.filter(m => m.role !== 'system')
  // 委托给下一个
  return next(filtered)
  // 不调用 next() = 短路（拒绝请求）
})
```

### 好在哪

- **可组合**——多个处理器链式处理
- **可拦截**——任何处理器都可以短路
- **可修改**——每个处理器可以修改传递的值

### 适用场景

- 请求处理管道
- 中间件系统
- 责任链

## 模式四：Effect + Disposer

### 问题

注册的资源需要在卸载时清理，手动管理容易遗漏。

### 解法

注册时返回 disposer，卸载时自动调用：

```typescript
ctx.effect(() => {
  // 注册
  const id = setInterval(() => console.log('tick'), 1000)

  // 返回 disposer
  return () => {
    clearInterval(id)  // 卸载时自动调用
  }
})
```

### 好在哪

- **自动清理**——不需要手动跟踪和清理
- **逆序执行**——后注册的先清理，避免依赖问题
- **声明式**——注册和清理在同一个地方

### 适用场景

- 事件监听器
- 定时器
- 文件句柄
- 网络连接

## 模式五：Async Iteration

### 问题

流式数据需要逐块处理，不能等全部到达。

### 解法

用 `AsyncIterable` 处理流式数据：

```typescript
async function* streamFromAPI(url: string): AsyncIterable<Chunk> {
  const response = await fetch(url)
  const reader = response.body?.getReader()

  while (true) {
    const { done, value } = await reader!.read()
    if (done) break
    yield parseChunk(value)
  }
}

// 使用
for await (const chunk of streamFromAPI(url)) {
  process(chunk)
}
```

### 好在哪

- **惰性求值**——按需处理，不一次性加载
- **背压处理**——消费者控制速度
- **可组合**——可以 map/filter/transform

### 适用场景

- 流式 API
- 实时数据
- 大文件处理

## 模式六：Handle 模式

### 问题

异步任务需要管理（查询状态、取消、获取结果）。

### 解法

返回 Handle 对象，提供状态查询和控制方法：

```typescript
class TaskHandle<T> {
  private promise: Promise<T>
  private status: 'running' | 'done' | 'error' = 'running'

  constructor(executor: () => Promise<T>) {
    this.promise = executor().then(
      result => { this.status = 'done'; return result },
      error => { this.status = 'error'; throw error }
    )
  }

  isRunning() { return this.status === 'running' }
  async wait() { return this.promise }
  cancel() { /* ... */ }
}
```

### 好在哪

- **可控**——可以查询状态、取消执行
- **可等待**——Promise 接口，可以 await
- **可组合**——多个 handle 可以并行管理

### 适用场景

- 后台任务
- Subagent 执行
- 长时间运行的操作

## 模式七：Scope 隔离

### 问题

不同上下文需要不同的服务实例（比如每个 agent 有自己的工具集）。

### 解法

通过 Scope 创建隔离的上下文：

```typescript
// 主 context
const main = new Context()
main.tools = globalTools

// agent scope（隔离）
const agentScope = main.extend({ isolate: ['tools'] })
agentScope.tools = agentSpecificTools  // 只影响这个 scope

// 不影响主 context
console.log(main.tools)  // globalTools
console.log(agentScope.tools)  // agentSpecificTools
```

### 好在哪

- **隔离**——不同上下文互不影响
- **继承**——子 scope 继承父 scope 的服务
- **可覆盖**——子 scope 可以覆盖父 scope 的服务

### 适用场景

- 多租户
- 测试环境
- Agent 隔离

## 总结

dsh 的代码模式可以提炼为七个核心模式：

| 模式 | 解决的问题 | 核心思想 |
|------|-----------|---------|
| Service Locator | 插件通信 | 通过 key 查找服务 |
| Event Sourcing | 状态一致性 | 事件是唯一事实来源 |
| Waterfall 中间件 | 请求处理 | 链式处理 + 短路 |
| Effect + Disposer | 资源清理 | 注册时返回清理函数 |
| Async Iteration | 流式处理 | 惰性求值 + 背压 |
| Handle 模式 | 任务管理 | 返回控制句柄 |
| Scope 隔离 | 上下文隔离 | 继承 + 覆盖 |

这些模式不是 dsh 独创的，但 dsh 把它们组合得很好——每个模式解决一个特定问题，组合起来构建了一个完整的 agent 框架。
