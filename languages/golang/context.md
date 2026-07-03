# Go Context：一根贯穿所有 goroutine 的线

> 你开了 50 个 goroutine 处理请求。用户关了浏览器，你想让这 50 个 goroutine 都停下来——但你怎么通知它们？传一个全局变量？发一条 channel 消息？Go 的答案是 `context.Context`：一根串起所有 goroutine 的线，轻轻一拉，全停下来。

本文基于 Go 1.25。

## 没有 context 的时候：一个请求，50 个工人，怎么喊停

你接到一个订单处理请求，开了 50 个 goroutine 分别去查库存、算运费、调支付。用户不耐烦关了页面——这 50 个工人还在吭哧吭哧干活。你怎么叫停他们？

```go
// ❌ 用全局 bool？每个 goroutine 都要定时看一眼，没人看就等于白设
var stop bool

// ❌ 发 channel？你要发 50 个消息，还得确认谁还活着
stopCh := make(chan struct{})
// 发一个，一个 goroutine 收到了，其他 49 个还在跑……
```

这就像你在工厂车间，要通知所有工人「下班了」。你不能用广播（没这设备），不能一个一个发消息（太慢），最好的是在车间天花板拉一根绳子——一拉，铃响了，所有人停手。

context 就是这根绳子。

## context 是什么：穿过所有工人的一根绳

```go
func handleOrder(ctx context.Context) {
    // 这根绳子 ctx 会传到每一个子任务手里
    go checkInventory(ctx)
    go calculateShipping(ctx)
    go processPayment(ctx)
}

func checkInventory(ctx context.Context) {
    select {
    case <-ctx.Done():   // 绳子动了→老板让下班
        return
    default:
        // 干活
    }
}
```

`ctx.Done()` 返回一个 channel。context 被取消时，这个 channel 会关闭。**关闭的 channel 对所有 `<-ctx.Done()` 的 goroutine 同时生效**——就像一根绳子连着的所有铃铛，一拉全响。

## 四种创建方式

```go
// 1. 天花板上的主绳——整个程序的根
ctx := context.Background()

// 2. 空管子，什么都不传，只为了占位
ctx := context.TODO()

// 3. 定时闹钟——到点自动拉绳
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()  // 不管任务完没完成，记得关闹钟

// 4. 手动拉绳——你决定什么时候下班
ctx, cancel := context.WithCancel(context.Background())
go doWork(ctx)
// 做完了
cancel()  // 拉绳！所有人下班！

// 5. 带值传下去——绳子上挂个小篮子（少用）
ctx := context.WithValue(parentCtx, "userID", 42)
```

### 场景 1：数据库查询超时——定时闹钟

```go
func queryUser(ctx context.Context, db *sql.DB, id int) (*User, error) {
    // 设置 2 秒超时：过了 2 秒自动拉绳
    ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()  // 别忘了关闹钟——否则闹钟一直在走

    row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE id = ?", id)
    var u User
    err := row.Scan(&u.Name, &u.Email)
    return &u, err
    // 2 秒后 database/sql 自动取消查询，释放数据库连接
}
```

### 场景 2：请求取消——用户走了

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()  // HTTP 请求自带的绳子——用户断开连接时自动拉

    results := make(chan Result)

    go func() {
        r, _ := doSlowWork(ctx)    // 绳子传下去
        results <- r
    }()

    select {
    case res := <-results:
        fmt.Fprintln(w, res)
    case <-ctx.Done():
        // 用户关了浏览器——绳子动了
        // goroutine 里的 doSlowWork 也会收到 ctx.Done()
        fmt.Println("client disconnected")
    }
}
```

### 场景 3：手动取消——收到信号就停

```go
func main() {
    ctx, cancel := context.WithCancel(context.Background())

    // 启动 5 个工人
    for i := 0; i < 5; i++ {
        go worker(ctx, i)
    }

    // 监听 Ctrl+C
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, os.Interrupt)
    <-sigCh

    fmt.Println("下班了！")
    cancel()  // 拉绳——5 个工人的 ctx.Done() 同时触发

    time.Sleep(1 * time.Second)  // 给工人一点时间收拾工具
}

func worker(ctx context.Context, id int) {
    for {
        select {
        case <-ctx.Done():
            fmt.Printf("工人 %d 收到下班通知，收拾工具\n", id)
            return
        default:
            // 干活
        }
    }
}
```

## 绳子上挂篮子：context.WithValue

```go
type contextKey string
const userIDKey contextKey = "userID"

// 把用户 ID 放进篮子，传给下游
ctx = context.WithValue(ctx, userIDKey, 42)

// 下游从篮子里取出用户 ID
func handler(ctx context.Context) {
    userID, ok := ctx.Value(userIDKey).(int)
    if !ok {
        // 篮子里没有这个键
    }
}
```

**withValue 的正确用法**：只能传**贯穿整个请求的元数据**——request ID、认证 token、trace ID。不要把业务数据塞进去——那是函数参数该做的事。

```go
// ✅ 绳子上的篮子：request ID、trace ID、认证信息
ctx = context.WithValue(ctx, traceIDKey, "abc-123")

// ❌ 不要这样：篮子不是传业务数据的
ctx = context.WithValue(ctx, "order", someOrder)  // 你完全可以直接传参数
```

## 几个黄金规则

**1. context 是第一个参数**

```go
// ✅ Go 规范
func doSomething(ctx context.Context, arg string) error

// ❌
func doSomething(arg string, ctx context.Context) error
```

**2. 不要存 context 到 struct**

```go
// ❌ 别把绳子当钉子钉在墙上
type Worker struct {
    ctx context.Context  // ← 不要这样
}

// ✅ 绳子是临时的——每次调用传进去
func (w *Worker) doWork(ctx context.Context) error
```

**3. 好的主人记得关闹钟**

```go
ctx, cancel := context.WithTimeout(parent, 5*time.Second)
defer cancel()  // 函数返回时关闹钟，不然后台计时器一直在跑
```

**4. 函数的取消信号要尊重**

```go
func process(ctx context.Context) error {
    for _, item := range items {
        select {
        case <-ctx.Done():
            return ctx.Err()  // 被叫停了，别再取下一个
        default:
        }
        handle(ctx, item)
    }
    return nil
}
```

**5. 别在篮子里放会变的东西**

context 的 value 是不可变的——你不能修改篮子里的东西，只能往里放新的。如果你需要变化的共享状态，用 `sync.Mutex` 或 channel。

## 什么时候用 context，什么时候不用

| 用 context | 不用 context |
|---|---|
| 跨 API 边界的请求范围数据 | 函数内部的可选参数 |
| 取消信号（超时、用户断开） | struct 里的配置 |
| 通过多层调用链传递的数据 | 可以通过函数参数自然传递的东西 |
| request ID、trace ID、auth token | 业务对象 |

**简单的判断标准**：如果这个信息需要穿过三个以上函数调用才能到达使用它的地方，放 context 里。否则，传参数。

## 小结

```text
context 就是连着你所有 goroutine 的绳子
  → WithCancel：你手动拉
  → WithTimeout：闹钟自动拉
  → WithDeadline：定个具体时间，到点拉
  → WithValue：绳子上挂个小篮子

绳子的规矩：
  1. 第一个参数
  2. 每次调用传进去（别存 struct）
  3. 收到 Done() 就停手
  4. defer cancel() 及时关闹钟
```

---

**返回：** [Go 笔记](index.md)
