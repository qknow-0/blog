# Claude Code 安装 + DeepThink V4 接入实战

Claude Code 是 Anthropic 官方推出的终端 AI 编程助手。而 DeepSeek 的 DeepThink V4 模型兼容 Anthropic API 协议，可以用 Claude Code 直接调用。本文手把手走一遍从零安装到配置运行的全流程。

## 前置条件

- **终端** — macOS/Linux 原生终端，或 Windows 上的 PowerShell/CMD/WSL
- **Git**（Windows 用户推荐安装 [Git for Windows](https://git-scm.com/downloads)，Claude Code 的 Bash 工具依赖它）
- **DeepSeek API Key**（在 [DeepSeek Platform](https://platform.deepseek.com) 获取）

## 第 1 步：安装 Claude Code

官方推荐使用原生安装脚本，支持 macOS、Linux、WSL 和 Windows。安装后会自动在后台更新到最新版本。

### macOS / Linux / WSL

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://claude.ai/install.ps1 | iex
```

### Windows CMD

```
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### 其他安装方式

**Homebrew（macOS）：**

```bash
brew install --cask claude-code
```

Homebrew 有两个 cask：`claude-code` 跟踪稳定版（滞后约一周，跳过有重大回归的版本），`claude-code@latest` 跟踪最新版。注意 Homebrew 安装不会自动更新，需要手动 `brew upgrade`。

**WinGet（Windows）：**

```
winget install Anthropic.ClaudeCode
```

WinGet 也不会自动更新，需定期运行 `winget upgrade Anthropic.ClaudeCode`。

**Linux 包管理器：** Debian 系用 `apt`，Fedora/RHEL 用 `dnf`，Alpine 用 `apk`。

### 验证安装

```bash
claude --version
```

终端输出类似：

```
v1.0.37 (Anthropic Claude Code)
```

## 第 2 步：配置 DeepSeek API 作为后端

Claude Code 默认调用 Anthropic 官方 API。要使用 DeepSeek 的 DeepThink V4，需要将 API 端点指向 DeepSeek 的兼容接口。

### macOS / Linux

在终端中执行：

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="<你的 DeepSeek API Key>"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
```

### Windows（PowerShell）

```powershell
$env:ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
$env:ANTHROPIC_AUTH_TOKEN="<你的 DeepSeek API Key>"
$env:ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
$env:CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
$env:CLAUDE_CODE_EFFORT_LEVEL="max"
```

### 持久化配置（推荐）

每次都 export 太麻烦。推荐写入 shell 配置文件：

```bash
# macOS / Linux — 追加到 ~/.zshrc 或 ~/.bashrc
cat >> ~/.zshrc << 'EOF'

# DeepSeek API for Claude Code
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
EOF

source ~/.zshrc
```

## 第 3 步：进入项目启动

```bash
cd /path/to/my-project
claude
```

启动后你会看到 Claude Code 的交互界面。此时所有的请求已通过 DeepSeek 的 API 处理，背后的模型就是 DeepThink V4。

终端输出大致如下：

```
████████████████████████████████████████████████████████████████████████████████
█     Claude Code v1.0.37                                              █
█     Model: deepseek-v4-pro[1m] (via api.deepseek.com)               █
█                                                                      █
█     Tips for getting started:                                       █
█       /help       Show available commands                           █
█       Shift+Enter Add a newline                                     █
████████████████████████████████████████████████████████████████████████████████

> 
```

此时直接输入自然语言即可交互：

```
> 帮我查看当前项目结构，给一个概览
```

## 模型分配策略说明

配置里有 4 个模型变量，它们的作用如下：

| 环境变量 | 用途 | DeepSeek 推荐 |
|----------|------|:---:|
| `ANTHROPIC_MODEL` | 默认使用的模型 | `deepseek-v4-pro[1m]` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | 需要深度推理的任务 | `deepseek-v4-pro[1m]` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 主要编码任务 | `deepseek-v4-pro[1m]` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | 轻量级快速任务 | `deepseek-v4-flash` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | 子代理（多代理模式） | `deepseek-v4-flash` |

三个主力位置都指向同一个 `deepseek-v4-pro[1m]`，这是因为 DeepThink V4 的能力足够覆盖所有场景。子代理和 Haiku 场景用 `v4-flash` 可以**节省成本**——子代理的调用频率通常是主代理的 3-5 倍。

`[1m]` 后缀表示 **100 万 token 上下文窗口**。DeepThink V4 原生支持 100 万 token，是 Claude Sonnet 4.6（200K）的 5 倍。对于大型项目的代码审查和跨文件重构非常有优势。

`CLAUDE_CODE_EFFORT_LEVEL="max"` 告诉模型使用最大推理努力，充分利用 DeepThink V4 的推理能力。在需要深度分析的场景中显著提升输出质量，代价是响应延迟略有增加。

## 实战场景

### 场景 1：代码审查

```bash
cd ~/my-backend-project
claude
```

```
> 审查 app/api/users/route.ts 的安全问题，重点关注输入验证和 SQL 注入
```

Claude Code 会读取文件，逐行分析潜在问题，给出修复建议甚至直接修复。

### 场景 2：跨文件重构

```
> 把项目中所有 console.log 替换为统一的 logger 调用，
  包括 async 函数中的。先给计划，等我确认再执行。
```

### 场景 3：子代理并行探索

```
> 这个项目有三个 microservice 目录，每个都有自己的数据库 schema。
  用子代理分别探索三个目录，汇总所有 schema 中不一致的字段命名。
```

Claude Code 会启动 3 个子代理并行分析，结果汇总到主会话。子代理使用 `deepseek-v4-flash`，主代理用 `deepseek-v4-pro[1m]` 做综合分析。

## 费用对比

DeepSeek API 的定价远低于 Anthropic 官方 API。以 2026 年 5 月的公开定价对比：

| 模型 | 输入价格（每百万 token） | 输出价格（每百万 token） |
|------|:---:|:---:|
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Opus 4.7 | $15.00 | $75.00 |
| DeepSeek V4 Pro | ~$0.55 | ~$2.19 |

对于每天大量使用 AI 编程助手的开发者，**成本可以降低 80-90%**。一个重度 Claude Code 用户月费从 $200-500 降到 $20-100。

> 注：具体价格请以 [DeepSeek 官方定价页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing) 为准。

## 常见问题

### Q: 如果之前配置过 Anthropic 官方的 API，想切回官方怎么办？

```bash
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_MODEL
# ... 以及其他变量
```

然后设置回 Anthropic 的 API Key，或者用 `claude login` 重新登录。

### Q: DeepThink V4 的工具调用（tool use）支持如何？

DeepThink V4 完全兼容 Anthropic Messages API 的 tool use 协议。Claude Code 的文件读写、Bash 执行、Grep 搜索等所有工具都能正常使用。实测工具调用成功率和 Claude Sonnet 4.6 基本持平。

### Q: 子代理用 v4-flash 能行吗？

对于探索性任务、简单文件读写、grep 搜索这类任务，v4-flash 完全够用。如果是子代理也要做复杂代码分析，可以把 `CLAUDE_CODE_SUBAGENT_MODEL` 也设为 `deepseek-v4-pro[1m]`。

### Q: 100 万 token 上下文真的能用满吗？

能。一个中等规模的微服务项目（30-50 个文件），Claude Code 加载项目上下文时很容易超过 100K token。DeepThink V4 的 1M 窗口意味着你可以在一个会话里分析整个大型单体仓库的核心模块。

## 总结

三步完成 Claude Code + DeepThink V4 的配置：

1. `curl -fsSL https://claude.ai/install.sh | bash` — 安装
2. 设置 7 个环境变量 — 指向 DeepSeek API
3. `cd my-project && claude` — 开始使用

DeepThink V4 的 100 万 token 上下文加上 DeepSeek 的价格优势，是目前最具性价比的 AI 编程方案之一。每天重度编码的开发者月费可以控制在百元以内，而体验和 Anthropic 官方 API 几乎没有差别。

> **Claude Code 官方文档**：[https://code.claude.com/docs/en/quickstart](https://code.claude.com/docs/en/quickstart)
> **DeepSeek 接入指南**：[https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/claude_code)
> **DeepSeek Platform**：[https://platform.deepseek.com](https://platform.deepseek.com)
