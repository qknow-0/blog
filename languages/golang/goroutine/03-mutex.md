# Go Goroutines 系列（三）：锁与原子操作——Mutex、RWMutex 与 atomic

> 本文基于 Go 1.24。

goroutine 通过 channel 通信——但有些场景必须共享内存（计数器、缓存、配置）。这时候需要锁。Go 提供了三种层级的保护：Mutex（互斥锁）、RWMutex（读写锁）、atomic（原子操作）。这篇从 Mutex 讲起，到 race detector 怎么帮你找并发 bug。

## sync.Mutex——互斥锁

```go
type Counter struct {
    mu    sync.Mutex
    value int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    c.value++
    c.mu.Unlock()
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}
```

`defer c.mu.Unlock()` 是惯用写法——即使中间 panic，锁也会被释放。不要手动 `Unlock`：

```go
// ❌ 如果 return 前面忘了 unlock
func (c *Counter) BadValue() int {
    c.mu.Lock()
    return c.value  // 锁没释放——死锁
}

// ✅ defer 保证 unlock
func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}
```

**Mutex 不可 copy**——传结构体值会复制锁：

```go
type Container struct {
    mu sync.Mutex
    data map[string]int
}

func (c Container) BadMethod() {  // ❌ 值接收者——c 是副本，锁在副本上
    c.mu.Lock()
    // ...
}

func (c *Container) GoodMethod() { // ✅ 指针接收者
    c.mu.Lock()
    // ...
}
```

## sync.RWMutex——读写锁

```go
type Cache struct {
    mu   sync.RWMutex
    data map[string]string
}

func (c *Cache) Get(key string) string {
    c.mu.RLock()           // 读锁——多个 goroutine 可以同时持有
    defer c.mu.RUnlock()
    return c.data[key]
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()            // 写锁——独占
    defer c.mu.Unlock()
    c.data[key] = value
}
```

RWMutex 适合读多写少的场景——N 个 goroutine 可以同时 `RLock`，但 `Lock` 会等所有 `RLock` 释放、`RLock` 也会等 `Lock` 释放。

```go
// 场景：配置热更新——每分钟读几万次，每小时写一次
type Config struct {
    mu   sync.RWMutex
    conf *AppConfig
}

func (c *Config) Get() *AppConfig {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.conf
}

func (c *Config) Update(newConf *AppConfig) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.conf = newConf
}
```

99.99% 的时间在执行 `RLock`——几十个 goroutine 同时读，互相不阻塞。只有配置更新那一下需要 `Lock`。

## sync.Map——并发安全的 map，但不是银弹

```go
var m sync.Map

m.Store("key", "value")
v, ok := m.Load("key")
m.Delete("key")
m.Range(func(k, v any) bool {
    fmt.Println(k, v)
    return true  // 返回 false 停止遍历
})
```

sync.Map 有场景局限性——官方文档明确说它在两种场景下优于 `map + Mutex`：

1. **一次写入、多次读取**——entry 基本不更新
2. **多个 goroutine 读写不相交的 key**——每个 goroutine 操作自己的 key 集合

**不是普通 map 的直接替代**。对大多数场景，`map + RWMutex` 更简单、性能也够。

## sync/atomic——无锁的原子操作

```go
import "sync/atomic"

type AtomicCounter struct {
    value atomic.Int64      // Go 1.19+ 泛型原子类型
}

func (c *AtomicCounter) Inc() {
    c.value.Add(1)
}

func (c *AtomicCounter) Value() int64 {
    return c.value.Load()
}
```

atomic 比 Mutex 快——没有锁开销、没有 goroutine 阻塞。但它只能保护**单个变量**的单个操作：

```go
// ✅ atomic 可以——单变量递增
var counter atomic.Int64
counter.Add(1)

// ❌ atomic 不行——两个变量需要一起改
type Balance struct {
    available int64
    pending   int64
}
// 转账：available -= 100; pending += 100
// atomic 保证不了这两步的原子性——需要 Mutex
```

atomic 的其他操作：

```go
var flag atomic.Bool
flag.Store(true)
if flag.Load() { ... }

var ptr atomic.Pointer[Config]
ptr.Store(newConfig)
cfg := ptr.Load()

// CAS——比较并交换（lock-free 数据结构的基础）
var v atomic.Int64
if v.CompareAndSwap(oldValue, newValue) {
    // 成功
}
```

**atomic 的价值不是替代 Mutex——是把可以无锁化的操作暴露出来**。计数器、标志位、配置指针——这些最简单的操作，atomic 比 Mutex 快 5-10 倍。

## Race Detector——找并发 bug

```bash
go test -race ./...
go run -race main.go
go build -race -o myapp
```

race detector 在运行时检测**两个 goroutine 同时访问同一变量且至少一个是写操作**的情况。它不在编译时检查——需要在测试或运行时开启。

```go
// 这个代码跑 go test -race 会报 "DATA RACE"
func TestRace(t *testing.T) {
    var counter int
    for i := 0; i < 100; i++ {
        go func() {
            counter++  // 读-改-写——竞态！
        }()
    }
}
```

race detector 有开销——CPU 慢 5-10 倍，内存多 5-10 倍。只在测试和 CI 中开启，生产环境不启用。

## 锁的粒度——不是越细越好

```go
// ❌ 锁太粗——整个 map 一把锁，读 key1 和读 key2 互相阻塞
type CoarseCache struct {
    mu   sync.RWMutex
    data map[string]*Item
}

// ✅ 分片锁——每个 shard 独立加锁
type ShardedCache struct {
    shards [256]struct {
        mu   sync.RWMutex
        data map[string]*Item
    }
}

func (c *ShardedCache) getShard(key string) *shard {
    h := fnv32(key)
    return &c.shards[h%256]
}
```

分片锁是 `sync.Map` 背后的思想。但大多数项目不需要手写分片锁——锁粒度优化的收益出现在 10+ 个 goroutine 持续竞争同一把锁的情况下。在这之前，一把 `RWMutex` 就够了。

## 总结

| 工具 | 场景 | 开销 |
|------|------|------|
| `sync.Mutex` | 任意共享数据的互斥保护 | 中等 |
| `sync.RWMutex` | 读多写少——N 个同时读 | 中等 |
| `sync.Map` | 一次写多读、key 不相交 | 中等 |
| `atomic` | 单变量的单操作 | 极低 |

选择顺序：channel 能解决就别用锁 → 单变量用 atomic → 读多写少用 RWMutex → 其他用 Mutex。

→ [（四）Context：超时、取消与值传递](04-context.md)
