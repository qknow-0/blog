# RTK (Rust Token Killer)：将 LLM Token 消耗降低 80% 的 CLI 代理神器

## 前言

使用 AI 编程工具（如 Claude Code、GitHub Copilot）时，你是否注意过一个现象：每次执行 `git diff`、`cargo test` 等命令后，AI 的上下文就会被大量原始终端输出塞满？在一次半小时的 Claude Code 会话中，终端输出可能消耗 **~118,000 tokens**，其中绝大部分是调试噪音和无关信息。

RTK（Rust Token Killer）正是为解决这个痛点而生。

## 项目概述

RTK 是一个高性能 CLI 代理，位于 **AI 编程工具与终端命令之间**，在命令输出到达 LLM 上下文之前对其进行过滤和压缩。

基于 Rust 编写，单一二进制文件，无运行时依赖，启动开销 **<10ms**，支持 **100+ 种命令**，已获 **22k+ GitHub Stars**。

- **仓库**：[github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk)
- **官网**：[rtk-ai.app](https://www.rtk-ai.app)
- **当前版本**：v0.34.3
- **许可证**：MIT

## 核心功能

### 四种过滤策略

RTK 对不同类型的命令输出应用四种策略：

| 策略 | 说明 | 示例 |
|------|------|------|
| **智能过滤** | 去除注释、空白行、样板代码 | `cargo build` 编译进度条 |
| **分组聚合** | 按目录/类型合并相似项 | `ls -la` 的详细权限列 |
| **截断** | 保留关键上下文，裁剪冗余 | 长测试输出只保留 1 行摘要 |
| **去重** | 合并重复日志行并计数 | Docker 日志中的重复错误 |

### 支持的生态系统

```
Git/GitHub CLI   → git, gh
Rust             → cargo build, cargo test, cargo clippy
JavaScript/TS    → npm, pnpm, vitest, jest, tsc, next build, prettier
Python           → pytest, ruff, pip, mypy
Go               → go test, go build, golangci-lint
Ruby             → rspec, rubocop, rake test
.NET             → dotnet build/test
Cloud            → aws, docker, kubectl
通用             → ls, cat/grep/find, curl, wget
```

### 实测节省数据

官方基于中等规模 TypeScript/Rust 项目 30 分钟 Claude Code 会话的估算：

| 操作 | 原始 Tokens | RTK 后 | 节省 |
|------|-------------|--------|------|
| `ls` / `tree` | 2,000 | 400 | -80% |
| `cat` / `read` | 40,000 | 12,000 | -70% |
| `grep` / `rg` | 16,000 | 3,200 | -80% |
| `git status` | 3,000 | 600 | -80% |
| `git diff` | 10,000 | 2,500 | -75% |
| `cargo test` / `npm test` | 25,000 | 2,500 | -90% |
| `git add/commit/push` | 1,600 | 120 | -92% |
| **总计** | **~118,000** | **~23,900** | **-80%** |

## 工作原理

RTK 在命令链中扮演"中间人"角色：

```
没有 RTK:
  AI工具  --git status-->  shell  -->  git
    ^                                   |
    |        ~2,000 tokens (原始输出)    |
    +-----------------------------------+

使用 RTK:
  AI工具  --git status-->  RTK  -->  git
    ^                      |          |
    |   ~200 tokens        | 过滤     |
    +-----------------------+----------+
```

AI 工具执行 `git status` 时，hook 机制自动将其重写为 `rtk git status`，RTK 执行真正的 `git status` 命令，然后将输出过滤压缩后返回给 AI。

## 安装方式

### 方法一：Homebrew（macOS 推荐）

```bash
brew install rtk
```

### 方法二：快速安装脚本（Linux/macOS）

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

### 方法三：Cargo 安装

```bash
cargo install --git https://github.com/rtk-ai/rtk
```

### 验证安装

```bash
rtk --version   # 应显示 "rtk 0.34.3"
rtk gain        # 应显示 token 节省统计
```

> **注意**：crates.io 上的 `rtk` 还有一个同名但完全不同的项目（Rust Type Kit），安装后请务必用 `rtk gain` 验证是否正确。

## 使用场景与实战演示

### 场景一：直接使用 RTK

最直接的使用方式是在任何命令前加上 `rtk`：

```bash
# 文件操作
$ rtk ls .                  # 紧凑目录树（12 行 vs 原始 45 行）
my-project/
  +-- src/ (8 files)
  +-- Cargo.toml

$ rtk read src/main.rs       # 智能文件读取（去除注释和空行）

$ rtk grep "TODO" .          # 按文件分组搜索结果

# Git 操作
$ rtk git status             # 紧凑状态
M  src/main.rs
?? docs/

$ rtk git push               # → 一行搞定
ok main

$ rtk git log -n 5           # 单行提交历史
abc1234 fix: handle edge case
def5678 feat: add new endpoint

# 测试输出
$ rtk cargo test             # 只显示失败（-90%）
FAILED: 2/15 tests
  test_edge_case: assertion failed
  test_overflow: panic at utils.rs:18

$ rtk vitest                 # Vitest 紧凑输出（-99.6%）
FAIL  src/__tests__/api.test.ts > should handle timeout
```

### 场景二：为 AI 编程工具安装 Hook

这是 RTK 最强大的使用方式——安装后所有命令**自动重写**，零感知成本：

```bash
# 为 Claude Code 安装（全局）
rtk init -g

# 为其他工具安装
rtk init -g --gemini            # Gemini CLI
rtk init -g --codex             # Codex (OpenAI)
rtk init --agent cursor         # Cursor
rtk init --agent cline          # Cline / Roo Code
rtk init --agent windsurf       # Windsurf

# 重启 AI 工具后直接使用
git status      # 自动重写为 rtk git status
cargo test      # 自动重写为 rtk cargo test
```

安装后，在 Claude Code 中执行 `git status`，hook 机制在命令执行前将其改写为 `rtk git status`，AI 收到的输出从 ~2,000 tokens 压缩到 ~200 tokens。

### 场景三：Token 节省分析

RTK 内置分析功能，可以查看节省统计：

```bash
# 查看汇总
$ rtk gain
Total tokens saved: 94,100 (79.7%)
Commands filtered: 134
Active since: 2026-05-01

# ASCII 图表（最近 30 天）
$ rtk gain --graph
May 15  ████████████████████████  4,200
May 14  ███████████████████      3,100
May 13  ██████████████████████   3,800

# 命令历史
$ rtk gain --history
  git status    (42x)  -81%
  cargo test    (18x)  -92%
  ls            (35x)  -79%
  git diff      (12x)  -76%
  npm test      (8x)   -91%

# 发现遗漏的节省机会
$ rtk discover
Found 3 commands without RTK filters:
  - terraform plan  (3x, ~12,000 tokens wasted)
  - ansible-playbook (2x, ~8,000 tokens wasted)
```

### 场景四：配置文件定制

`~/.config/rtk/config.toml`（macOS 上为 `~/Library/Application Support/rtk/config.toml`）：

```toml
[hooks]
exclude_commands = ["curl", "playwright"]  # 跳过这些命令的重写

[tee]
enabled = true           # 失败时保存原始输出（默认开启）
mode = "failures"        # "failures"、"always" 或 "never"
```

当过滤后的命令执行失败时，RTK 会提示完整输出位置，AI 可随时读取原始日志：

```
FAILED: 2/15 tests
[完整输出: ~/.local/share/rtk/tee/1707753600_cargo_test.log]
```

## 与其他方案对比

| 特性 | RTK | 手动写 prompt | 不做优化 |
|------|-----|--------------|---------|
| 自动重写命令 | 是 | 否 | 否 |
| 支持命令数 | 100+ | 需手动配置 | 0 |
| 额外启动开销 | <10ms | 0 | 0 |
| Token 节省 | 60-90% | 取决于 prompt | 0 |
| 学习成本 | 零（hook 模式） | 较高 | 无 |

## 适用场景

- **重度 AI 编程用户**：每天使用 Claude Code、Copilot、Cursor 等工具的开发者，Token 节省直接影响成本和会话长度
- **大型项目**：编译时间长、测试输出多的大型项目，RTK 的效果更显著
- **远程会话**：使用 SSH 远程开发时，减少传输数据量
- **CI/CD 场景**：AI 辅助调试 CI 失败时，快速定位关键错误

## 不适用场景

- **需要完整原始输出的情况**：RTK 默认截断冗余信息，如需完整输出可使用 `rtk proxy <cmd>` 透传
- **非 AI 编程场景**：RTK 专为 AI 编程工具的上下文窗口优化，普通终端使用无意义

## 总结

RTK 解决了一个具体且实际的问题：**AI 编程工具与终端命令之间的信息鸿沟**。它用一个轻量级的 Rust 二进制文件，在开发者无感知的情况下将 Token 消耗降低 60-90%，同时不丢失关键信息。

对于每天花费数小时与 AI 结对编程的开发者来说，RTK 提供的不仅仅是成本节省，更是会话效率和上下文质量的提升——AI 不再被无效信息分散注意力，能够更精准地理解当前状态。

## 参考链接

- [RTK GitHub 仓库](https://github.com/rtk-ai/rtk)
- [RTK 官网](https://www.rtk-ai.app)
- [官方文档](https://www.rtk-ai.app/guide)
- [RTK Discord 社区](https://discord.gg/RySmvNF5kF)
