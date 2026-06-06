# Go Goroutines 系列

从 `go` 关键字到 Context——四篇覆盖 Go 并发编程的全部核心机制。

## 阅读顺序

1. **[（一）goroutine 是什么——轻量线程的原理与实践](01-basics.md)** — 2026-06-04
   - `go` 关键字、goroutine vs OS 线程、GOMAXPROCS、goroutine 泄露

2. **[（二）同步——WaitGroup、Once 与 errgroup](02-waitgroup.md)** — 2026-06-04
   - 等完成、只做一次、收集错误、errgroup 取消传播

3. **[（三）锁与原子操作——Mutex、RWMutex 与 atomic](03-mutex.md)** — 2026-06-04
   - 互斥锁、读写锁、sync.Map、原子操作、race detector

4. **[（四）Context——超时、取消与值传递](04-context.md)** — 2026-06-04
   - 取消传播链、超时控制、WithValue 惯例、两条铁律
