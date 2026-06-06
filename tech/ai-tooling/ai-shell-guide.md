# AI Shell：自然语言转 Shell 命令

> 想用 `ffmpeg` 把视频转成 GIF 但忘了参数？想批量重命名文件但 `bash` 脚本写不利索？AI Shell 做的事很简单：你用自然语言描述想做什么，它给你对应的 Shell 命令——然后你可以选执行、修改或不执行。

## 一句话定位

`ai-shell` 是 Builder.io 开源的 CLI 工具，灵感来自 GitHub Copilot X CLI，但完全开源、接你自己的 API Key。它在终端里嵌入了一个 AI，让你用自然语言操作命令行。

```bash
$ ai "convert video.mp4 to a gif, 480p, 10fps"

◇  Generating...
│
◇  Here's your command:
│
◆  ffmpeg -i video.mp4 -vf "fps=10,scale=480:-1" output.gif
│
◆  Run this command?
●  Yes ✅ / No ❌ / Revise 📝 / Explain 🧠 / Copy 📋
```

你不需要记住 `ffmpeg` 的 `-vf` 滤镜语法——描述你要什么结果，命令就出来了。

## 安装与配置

```bash
npm install -g @builder.io/ai-shell

# 设置 API Key（至少配一个）
ai config set OPENAI_KEY=<your-openai-key>
# 或者用 Anthropic Claude
ai config set ANTHROPIC_KEY=<your-anthropic-key>
```

支持的 AI 后端：

| Provider | 环境变量 |
|----------|---------|
| OpenAI | `OPENAI_KEY` |
| Anthropic | `ANTHROPIC_KEY` |
| Groq | `GROQ_API_KEY` |
| Ollama（本地） | 自动连接 `http://localhost:11434` |
| Google Gemini | `GEMINI_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |

**Ollama 本地模式不需要 API Key**——只要你本地跑了 Ollama，`ai-shell` 自动检测并连接。命令在本地模型上跑，数据不出机器。

```bash
# 指定模型
ai config set MODEL=gpt-4o
# 或用 Anthropic
ai config set MODEL=claude-sonnet-4-6
ai config set PROVIDER=anthropic

# 查看当前配置
ai config get
```

## 基本用法

```bash
# 最简单的用法——描述要做的事
ai "list all files larger than 100MB recursively"

# 生成结果：
# find . -type f -size +100M -exec ls -lh {} \;

# 选择执行、修改或跳过
```

每次生成后，有五个选项：

- **Yes** ✅ ——执行命令
- **No** ❌ ——放弃
- **Revise** 📝 ——修改需求描述，重新生成
- **Explain** 🧠 ——让 AI 解释命令做了什么
- **Copy** 📋 ——复制到剪贴板

Explain 模式是学习命令行最好的方式之一：

```bash
$ ai "extract all .tar.gz files in current directory"

◇  Command:
│  for file in *.tar.gz; do tar -xzf "$file"; done
│
◆  Explain:
│  This bash loop iterates over all files matching *.tar.gz in the
│  current directory. For each file, it uses tar -xzf to extract
│  the contents. -x means extract, -z is for gzip compression,
│  -f specifies the file.
```

不只是给命令——还告诉你每一部分是什么意思。用几个月下来，你能学会不少 `find`、`xargs`、`awk` 的用法。

## Silent 模式和 Quiet 模式

```bash
# Silent——直接执行，不确认
ai "kill process on port 3000" -- silent
```

自动执行不确认。适合你完全信任 AI 的场景——但慎用。

```bash
# Quiet——只输出命令本身，不执行、不问，适合管道
ai "find all .log files modified in the last 24 hours" -- quiet
# find . -name "*.log" -mtime -1

# 把输出接管道或复制
ai "show git authors sorted by commit count" -- quiet | pbcopy
```

Quiet 模式回到 Unix 的原始哲学——只输出结果，不交互。适合把 `ai` 当成管道中的一个环节：

```bash
# 把生成的命令直接执行
eval $(ai "delete all .DS_Store files recursively" -- quiet)
```

## 会话模式

```bash
ai chat
```

进入对话模式，连续交互：

```
→ list all running docker containers
← docker ps
→ now stop the one named postgres-dev
← docker stop postgres-dev
→ also prune all stopped containers
← docker container prune -f
```

每次对话记住上下文——你可以用代词（"it", "the one"）引用上一条命令的结果。

## 实际场景

### 场景一：记不住的命令参数

```bash
$ ai "use kubectl to get pods in namespace prod, sorted by restart count"

# kubectl get pods -n prod --sort-by=.status.containerStatuses
# [0].restartCount
```

Kubernetes 的 `--sort-by` JSONPath 语法很难记——每次都要查文档。一行自然语言描述，比翻 K8s cheatsheet 快。

### 场景二：复杂的文本处理

```bash
$ ai "from access.log, count requests per hour and sort by count desc"

# awk '{print substr($4,2,14)}' access.log | uniq -c | sort -rn
```

`awk` 的 `substr` 提取时间戳、`uniq -c` 计数、`sort -rn` 倒排——这行命令手写要考虑五分钟，AI 一秒出。

### 场景三：一键式环境操作

```bash
$ ai "create a new directory called backup, copy all .env files there, and tar it"

# mkdir -p backup && find . -name ".env" -exec cp --parents {} backup/ \;
# && tar -czf backup.tar.gz backup/
```

把多步操作合并成一条自然语言描述——AI 负责连接命令。

## 自定义 System Prompt

```bash
ai config set SYSTEM_PROMPT="You are a macOS expert. Always prefer native macOS tools over GNU tools. Use zsh syntax."
```

或者针对特定场景定调：

```bash
ai config set SYSTEM_PROMPT="Always include error handling (|| true, set -e). Prefer one-liners with && over scripts. Use long flags (--recursive not -r) for readability."
```

这样生成的命令风格一致——你的团队可以共享同一个 system prompt，确保生成的命令符合同一个规范。

## 安全考量

**AI Shell 不执行你的命令，你执行。**

```
生成 → 展示 → 你确认 → 执行
```

不是自动执行（除非你用 `-- silent`），你总是有机会看清楚命令再决定。危险的命令——`rm -rf /`、`DROP TABLE`、`git push --force`——在展示阶段你就能拦截。

但仍有几点需要注意：

- **生成的命令可能不完全符合你的意图**——特别是文件路径和文件名，AI 可能猜错
- **管道命令的中间结果不可见**——复杂命令建议先 Explain 理解每一步
- **Silent 模式不确认**——只在你完全信任的场景下用

## 和 Copilot X CLI 的区别

GitHub Copilot X CLI 目前只在有限范围内可用。AI Shell 是开源的替代方案：

| | AI Shell | Copilot X CLI |
|---|---|---|
| 开源 | ✅ MIT | ❌ |
| API Key | 你自己的 | GitHub |
| 模型选择 | OpenAI/Anthropic/Groq/Ollama/Gemini/Mistral | GitHub 模型 |
| 本地模型 | ✅ Ollama | ❌ |
| 数据隐私 | 取决于 Provider | 取决于 GitHub |
| 价格 | 按 API 用量 | 订阅制 |

如果你已经买了 Claude/OpenAI API，`ai-shell` 是零额外成本的方案。

## 总结

不是 `man` 的替代品——是当你「不知道命令叫什么、不知道 man 该搜什么、不知道这个 flag 长什么样」时的救兵。

```bash
npm install -g @builder.io/ai-shell
ai config set ANTHROPIC_KEY=sk-ant-...
ai "find all TypeScript files with console.log and count them"
```

来自 Builder.io 这个做前端可视化工具的团队——顺手写了一个终端里最实用的 AI 工具。
