# Go 单元测试：标准库就够了

> 本文基于 Go 1.25。

Go 的测试框架和 Rust 一样长在语言里——`go test` 开箱即用。不用装 testify、ginkgo、gomock，标准库 `testing` 包覆盖了绝大多数场景。Go 社区的习惯是少依赖第三方测试框架，多用标准库组合。

## 基本姿势

```go
// calculator.go
package calculator

func Add(a, b int) int {
    return a + b
}
```

```go
// calculator_test.go
package calculator

import "testing"

func TestAdd(t *testing.T) {
    got := Add(2, 3)
    want := 5
    if got != want {
        t.Errorf("Add(2, 3) = %d; want %d", got, want)
    }
}
```

测试文件以 `_test.go` 结尾，测试函数以 `Test` 开头。跑起来：

```bash
go test ./...      # 递归跑所有包
go test -v         # 显示每个测试的名字和结果
go test -run TestAdd  # 只跑名称匹配的测试
```

输出：

```
=== RUN   TestAdd
--- PASS: TestAdd (0.00s)
PASS
ok      calculator  0.123s
```

## 表驱动测试：Go 的灵魂写法

写十个 `TestAddPositive`、`TestAddNegative`、`TestAddZero` 是 Java/Jest 的习惯。Go 用表驱动——一个结构体切片，循环跑：

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
        {"mixed", -5, 10, 5},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.want {
                t.Errorf("Add(%d, %d) = %d; want %d",
                    tt.a, tt.b, got, tt.want)
            }
        })
    }
}
```

`t.Run` 创建子测试——每个 case 独立运行，失败不影响其他。`-run` 也能过滤子测试：

```bash
go test -run TestAdd/negative
```

## testify：社区标准增强库

标准库的 `if got != want` 写多了有点啰嗦。`testify` 是 Go 社区最广泛使用的断言库：

```go
import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestDivide(t *testing.T) {
    result, err := Divide(10, 2)

    require.NoError(t, err)        // 失败立即终止
    assert.Equal(t, 5, result)     // 失败继续执行
    assert.NotZero(t, result)
}
```

`require` 失败后当前测试停止，`assert` 失败后继续。判断规则：前置条件用 `require`（除数为零就没必要继续了），断言用 `assert`。

## Mock：不需要框架

Go 的接口天然支持 mock，不需要 gomock 生成代码：

```go
// 定义接口
type UserRepository interface {
    FindByID(id int) (*User, error)
}

// 真实实现
type PostgresRepo struct { db *sql.DB }
func (r *PostgresRepo) FindByID(id int) (*User, error) { /* ... */ }

// Mock 实现
type MockRepo struct {
    users map[int]*User
}

func (m *MockRepo) FindByID(id int) (*User, error) {
    if u, ok := m.users[id]; ok {
        return u, nil
    }
    return nil, fmt.Errorf("user %d not found", id)
}

// 测试
func TestGetUserName(t *testing.T) {
    repo := &MockRepo{
        users: map[int]*User{
            1: {Name: "Alice"},
        },
    }
    svc := NewUserService(repo)
    name, err := svc.GetUserName(1)

    assert.NoError(t, err)
    assert.Equal(t, "Alice", name)
}
```

接口让你在测试中注入 mock 实现。Go 的哲学是：**依赖接口而不是具体类型**，这个原则同时让代码更可测试。

## 临时文件和目录

`t.TempDir()` 创建测试结束后自动清理的临时目录：

```go
func TestWriteConfig(t *testing.T) {
    dir := t.TempDir()   // 测试结束自动删除

    configPath := filepath.Join(dir, "config.toml")
    err := WriteConfig(configPath, Config{Port: 8080})
    require.NoError(t, err)

    data, err := os.ReadFile(configPath)
    require.NoError(t, err)
    assert.Contains(t, string(data), "port = 8080")
}
```

不用 `os.MkdirTemp` + `defer os.RemoveAll`，`t.TempDir()` 一行搞定。多个测试同时跑，每个独享一个目录。

## 并行测试

```go
func TestSlow(t *testing.T) {
    t.Parallel()  // 和别的并行测试一起跑
    time.Sleep(100 * time.Millisecond)
    // ...
}
```

`t.Parallel()` 标记的测试被调度到不同 goroutine 同时执行。单测中 IO 密集或纯计算场景有明显提速。

并行模式下子测试的闭包陷阱需要特别注意：

```go
for _, tt := range tests {
    tt := tt          // ← 必须重新绑定！
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // 用 tt，不要用外层循环变量
    })
}
```

Go 1.22 修复了循环变量捕获问题，但测试中显式 `tt := tt` 仍是推荐习惯。

## 测试辅助函数

提取公共的 setup 和断言：

```go
// 辅助函数——接受 *testing.T，失败时调用 t.Helper()
func setupDB(t *testing.T) *sql.DB {
    t.Helper()  // ← 关键：失败时报告调用者位置而非此函数位置

    db, err := sql.Open("sqlite3", ":memory:")
    require.NoError(t, err)
    t.Cleanup(func() { db.Close() })  // 测试结束自动清理
    return db
}

func TestCreateUser(t *testing.T) {
    db := setupDB(t)  // 失败报告指向这里，而非 setupDB 内部
    // ...
}
```

`t.Helper()` 让错误定位到测试函数里，而不是 helper 里面。`t.Cleanup` 注册清理函数，和 `defer` 类似但更灵活——你可以从 helper 里注册 cleanip。

## 覆盖率

```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out  # 浏览器打开可视化
```

覆盖率文件可以通到 CI——新代码覆盖率低于阈值直接拦截。

## 基准测试

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(2, 3)
    }
}
```

```bash
go test -bench=. -benchmem
```

`b.N` 由框架自动调整，确保每次 benchmark 跑足够多次才有统计意义。`-benchmem` 输出分配次数和字节数——优化目标不只是耗时，还有 GC 压力。

## Go vs Rust 测试对比

| | Go | Rust |
|------|------|------|
| 测试文件 | `<name>_test.go` | `#[cfg(test)] mod tests` |
| 断言 | `if got != want` / testify | `assert_eq!` / `assert!` |
| 子测试 | `t.Run` | `mod` 嵌套 |
| Mock | 接口 + 手写实现 | trait + 条件编译 |
| 基准测试 | `testing.B` | `#[bench]` |
| 并发测试 | `t.Parallel()` | rayon / 手动 spawn |
| 覆盖率 | `go test -coverprofile` | `cargo llvm-cov` |

Go 的测试风格更偏向「手动 if 判断 + 表驱动」，Rust 更偏向「宏 + 模块组织」。两种都是语言自带的，都不需要装第三方跑器——这是最大共同点。

> 参考：[Go testing 文档](https://pkg.go.dev/testing)
