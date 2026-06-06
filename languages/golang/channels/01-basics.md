# Go Channel 系列（一）：基础——创建、发送、接收与阻塞语义

> 本文基于 Go 1.24。

Channel 是 Go 并发模型的核心——它不是锁、不是共享内存，而是一根**有类型的管道**。goroutine 通过它传递数据，也通过它同步执行。第一篇从最基础的操作讲起：创建、发送、接收、关闭，以及阻塞在什么时候发生。

## Channel 是什么

```go
ch := make(chan int)    // 创建一个传递 int 的 channel

// 发送：箭头指向 channel
ch <- 42

// 接收：箭头从 channel 出来
value := <-ch

// 关闭：发送方告诉接收方「没有更多数据了」
close(ch)
```

三件事组成最简通信：发送方把数据推进去 → 接收方把数据拉出来 → 发送方关闭管道。

## 无缓冲 channel——同步的握手

```go
func main() {
    ch := make(chan string)

    go func() {
        time.Sleep(1 * time.Second)
        ch <- "hello"       // 阻塞——直到有人接收
        fmt.Println("sent")
    }()

    msg := <-ch              // 阻塞——直到有人发送
    fmt.Println(msg)         // "hello"
    // 然后 goroutine 打印 "sent"
}
```

无缓冲 channel 的发送和接收是**同步的**——发送方等接收方准备好，接收方等发送方投递。谁先到谁先等，直到双方都就位。

这本质上是一个**握手**：
1. goroutine 想发送，但 main 还没到 `<-ch` → goroutine 阻塞
2. main 到了 `<-ch` → goroutine 发送完成，main 接收到
3. 双方继续

如果你在主 goroutine 里对一个无缓冲 channel 发送，而没有其他 goroutine 在接收——**死锁**。Go 运行时检测到这种情况直接 panic，而不是让你无限等下去。

```go
func main() {
    ch := make(chan int)
    ch <- 1   // ❌ fatal error: all goroutines are asleep - deadlock!
}
```

## 关闭 channel——发送方的责任

```go
ch := make(chan int, 3)
ch <- 1
ch <- 2
close(ch)

// 关闭后还能接收剩余数据
fmt.Println(<-ch)  // 1
fmt.Println(<-ch)  // 2
fmt.Println(<-ch)  // 0（零值）——channel 空了

// 用 comma ok 检测
v, ok := <-ch
if !ok {
    fmt.Println("channel closed")
}
```

关键规则：

- **只有发送方应该关闭 channel**——接收方关闭会 panic
- **不要对已关闭的 channel 发送**——会 panic
- **关闭已关闭的 channel**——会 panic
- **从已关闭且为空的 channel 接收**——得到零值，不 panic

```go
// ✅ 惯用模式——发送方在消息发送完后关闭
go func() {
    for _, item := range items {
        ch <- item
    }
    close(ch)
}()

// 接收方用 range 自动检测关闭
for item := range ch {
    fmt.Println(item)
}
```

## `for range`——自动处理关闭

```go
ch := make(chan int, 3)
go func() {
    ch <- 1
    ch <- 2
    ch <- 3
    close(ch)
}()

for v := range ch {
    fmt.Println(v)   // 1, 2, 3——close 后循环自动结束
}
```

这是接收多条消息的最常用模式——不需要手动检查 `ok`，`range` 会在 channel 关闭且为空时自动退出。

## 方向——只读和只写 channel

```go
// 声明时指定方向
func producer(out chan<- int) {   // 只能发送
    out <- 42
    // <-out  ❌ 编译错误
}

func consumer(in <-chan int) {    // 只能接收
    v := <-in
    // in <- 42  ❌ 编译错误
}

func main() {
    ch := make(chan int)
    go producer(ch)
    consumer(ch)
}
```

方向标注是**编译时检查**——不是运行时强制。它让函数签名自我文档化：看了 `producer(out chan<- int)` 就知道这个函数只会往 channel 里写，不会读。

双向 channel 可以隐式转为单向，但反过来不行：

```go
ch := make(chan int)
var out chan<- int = ch     // ✅ 双向 → 单向
var in <-chan int = ch      // ✅ 双向 → 单向
// var ch2 chan int = out   // ❌ 单向 → 双向不行
```

## 总结

| 操作 | 无缓冲 | 有缓冲（非满） | 有缓冲（满） | 已关闭 |
|------|--------|-------------|------------|--------|
| 发送 | 阻塞等接收 | 不阻塞 | 阻塞等空间 | **panic** |
| 接收 | 阻塞等发送 | 不阻塞 | 不阻塞 | 返回零值 |
| 关闭 | ✅ | ✅ | ✅ | **panic** |

记住三条够日常用：
1. 发送方关闭 channel，接收方用 `range` 接收
2. 无缓冲是同步握手，有缓冲（下一篇讲）是异步邮箱
3. 方向标注 (`chan<-` / `<-chan`) 让签名自文档化

→ [（二）有缓冲 channel：容量、异步与背压](02-buffered.md)
