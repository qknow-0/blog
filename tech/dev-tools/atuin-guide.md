# Atuin：把 Shell 历史变成可搜索、可同步、可统计的数据库

> 基于 [atuinsh/atuin](https://github.com/atuinsh/atuin)，Rust 实现，MIT 协议。

## 一句话说清楚

Atuin 把你的 shell 历史从"一个 `.bash_history` 文本文件"升级成**一个 SQLite 数据库**——每条命令记录退出码、工作目录、主机名、耗时，支持全屏交互式搜索、跨机器加密同步、统计分析。绑定了 `ctrl-r` 和上箭头，让"找到之前跑过的那个命令"从 grep 变成搜索引擎。

## 安装

```bash
# macOS / Linux
curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh

# Homebrew
brew install atuin

# Cargo
cargo install atuin

# 然后注册（可选，用于多机器同步）
atuin register -u <用户名> -e <邮箱>

# 导入已有的 shell 历史
atuin import auto

# 同步
atuin sync
```

安装后 `ctrl-r` 被替换——不再是 bash 那个简陋的单行反向搜索，而是全屏的历史浏览器。

## 和普通 shell 历史的区别

| | `~/.bash_history` / `~/.zsh_history` | Atuin |
|---|---|---|
| 存储 | 纯文本文件 | **SQLite 数据库** |
| 搜索 | `ctrl-r` 单行反向搜索 / `grep` | **全屏交互式搜索 UI** |
| 记录内容 | 命令文本 | 文本 + **退出码、目录、主机名、耗时、session** |
| 跨机器 | ❌ 需要在各机器分别配置 | ✅ **端到端加密同步** |
| 统计 | ❌ | ✅ 最常用命令、使用趋势 |
| 性能 | 大文件 grep 慢 | SQLite 索引查询，毫秒级 |

## 搜索：不是 `grep history`，是搜索引擎

按 `ctrl-r` 打开全屏搜索界面：

```
┌─────────────────────────────────────────────────┐
│ > cargo build                          [global] │
├─────────────────────────────────────────────────┤
│ cargo build --release           2026-07-20  0s  │
│ cargo build --features full      2026-07-19  2s  │
│ cargo build --all-targets        2026-07-18  5s  │
│ make build                       2026-07-15  1s  │
└─────────────────────────────────────────────────┘
```

交互：
- 输入关键词 → 实时过滤
- `ctrl-r` 循环切换过滤模式：**当前 session → 当前目录 → 全局**
- `Enter` 直接执行，`Tab` 先编辑再执行
- `Alt-1` ~ `Alt-9` 快速跳转到最近的条目

**过滤模式是核心功能**。写 Rust 项目时切换到"当前目录"模式——只看到在 `~/projects/blog` 目录下跑过的命令。切到另一个项目时自动切换。

## 每条命令记录 6 个维度

```
{
    "command": "cargo test --lib",
    "exit_code": 0,              # 成功还是失败
    "cwd": "/home/wei/projects/blog",  # 在哪个目录跑的
    "hostname": "macbook",       # 哪台机器
    "session": "abc123",        # 哪个终端 session
    "duration_ms": 3420,        # 花了多久
    "timestamp": "2026-07-20T14:30:00Z"  # 什么时候
}
```

这意味着你可以做**精确查询**：

```bash
# 所有失败的 cargo test 命令
atuin search --exit 1 cargo test

# 昨天下午在 blog 目录跑过的命令
atuin search --cwd ~/projects/blog --after "yesterday 12pm"

# 所有耗时超过 10 秒的命令
atuin search --duration 10000ms

# 本月使用最多的命令 top 10
atuin stats
```

## 同步：端到端加密

```mermaid
flowchart LR
    MAC["MacBook"] -->|"加密后上传"| SERVER["Atuin Server<br/>（看不到明文）"]
    LINUX["Linux 服务器"] -->|"加密后上传"| SERVER
    SERVER -->|"加密后下载"| MAC
    SERVER -->|"加密后下载"| LINUX
```

密钥存在本地。即使 Atuin 的服务器被攻击，攻击者也看不到你的命令历史。也可以自建 server（Atuin 提供了 server 端）。

不需要同步也可以只用本地功能——SQLite 的搜索和统计不需要联网。

## 配置

```toml
# ~/.config/atuin/config.toml

# 历史记录数上限
max_history_size = 100000

# 搜索过滤模式
filter_mode = "global"       # global / host / session / directory
filter_mode_shell_up_key_binding = "directory"  # 按上箭头的过滤模式

# 统计
[stats]
enabled = true
common_subcommands = false   # 统计子命令（cargo build 和 cargo test 分开）

# 同步（可选）
[sync]
records = true
auto_sync = true             # 每 5 分钟自动同步

# 不记录某些命令
[history_filter]
common_prefix = [" ", "ls", "cd", "clear", "exit"]
```

## 统计：你到底在终端里干什么

```bash
$ atuin stats
Top 10 commands:
  cargo test     ████████████████ 184
  cargo build    ██████████████   156
  git commit     █████████        98
  git push       █████████        89
  git status     ████████         82
  ls             ██████           65
  cd blog        █████            52
  git add        █████            48
  nvim src/      ████             42
  docker compose ████             38
```

不需要手动记工作日志——你的 shell 历史就是最诚实的日志。

## 和同类工具的对比

| | Atuin | fzf + history | mcfly | hstr |
|---|---|---|---|---|
| 存储 | SQLite | 纯文本 | SQLite | 纯文本 |
| 搜索 UI | **自研 TUI** | fzf 管道 | 自研 TUI | 自研 TUI |
| 跨机器同步 | ✅ **E2E 加密** | ❌ | ❌ | ❌ |
| 统计 | ✅ | ❌ | ❌ | ❌ |
| 上下文记录 | 退出码+目录+耗时+session | ❌ | 退出码+目录 | ❌ |
| 语言 | **Rust** | Go + Bash | Rust | C |

Atuin 和 fzf 不冲突——很多人在 shell 里同时用两者。Atuin 负责历史存储和同步，fzf 负责文件搜索和命令补全。

## 小结

```bash
# Ctrl-R → 不再是 bash 的反向搜索
# Enter → 直接执行，Tab → 编辑
# Ctrl-R 多按一次 → 切到当前目录模式

atuin search --exit 1        # 找失败的命令
atuin stats                  # 看你在终端里到底干什么
```

Atuin 的本质：**把 shell 历史从"一个你可能 grep 的文件"升级成"一个你会主动查询的个人数据库"**。SQLite 上的全屏搜索、E2E 加密的跨机器同步、按退出码/目录/耗时的精确过滤——这些都是 bash 原生 `ctrl-r` 做不到的。
