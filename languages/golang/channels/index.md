# Go Channel 系列

从创建到 select 到并发模式——四篇覆盖 Go channel 的全部核心机制。

## 阅读顺序

1. **[（一）基础：创建、发送、接收与阻塞语义](01-basics.md)** — 2026-06-04
   - 无缓冲 channel 的同步握手、关闭规则、方向标注、`for range`

2. **[（二）有缓冲 channel：容量、异步与背压](02-buffered.md)** — 2026-06-04
   - 缓冲大小的选择、worker pool、`len(ch)` 的陷阱

3. **[（三）select：多路复用的核心机制](03-select.md)** — 2026-06-04
   - 超时控制、取消信号、非阻塞操作、nil channel 妙用

4. **[（四）并发模式：Pipeline、Fan-In 与 Done Channel](04-patterns.md)** — 2026-06-04
   - Pipeline、Fan-Out/Fan-In、Done Channel、Or-Done、Tee
