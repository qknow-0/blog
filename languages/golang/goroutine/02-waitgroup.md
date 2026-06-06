# Go Goroutines 系列（二）：同步——WaitGroup、Once 与 errgroup

> 本文基于 Go 1.24。

上一篇讲了 `go` 关键字启动 goroutine。这一篇讲怎么等它结束、怎么确保只做一次、怎么收集错误。

## sync.WaitGroup——等一组 goroutine 完成

```go
var wg sync.WaitGroup

for i := 0; i < 5; i++ {
    wg.Add(1)                     // 计数器 +1
    go func(id int) {
        defer wg.Done()           // 完成时 -1
        fmt.Printf("worker %d done\n", id)
    }(i)
}

wg.Wait()                         // 阻塞——直到计数器归零
fmt.Println("all workers done")
```

`Add`、`Done`、`Wait`——一个计数器、三个方法。规则很简单：

- `Add(n)` 在启动 goroutine **之前**调用。不要在 goroutine 内部调用 `Add`——可能 Wait 先于 Add 执行
- `Done()` 在 goroutine 完成时调用——`defer wg.Done()` 是惯用写法
- `Wait()` 阻塞到计数器归零

```go
// ❌ 常见错误——Add 放在 goroutine 里面
go func() {
    wg.Add(1)  // Wait 可能已经执行完了，这个 Add 还没跑
    defer wg.Done()
    work()
}()

// ✅ Add 在 goroutine 外面
wg.Add(1)
go func() {
    defer wg.Done()
    work()
}()
```

## 传递 WaitGroup——必须传指针

```go
// ❌ 传值——每个 goroutine 拿到的是副本，Done 的是副本，外面的 WaitGroup 感受不到
func worker(wg sync.WaitGroup) {
    defer wg.Done()
}

// ✅ 传指针
func worker(wg *sync.WaitGroup) {
    defer wg.Done()
}
```

`sync.WaitGroup` 内部有状态（计数器），**绝不可以 copy**。传值就是 copy——`go vet` 能检测这类错误。

## WaitGroup + channel 结果收集

```go
func processConcurrently(items []string) []Result {
    var wg sync.WaitGroup
    results := make(chan Result, len(items))

    for _, item := range items {
        wg.Add(1)
        go func(item string) {
            defer wg.Done()
            results <- process(item)
        }(item)
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    var out []Result
    for r := range results {
        out = append(out, r)
    }
    return out
}
```

`wg.Wait()` 在独立的 goroutine 里执行——因为主 goroutine 在 `range results` 上阻塞。关闭 results 需要等所有 worker 完成，但不能在主 goroutine 里等（那会死锁）。所以开一个 goroutine 专门等待，等完了关 channel。

## sync.Once——只执行一次

```go
var (
    once sync.Once
    config *Config
)

func GetConfig() *Config {
    once.Do(func() {
        config = loadConfig()  // 只执行一次——即使多个 goroutine 同时调用 GetConfig
    })
    return config
}
```

用途：懒加载、单例初始化、全局资源注册。`once.Do` 保证函数只执行一次——即使多个 goroutine 同时调用，只有一个会执行，其他阻塞等待。

```go
// ❌ 不能嵌套
once.Do(func() {
    once.Do(func() {  // deadlock
        ...
    })
})
```

## errgroup——等一组 goroutine 完成，收集第一个错误

```go
import "golang.org/x/sync/errgroup"

func fetchAll(urls []string) error {
    g := new(errgroup.Group)

    for _, url := range urls {
        url := url
        g.Go(func() error {
            resp, err := http.Get(url)
            if err != nil {
                return err
            }
            defer resp.Body.Close()
            // process...
            return nil
        })
    }

    return g.Wait()  // 阻塞，返回第一个非 nil 错误
}
```

`errgroup` = `WaitGroup` + 错误收集。任意一个 goroutine 返回 error，`Wait()` 返回那个 error，并且（通过 context）取消其他 goroutine。

```go
// 带 context 取消
g, ctx := errgroup.WithContext(context.Background())

g.Go(func() error {
    return fetchWithContext(ctx, url1)
})

g.Go(func() error {
    return fetchWithContext(ctx, url2)
})

// url1 出错 → ctx 被取消 → url2 收到 ctx.Done() → url2 提前退出
```

`errgroup.WithContext` 是 WaitGroup + 错误 + 取消的组合——任意一个子任务失败，其他还在运行的任务通过 context 知道「可以停了」。

## WaitGroup vs errgroup vs channel

| | WaitGroup | errgroup | channel |
|---|---|---|---|
| 等完成 | ✅ | ✅ | 需要额外逻辑 |
| 收集错误 | ❌ 自己写 | ✅ 自动 | ❌ 自己写 |
| 取消其他 goroutine | ❌ | ✅（WithContext） | ❌ 自己建 done channel |
| 收集返回值 | ❌ 自己建 channel | ❌ 自己建 channel | ✅ 自然支持 |
| 依赖 | 标准库 | golang.org/x/sync | 标准库 |

需要返回值 → channel。需要错误处理 → errgroup。只需要等完成 → WaitGroup。

## 总结

1. `WaitGroup` 等一组 goroutine 结束——Add 在外面，Done defer，Wait 阻塞
2. `Once` 保证只跑一次——单例、懒加载的惯用写法
3. `errgroup` 是 WaitGroup 的升级——自动收集错误，可选取消传播

下一篇讲 goroutine 之间共享数据怎么保护——Mutex、RWMutex 和 atomic。

→ [（三）锁与原子操作：Mutex、RWMutex 与 atomic](03-mutex.md)
