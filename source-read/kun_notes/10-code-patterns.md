# Kun 源码阅读（十）：全仓库优秀代码模式精选

> 基于 [KunAgent/Kun](https://github.com/KunAgent/Kun)。从 200+ 个源文件中精选。

## 1. InflightTracker——防止工具重复执行

### 源码

```typescript
// kun/src/loop/inflight-tracker.ts（简化）
class InflightTracker {
    private inflight = new Map<string, Promise<any>>();

    async executeOnce(key: string, fn: () => Promise<any>): Promise<any> {
        if (this.inflight.has(key)) {
            return this.inflight.get(key)!;  // 复用已在执行的 Promise
        }
        const promise = fn().finally(() => this.inflight.delete(key));
        this.inflight.set(key, promise);
        return promise;
    }
}
```

### 好在哪

不是锁（不阻塞）、不是去重（保证执行）。同样是 key 的两个并发请求，第二个**复用第一个的 Promise**——不创建新请求，不等待完成信号。`finally` 保证执行完一定清除。

### 模式

Promise Deduplication。

### 骨架代码

```typescript
class InflightTracker {
    private m = new Map<string, Promise<any>>();
    async once(key: string, fn: () => Promise<any>): Promise<any> {
        if (this.m.has(key)) return this.m.get(key)!;
        const p = fn().finally(() => this.m.delete(key));
        this.m.set(key, p);
        return p;
    }
}
```

## 2. turn-budget-gate——响应前检查预算

### 源码

```typescript
// kun/src/loop/turn-budget-gate.ts（简化）
class TurnBudgetGate {
    check(usage: Usage, limits: TurnLimits): 'proceed' | 'warn' | 'block' {
        if (usage.tokens > limits.maxTokens) return 'block';
        if (usage.toolCalls > limits.maxToolCalls) return 'block';
        if (usage.tokens > limits.maxTokens * 0.8) return 'warn';
        if (usage.toolCalls > limits.maxToolCalls * 0.8) return 'warn';
        return 'proceed';
    }
}
```

### 好在哪

**三级闸门**：proceed（继续）、warn（警告但继续）、block（停止）。warn 阶段给 Agent 最后一次机会收尾——不是直接截断。80% 阈值触发 warn。

### 骨架代码

```typescript
class Gate<T> {
    constructor(private limits: T, private warnRatio = 0.8) {}
    check(usage: T, max: keyof T): 'proceed'|'warn'|'block' {
        if (usage[max] > this.limits[max]) return 'block';
        if (usage[max] > this.limits[max] * this.warnRatio) return 'warn';
        return 'proceed';
    }
}
```

## 3. round-outcome-coordinator——多结果协调

### 源码

```typescript
// kun/src/loop/round-outcome-coordinator.ts（简化）
class RoundOutcomeCoordinator {
    async coordinate(results: TurnResult[]): Promise<CoordinatedOutcome> {
        const failures = results.filter(r => r.status === 'failed');
        const successes = results.filter(r => r.status === 'ok');

        if (failures.length === 0) {
            return { action: 'continue', summary: this.summarize(successes) };
        }
        if (failures.length < successes.length) {
            return { action: 'continue_partial', failures };
        }
        return { action: 'escalate', failures };  // 大部分失败→升级给用户
    }
}
```

### 好在哪

**部分成功仍然继续。** 不是"有一个失败就全部重来"。少数失败→继续推进，多数失败→升级给用户决策。这比"全部成功或全部失败"的二元模型更接近真实协作。

## 4. Dependency Injection——接口驱动

Kun 大量使用依赖注入：每个模块的构造函数接收 `deps` 对象，而不是直接 import。

```typescript
// ✅ Kun 的做法
constructor(private readonly deps: ToolExecutionServiceDeps) {}

// ToolExecutionServiceDeps 是接口
type ToolExecutionServiceDeps = {
    toolHost: ToolHost;
    inflight: InflightTracker;
    turns: TurnService;
    events: RuntimeEventRecorder;
};
```

### 好在哪

测试时注入 mock——不需要启动整个运行时。类型接口（`type Deps = { ... }`）不是抽象类——TypeScript 的结构类型自动匹配，不需要 `implements`。

## 5. 同目录测试——.ts 旁边放 .test.ts

```
kun-process.ts          →  kun-process.test.ts (75KB test!)
claw-runtime.ts         →  claw-runtime.test.ts (200KB!)
settings-store.ts       →  settings-store.test.ts (31KB)
```

测试文件比源文件大的比比皆是——因为边界情况极多。同目录放置让重构不会遗漏测试。

## 系列回顾

| 篇 | 主题 | 核心收获 |
|---|---|---|
| 一 | 架构总览 | Electron+SSE+四层settings |
| 二 | Agent Loop | round-engine+token-economy+steering |
| 三 | Graph 系统 | reducer+租约+恢复 |
| 四 | 委派系统 | 技能路由+fork上下文 |
| 五 | Memory&Context | 预算管理+history-hygiene |
| 六 | Tool 系统 | 修复+熔断+风暴断路器 |
| 七 | Browser Use | 68KB管理器+network-policy |
| 八 | Extensions | SDK+Disposable+consent |
| 九 | IM 桥接 | 适配器+统一消息+附件管道 |
| 十 | 代码模式 | InflightTracker+Gate+DI+测试 |
