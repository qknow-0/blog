# Go Channel 系列（二）：有缓冲 channel——容量、异步与背压

> 本文基于 Go 1.24。

上一篇讲了无缓冲 channel 的同步握手。这一篇讲有缓冲 channel——它可以提前存数据，发送和接收解耦，但引入了新的问题：缓冲区多大合适？满了怎么办？

## 无缓冲 vs 有缓冲——一个比喻

```
无缓冲 channel = 电话
  你说的时候对方必须在听——同步、实时、一对一

有缓冲 channel = 信箱
  你投递进去就走——异步、解耦、对方稍后取
```

```go
// 无缓冲——双方必须同时在场
ch := make(chan int)

// 有缓冲——容量为 3
ch := make(chan int, 3)
```

## 创建与基本行为

```go
ch := make(chan string, 3)

// 发送——缓冲区没满就不阻塞
ch <- "one"
ch <- "two"
ch <- "three"
fmt.Println("sent 3 messages without blocking")

// ch <- "four"  // ❌ 阻塞——缓冲区满了，等有人接收

// 接收——FIFO
fmt.Println(<-ch)  // "one"
fmt.Println(<-ch)  // "two"

// 检查容量和当前长度
fmt.Println(cap(ch))  // 3——总容量
fmt.Println(len(ch))  // 1——当前消息数
```

有缓冲 channel 像一个**固定容量的队列**——发送方在队列满之前不阻塞，接收方按 FIFO 顺序取。

## 什么时候用缓冲

```go
// ✅ 好场景：worker pool——限制并发数
func process(items []string) {
    sem := make(chan struct{}, 4)   // 最多 4 个并发

    for _, item := range items {
        sem <- struct{}{}           // 获取许可——满了就等
        go func(item string) {
            defer func() { <-sem }() // 释放许可
            doWork(item)
        }(item)
    }
}
```

```go
// ✅ 好场景：生产者比消费者快——缓冲区吸收突发
func fanIn(inputs ...<-chan int) <-chan int {
    out := make(chan int, len(inputs))  // 缓冲吸收多个生产者的突发
    var wg sync.WaitGroup
    for _, in := range inputs {
        wg.Add(1)
        go func(in <-chan int) {
            defer wg.Done()
            for v := range in {
                out <- v
            }
        }(in)
    }
    go func() { wg.Wait(); close(out) }()
    return out
}
```

```go
// ❌ 坏场景：用缓冲来「修」死锁
// 这不是解决方案——是掩盖了设计问题
ch := make(chan int, 100)  // 缓冲足够大就不会死锁……
// 但你其实想要的是并发模型清晰，不是缓冲够大
```

## 缓冲大小怎么定

| 大小 | 行为 | 适用场景 |
|------|------|---------|
| 0（无缓冲） | 同步握手 | 需要严格同步、确保发送被接收 |
| 1 | 单槽信箱 | 通知「有事发生了」——不关心具体值 |
| N（小） | 有限排队 | worker pool 的并发控制 |
| N（大） | 吸收突发 | 生产者速率波动大于消费者 |

没有标准答案——**缓冲大小是对生产者-消费者速率不匹配的容忍度**。缓冲越大，短时间的速率波动越不会被阻塞。但缓冲不会解决长期的速率不匹配——如果消费者长期慢于生产者，多大的缓冲都会被填满。

## 关闭有缓冲 channel

```go
ch := make(chan int, 3)
ch <- 1
ch <- 2
close(ch)
ch <- 3  // ❌ panic——不能向已关闭的 channel 发送

// 但剩余数据还能接收
fmt.Println(<-ch)  // 1
fmt.Println(<-ch)  // 2
fmt.Println(<-ch)  // 0（零值，已空）
```

和有缓冲无关——关闭规则都一样：发送方关、接收方读完后得零值。

## `len(ch)` 的陷阱

```go
ch := make(chan int, 10)
go func() {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch)
}()

time.Sleep(10 * time.Millisecond)
fmt.Println(len(ch))  // 可能是 5，可能是 3——不可靠

// ❌ 不要用 len(ch) 做决策
if len(ch) == 0 {
    // 这个判断在并发下无意义
    // 检查时是 0，但执行下一行时可能就有数据了
}

// ✅ 用 range 或 select
for v := range ch {
    process(v)
}
```

**`len(ch)` 在并发场景下是瞬时快照，不是可靠的状态判断**。它唯一的合理用途是监控和日志——「队列大概有多深」，而不是控制流。

## 总结

有缓冲 channel 的价值：**把同步握手变成异步投递**。代价：你需要关心缓冲区满的情况。缓冲写多大没有公式——它是对速率波动的容忍度，不是对设计问题的修补。

下一篇讲 `select`——同时等待多个 channel，Go 并发模型中最强大也最容易被滥用控制结构。

→ [（三）select：多路复用的核心机制](03-select.md)
