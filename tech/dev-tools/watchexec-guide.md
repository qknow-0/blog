# watchexec：文件变了就自动跑命令，不用每次手动敲

> 基于 watchexec 最新版本，[github.com/watchexec/watchexec](https://github.com/watchexec/watchexec)。

## 你的日常：改代码 → 切终端 → 跑测试 → 切回来 → 改代码 →

```bash
# 改完 Rust 代码
$ cargo test                    # 切到终端，跑，等结果
# 改完前端代码
$ npm run build                 # 又切过去，跑，等结果
# 改完 Python
$ pytest                        # 再来一遍...
```

这不是开发，这是**手动挡换挡**。`watchexec` 帮你把最后三步自动化——文件变了，自动跑命令。

```bash
# 任何 .rs 文件变化 → 自动 cargo test
$ watchexec -e rs -- cargo test

# 任何 .py 文件变化 → 自动重启服务器
$ watchexec -r -e py -- python server.py

# 前端文件变化 → 自动 build
$ watchexec -e js,css,html npm run build
```

## 三个让你回不去的参数

### `-r`：自动杀死旧进程，启动新的

这是 watchexec 最常用的参数。不加 `-r`，每次文件变化只跑一次命令；加了 `-r`，它会记住上次启动的进程，下次文件变化时**先杀掉旧的，再启动新的**：

```bash
# 不加 -r：每次 python server.py 跑完就完事了——不适合服务
# 加 -r：杀掉旧 server，启动新 server——这才是你想要的
$ watchexec -r -e py -- python server.py
```

关键是它处理的不是单个进程，而是**整个进程组**。如果你的 server fork 了子进程，`watchexec` 会一次性全部清理——不会留下孤儿进程。

### `-e`：只看你关心的文件

```bash
$ watchexec -e rs,toml -- cargo check    # 只关心 Rust 文件
$ watchexec -e py,html,css -- pytest     # 只关心 Python + 前端
$ watchexec -e go -- go test ./...       # 只关心 Go 文件
```

没有 `-e` 的话，任何文件变化都触发——`target/` 里的编译产物、`.git/` 里的内部文件、编辑器的临时文件……这些你不想要的触发，watchexec 默认帮你过滤了。

### `--ignore` 和 `.gitignore` 原生支持

```bash
# 不看 target 目录（Rust 编译产物）
$ watchexec --ignore='target/**' -- cargo test

# 自动加载项目的 .gitignore——target/、node_modules/ 等默认不触发
$ watchexec -- cargo build   # .gitignore 生效，不需要手动 ignore
```

## 智能事件合并：编辑器保存不会触发两次

很多编辑器保存文件时不是"直接写入"，而是：

1. 写到一个临时文件（`file.rs~`、`.#file.rs`）
2. 删除原文件
3. 临时文件重命名为正式文件名

这会产生 3 个文件系统事件。普通文件监听器看到 3 个事件就触发 3 次命令——每次都是一样的结果。

watchexec 有**事件合并**机制——在一个时间窗口内的连续事件被合并成一次触发：

```
文件系统: [create tmp] [delete orig] [rename tmp → orig]
                          ↓ coalesce
watchexec:              [触发一次]
```

这个时间窗口默认 50ms，可以通过 `--debounce` 调整：

```bash
$ watchexec --debounce 200ms -- cargo test   # 200ms 内的连续事件只触发一次
```

## 实战：Rust + Python 双语言项目

```bash
# 项目结构
# ├── src/        # Rust 后端
# ├── tests/      # Python 测试
# └── frontend/   # 前端

# 三个 watchexec 同时跑
$ watchexec -e rs,toml -r -- cargo run &           # Rust 后端：改代码 → 重启
$ watchexec -e py -- pytest &                       # Python：改测试 → 跑测试
$ watchexec -e js,css,html -- npm run build &       # 前端：改文件 → 构建
```

## 环境变量：知道你改了什么文件

watchexec 在执行命令时注入环境变量，让命令知道"哪些文件变了"：

```bash
$ watchexec -e rs -- sh -c 'echo "changed: $WATCHEXEC_WRITTEN_PATH"'
# → changed: src/main.rs

# 多个文件变了：
# → changed: src/lib.rs:src/main.rs
```

也支持通过 stdin 传递：

```bash
$ watchexec --emit-events-to=stdin -- cat
# → {"event":"write","path":"src/main.rs"}
```

## 不只是 CLI：底层是一个库生态

watchexec 是一个 Rust crate 家族，不只提供命令行。`cargo-watch`（Rust 生态里最常用的文件监听工具）就是建立在 watchexec 之上的：

```
watchexec crate
    ├── watchexec-cli （你用的命令行）
    ├── cargo-watch  （cargo watch 命令的底层）
    ├── ghciwatch    （Haskell GHCi 监听）
    └── 更多下游项目...
```

## 和同类工具的对比

| 工具 | 语言依赖 | 跨平台 | 进程组管理 | .gitignore |
|---|---|---|---|---|
| **watchexec** | 无（独立二进制） | ✅ | ✅ | ✅ |
| nodemon | Node.js | ✅ | ❌ | 需插件 |
| watchdog | Python | ✅ | ❌ | 需配置 |
| guard | Ruby | ✅ | ❌ | 需配置 |
| entr | 无 | Unix only | ❌ | ❌ |

watchexec 不需要任何语言运行时——下载一个 3MB 的二进制文件就能跑。这也是它能被 `cargo-watch` 等工具作为底层依赖的原因。

## 小结

```bash
# 三句话记住 watchexec
$ watchexec -e py -r -- python server.py     # 文件变了 → 重启服务
$ watchexec -e rs -- cargo test              # 文件变了 → 跑测试
$ watchexec -e go -- go build ./...          # 文件变了 → 编译
```

一个独立二进制、零运行时依赖、所有语言通用。把它放进你的 `$PATH`，以后改代码就不用再手动切终端跑命令了。
