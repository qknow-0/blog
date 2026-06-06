# Go Goroutines 系列（四）：Context——超时、取消与值传递

> 本文基于 Go 1.24。

前三篇讲了怎么启动 goroutine、怎么等它结束、怎么保护共享数据。这一篇讲怎么取消它——一个 HTTP 请求超时了，所有相关的 goroutine（查数据库、调下游 API、渲染模板）都应该停止，而不是继续浪费资源。`context.Context` 就是 Go 中传播取消信号的标准方式。

## Context 是什么

```go
type Context interface {
    Deadline() (deadline time.Time, ok bool)  // 什么时候超时
    Done() <-chan struct{}                      // 取消信号——channel 被关闭
    Err() error                                 // 为什么被取消
    Value(key any) any                          // 携带的值
}
```

一个 Context 能做三件事：
1. **传播取消**——父 Context 取消，所有子 Context 都取消
2. **携带超时**——指定时间后自动取消
3. **携带值**——跨调用链传递 request-scope 数据

## WithCancel——手动取消

```go
ctx, cancel := context.WithCancel(context.Background())
defer cancel()  // 确保 ctx 被取消，防止 goroutine 泄漏

go func() {
    for {
        select {
        case <-ctx.Done():
            fmt.Println("cancelled:", ctx.Err())  // context.Canceled
            return
        default:
            // 正常干活
        }
    }
}()

// 某个条件满足时
cancel()  // 取消 ctx——所有从它派生的 ctx 都会被取消
```

`cancel()` 是幂等的——可以多次调用，只有第一次有效。`defer cancel()` 确保函数返回时 ctx 被清理，是防止 goroutine 泄漏的标准写法。

## WithTimeout——超时自动取消

```go
func fetchWithTimeout(url string) (string, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return "", err  // 超时后返回 "context deadline exceeded"
    }
    defer resp.Body.Close()
    body, _ := io.ReadAll(resp.Body)
    return string(body), nil
}
```

3 秒后，ctx 自动取消 → HTTP 请求被终止 → `Do(req)` 返回 `context.DeadlineExceeded` 错误。

`defer cancel()` 仍然需要——请求在 3 秒内完成时，cancel 提前释放 ctx 关联的 timer 资源。不 defer cancel 会导致 timer 泄漏。

## WithDeadline——指定时间点取消

```go
deadline := time.Now().Add(30 * time.Second)
ctx, cancel := context.WithDeadline(context.Background(), deadline)
defer cancel()
```

和 `WithTimeout` 本质一样——一个指定时长，一个指定时刻。内部实现相同。

## WithValue——携带请求级数据

```go
type contextKey string

const (
    userIDKey  contextKey = "userID"
    traceIDKey contextKey = "traceID"
)

func WithUserID(ctx context.Context, userID string) context.Context {
    return context.WithValue(ctx, userIDKey, userID)
}

func GetUserID(ctx context.Context) string {
    v, _ := ctx.Value(userIDKey).(string)
    return v
}

// 用法
ctx = WithUserID(ctx, "12345")
// ... 后续所有函数都能拿到 userID
```

三个惯例：

1. **key 用自定义类型，不用 `string`**——防止不同包之间的 key 冲突（`string` 类型的 `"userID"` 在不同包可能是不同的语义）
2. **Value 只用于请求级数据**——trace ID、user ID、request ID。不要用来传业务参数
3. **不存可选参数**——`context.Value` 的返回值没有编译时保证，类型断言失败就没了

## 实际的调用链

```go
func HandleRequest(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel()

    ctx = WithUserID(ctx, extractUserID(r))

    result, err := processOrder(ctx, orderID)
    if err != nil {
        http.Error(w, err.Error(), 500)
        return
    }
    json.NewEncoder(w).Encode(result)
}

func processOrder(ctx context.Context, orderID string) (*Order, error) {
    // 查订单
    order, err := queryOrder(ctx, orderID)
    if err != nil {
        return nil, err
    }

    // 查用户
    user, err := queryUser(ctx, GetUserID(ctx))
    if err != nil {
        return nil, err
    }

    // 调支付
    if err := chargePayment(ctx, user, order.Total); err != nil {
        return nil, err
    }

    return order, nil
}

func queryOrder(ctx context.Context, orderID string) (*Order, error) {
    row := db.QueryRowContext(ctx, "SELECT ...", orderID)
    // 如果 ctx 超时了，db.QueryRowContext 直接返回错误
    ...
}
```

这一整条调用链——HTTP handler → processOrder → queryOrder → queryUser → chargePayment——共享同一个 ctx。5 秒超时时，所有还在执行的操作（数据库查询、HTTP 调用）同时被取消。不需要每个函数自己管理超时。

## Context 的两个铁律

**铁律一：Context 是函数的第一个参数，命名为 `ctx`**

```go
// ✅
func doSomething(ctx context.Context, arg string) error { ... }

// ❌
func doSomething(arg string, ctx context.Context) error { ... }
```

不是技术限制——是 Go 社区的惯例。所有标准库和第三方库都遵守。

**铁律二：不要把 Context 存到 struct 里**

```go
// ❌
type Service struct {
    ctx context.Context  // Context 是请求级的，不是服务级的
}

// ✅——ctx 通过参数传递
func (s *Service) Handle(ctx context.Context, req Request) error { ... }
```

Context 的生命周期是一个请求——不是 struct 的生命周期。存到 struct 里意味着所有请求共享同一个 ctx——一旦第一个请求取消，ctx 就 Done 了，后续请求全用不了了。

## Context 的最佳实践

```go
// 1. 入口函数创建 Context
func Handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()                          // HTTP 请求自带 ctx
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()
    // ...
}

// 2. 中间函数传递 Context
func processTask(ctx context.Context, task Task) error {
    select {
    case <-ctx.Done():
        return ctx.Err()  // 提前退出
    default:
    }
    // 正常处理
    return doWork(ctx, task)
}

// 3. 底层函数检查 Context
func dbQuery(ctx context.Context, query string) (*Result, error) {
    return db.QueryRowContext(ctx, query)  // 依赖库自己会检查
}
```

## 总结

| 函数 | 创建方式 | 取消时机 |
|------|---------|---------|
| `Background()` | 根 Context——永不取消 | 手动 `cancel()` |
| `WithCancel()` | 可手动取消的子 Context | `cancel()` |
| `WithTimeout()` | 带超时的子 Context | 超时或 `cancel()` |
| `WithDeadline()` | 带截止时间的子 Context | 到达时刻或 `cancel()` |
| `WithValue()` | 携带值的子 Context | 继承父 Context 的取消 |

四个派生函数共享同一个取消传播链——取消父 Context，所有子孙 Context 都 Done。

四条规则收束 goroutine 系列：

1. `go f()` 启动 goroutine——轻量，可以开成千上万个
2. `WaitGroup` 等完成、`errgroup` 收集错误、`channel` 传递数据
3. 共享内存用 `Mutex`/`RWMutex`——单变量优先用 `atomic`
4. **每个可能阻塞的 goroutine 都应该接受 `ctx context.Context` 作为第一个参数**——保证它可以被取消

→ [回到系列导航](index.md)
