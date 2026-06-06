# Go Channel 系列（三）：select——多路复用的核心机制

> 本文基于 Go 1.24。

前两篇讲了一个 channel 的发和收。实际情况是你同时面对着好几个 channel——一个等用户输入、一个等超时、一个等取消信号。`select` 就是 Go 的多路复用器：同时等多个 channel 操作，谁先就绪就执行谁。

## 基本语法

```go
select {
case v := <-ch1:
    fmt.Println("received from ch1:", v)
case ch2 <- 42:
    fmt.Println("sent to ch2")
case v := <-ch3:
    fmt.Println("received from ch3:", v)
}
```

`select` 会阻塞，直到某个 case 的 channel 操作可以执行（不阻塞）。如果多个 case 同时就绪——**随机选一个**。不是按顺序，不是优先级，是随机。

这个「随机」是故意的——防止一个 case 持续就绪导致其他 case 永远得不到执行（starvation）。

## 最常见的三个模式

### 超时控制

```go
func fetchWithTimeout(url string) (string, error) {
    result := make(chan string, 1)
    errCh := make(chan error, 1)

    go func() {
        resp, err := http.Get(url)
        if err != nil {
            errCh <- err
            return
        }
        defer resp.Body.Close()
        body, _ := io.ReadAll(resp.Body)
        result <- string(body)
    }()

    select {
    case data := <-result:
        return data, nil
    case err := <-errCh:
        return "", err
    case <-time.After(3 * time.Second):
        return "", fmt.Errorf("timeout")
    }
}
```

`time.After` 返回一个 `<-chan time.Time`——3 秒后它会收到一个值。和 result/errCh 一起放进 select，谁先到就执行谁。

### 取消信号

```go
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case job := <-jobs:
            process(job)
        case <-ctx.Done():
            fmt.Println("worker cancelled")
            return
        }
    }
}
```

`ctx.Done()` 返回一个 channel——context 被取消时，这个 channel 被关闭。select 会选中 `ctx.Done()` 这个 case，worker 优雅退出。这是 Go 中传递取消信号的标准方式。

### 非阻塞操作

```go
select {
case msg := <-ch:
    fmt.Println("received:", msg)
default:
    fmt.Println("nothing available")
}
```

`default` 让 select 不阻塞——如果所有 case 都不能立即执行，就执行 default。两个用途：

```go
// 1. 非阻塞发送——如果缓冲满了就跳过
select {
case ch <- msg:
    fmt.Println("sent")
default:
    fmt.Println("channel full, dropped")
}

// 2. 非阻塞接收——有数据就拿，没有就跳过
select {
case v := <-ch:
    fmt.Println("got:", v)
default:
    // 去做别的事
}
```

`default` 最常见的正确用法是「尽力而为」——缓冲满了就丢弃。最常见的错误用法是放在主循环里空转——`default` 不阻塞，select 瞬间返回，循环疯狂重复，CPU 飙升。

## nil channel 在 select 中的妙用

```go
// nil channel 永远阻塞——在 select 中被忽略
var nilCh chan int

select {
case <-nilCh:       // 永远不会被选中
    fmt.Println("never")
case v := <-realCh:
    fmt.Println(v)
}
```

**往 nil channel 发送或从 nil channel 接收——永远阻塞。**这在 select 里是一个设计工具：「暂时不想处理这个 case 了，把它置为 nil」。

```go
func generator() <-chan int {
    ch := make(chan int)
    go func() {
        defer close(ch)
        for i := 0; i < 10; i++ {
            ch <- i
        }
    }()
    return ch
}

func main() {
    in := generator()
    var timer <-chan time.Time  // nil——初始不触发

    count := 0
    for in != nil || timer != nil {
        select {
        case v, ok := <-in:
            if !ok {
                in = nil      // 数据源用完，置 nil
                continue
            }
            fmt.Println(v)
            count++

        case <-timer:
            fmt.Println("interval report:", count)
            timer = nil       // 报告完一次，timer 置 nil
        }

        // 第一次接收后启动定时器——只启动一次
        if count == 1 && timer == nil {
            timer = time.After(3 * time.Second)
        }
    }
}
```

`in` 和 `timer` 在生命周期中在 nil 和非 nil 之间切换——不需要额外的 flag 变量，select 本身会根据 channel 的 nil 状态自动跳过对应 case。

## select 不会按顺序评估

```go
// ❌ 错误假设：ch1 有数据就一定会先从 ch1 读
select {
case v := <-ch1:
    handle1(v)
case v := <-ch2:
    handle2(v)
}
// 如果 ch1 和 ch2 都有数据——随机选一个
// 不是先检查 ch1 再检查 ch2
```

如果需要优先级：

```go
// ✅ 两层 select 实现优先级
for {
    select {
    case v := <-priorityCh:
        handle(v)
    default:
        select {
        case v := <-priorityCh:
            handle(v)
        case v := <-normalCh:
            handle(v)
        }
    }
}
```

外层 select 检查高优先级——不阻塞等。没数据就走 default，内层 select 阻塞等任意一个就绪。结果：优先处理 `priorityCh`，但它不会饿死 `normalCh`。

## 总结

| 模式 | 写法 | 用途 |
|------|------|------|
| 基本多路复用 | `select { case <-ch1: ... case <-ch2: ... }` | 同时等多个 channel |
| 超时 | `case <-time.After(d):` | 给操作加时间上限 |
| 取消 | `case <-ctx.Done():` | 优雅退出 |
| 非阻塞 | `default:` | 尽力而为，不等待 |
| nil channel 禁用 | `ch = nil` | select 中临时跳过一个 case |

下一篇把前三篇串起来——pipeline、fan-in、fan-out、done channel 等实际并发模式。

→ [（四）并发模式：Pipeline、Fan-In 与 Done Channel](04-patterns.md)
