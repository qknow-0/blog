# ccstatusline：为 Claude Code 打造极致美观的状态栏

## 一个9k+ Stars 的神器

如果你使用 Claude Code 进行开发，大概率已经见过它了——终端底部那一行漂亮的状态栏，显示着当前模型、Git 分支、Token 用量，甚至还有进度条和计时器。这个项目就是 **ccstatusline**，一个专为 Claude Code CLI 打造的高度可定制状态栏格式化工具。

项目由 Matthew Breedlove（@sirmalloc）开发，采用 MIT 开源协议，截至目前已在 GitHub 上获得超过 **9300 颗星**，并被 [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) 收录推荐。

GitHub: https://github.com/sirmalloc/ccstatusline

---

## 核心功能一览

ccstatusline 提供的功能远不止"显示状态"这么简单，下面逐一盘点：

### 模型与会话信息
- **模型名称**：当前正在使用的 Claude 模型（如 Claude Sonnet 4.6）
- **输出风格**：当前输出模式
- **版本号**：Claude Code CLI 版本
- **会话 ID / 会话名称**：标识当前会话
- **会话时长 / 会话花费**：跟踪会话耗时和美元计费
- **Claude 账户邮箱**：显示当前登录的 Claude 账户

### Git 集成（非常全面）
- **Git 分支**：当前分支，支持点击跳转 GitHub/GitLab 链接
- **Git PR/MR**：当前分支的 PR 信息，支持状态和标题显示
- **Git 变更统计**：插入行数、删除行数、总变更数
- **Git 文件状态**：暂存/未暂存/未跟踪文件数量
- **Git 冲突数**：合并冲突计数
- **Git SHA**：当前短提交哈希
- **Git Worktree**：worktree 模式、名称、分支、原始分支
- **仓库远程信息**：origin/upstream 所有者、仓库名、是否 fork

### Token 与上下文
- **Token 计数**：输入/输出/缓存/总计 Token
- **Token 速度**：输入/输出/总速度，支持可配置滚动窗口（0-120秒）
- **上下文长度 / 上下文窗口**：当前用量和总窗口大小
- **上下文百分比**：已用/剩余百分比，支持进度条模式
- **压缩计数器**：会话上下文压缩次数

### 用量与计时
- **会话用量 / 周用量**：API 用量百分比可视化
- **模型级别用量**：Sonnet / Opus 分别的周用量
- **额外用量**：按量付费超量使用情况
- **Block 计时器**：跟踪 Claude Code 5 小时对话块的进度
- **Block 重置计时** / **周重置计时**：距离重置剩余时间，支持精确日期显示

### 环境与自定义
- **当前工作目录**：可配置显示段数，支持 fish shell 风格缩写
- **终端宽度**：实时检测
- **内存使用**：系统内存占用
- **自定义文本**：任意文字或表情符号
- **自定义命令**：执行 shell 命令并显示输出
- **链接部件**：可点击的 OSC 8 超链接
- **语音状态**：显示语音输入是否启用

### 全局与布局
- **Powerline 模式**：箭头分隔符、自定义端帽、自动对齐
- **多行支持**：无限数量独立状态行
- **Flexible 分隔符**：自动填充宽度的弹性分隔符
- **全局设置**：默认内边距、默认分隔符、全局粗体、全局颜色覆盖
- **极简模式**：全局强制无标签的原始值显示

---

## 安装方式

ccstatusline 最方便的地方在于——**无需安装即可使用**。

### 零安装（推荐初体验）

```bash
# 使用 npm
npx -y ccstatusline@latest

# 使用 Bun（更快）
bunx -y ccstatusline@latest
```

两个命令都会启动同一个终端 UI 配置界面。首次运行时会引导你选择安装模式：

1. **Pinned 全局安装**：锁定当前版本，写入 Claude Code 设置，后续 `ccstatusline` 命令直接可用
2. **临时运行**：仅启动配置界面，不写入设置

配置完成后，ccstatusline 会自动将状态栏命令写入 Claude Code 的 `settings.json`：

```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y ccstatusline@latest",
    "padding": 0,
    "refreshInterval": 10
  }
}
```

支持的命令值包括：`npx -y ccstatusline@latest`、`bunx -y ccstatusline@latest`、`ccstatusline`（全局安装后）。

---

## 实战演示

### 场景一：首次运行配置

在终端中执行：

```bash
npx -y ccstatusline@latest
```

你会看到一个交互式 TUI，操作流程如下：

1. **选择安装模式**：建议选 Pinned 全局安装，锁定版本避免意外更新
2. **添加部件**：按 `a` 打开部件选择器，搜索你想显示的部件
3. **排序调整**：按 `Enter` 进入移动模式，调整部件顺序
4. **自定义颜色**：按 `←/→` 为每个部件选择颜色主题
5. **预览效果**：TUI 实时渲染效果
6. **保存退出**：自动保存到 `~/.config/ccstatusline/settings.json`

支持中文搜索——例如输入"分支"就能找到 Git Branch 部件。

## 部件编辑器快捷键参考

| 快捷键 | 功能 |
|--------|------|
| `↑/↓` | 选择部件 |
| `a` | 添加部件 |
| `i` | 插入部件 |
| `k` | 克隆部件 |
| `d` | 删除部件 |
| `Enter` | 进入/退出移动模式 |
| `Space` | 切换手动分隔符字符 |
| `r` | 切换原始值模式（仅保留值，去掉标签） |
| `m` | 切换合并模式（合并/不合并/合并无内边距） |
| `c` | 清空当前行 |
| `Esc` | 返回 |

编辑器定位到具体部件后还会有更多专属快捷键，TUI 底部会实时显示当前可用操作。

---

## 跨平台与兼容性

- **Node.js / Bun** 双引擎支持
- **macOS / Linux / Windows** 全平台
- Windows 有专门的 [WINDOWS.md](https://github.com/sirmalloc/ccstatusline/blob/main/docs/WINDOWS.md) 文档，包含 PowerShell 示例、WSL 配置、Windows Terminal 字体设置
- 支持自定义 `CLAUDE_CONFIG_DIR` 环境变量，适应非标准 Claude Code 配置路径

---

## 社区生态

ccstatusline 的生态中还有几个值得关注的姊妹项目：

- **[tweakcc](https://github.com/Piebald-AI/tweakcc)**：定制 Claude Code 主题、思考动词等
- **[ccusage](https://github.com/ryoppippi/ccusage)**：跟踪和显示 Claude Code 用量指标
- **[codachi](https://github.com/vincent-k2026/codachi)**：电子宠物风格的状态栏宠物，随上下文窗口增长
- **[AIWatch](https://ai-watch.dev)**：30+ AI API 的实时状态监控，可嵌入状态行

### 与 AIWatch 集成示例

想知道当前是不是 Claude API 本身在抽风？通过 Custom Command 嵌入 AIWatch：

```bash
( curl -sf --max-time 2 https://ai-watch.dev/api/status/cached | \
  jq -r '[.services[] | select(.status != "operational") | "🔴 " + .name] | .[0:3] | join(" ")' ) \
  2>/dev/null || true
```

设置超时 2000ms，当所有服务正常时输出为空，部件自动隐藏。

### 第三方中文分支

社区还有一个中文版分支：[ccstatusline-zh](https://github.com/huangguang1999/ccstatusline-zh)，对中文用户更友好。

---

## 版本亮点回顾

ccstatusline 从 v2.0 开始持续快速迭代，这里摘录几个里程碑版本：

| 版本 | 亮点 |
|------|------|
| v2.0 | 引入 Powerline 模式与内置主题 |
| v2.1 | 添加用时/用量/上下文进度条部件 |
| v2.2 | Token 速度、思考力度、Vim 模式、GitLab 支持 |
| v2.2.18（最新）| 版本锁定、npm 来源验证、Git 锁竞争避免 |

---

## 总结

ccstatusline 给我的感觉是——它把"终端状态栏"这个看似不起眼的需求做到了极致。从最基本的模型名称显示，到复杂的 Git 远程信息解析、AI API 用量监控、OSC 8 超链接支持，再到 Powerline 风格的视觉效果，每个细节都打磨得很到位。

如果你经常在终端里使用 Claude Code，花几分钟配置一个 ccstatusline，绝对能让你每天的开发体验提升一个档次。

---

**原文仓库**：https://github.com/sirmalloc/ccstatusline
**NPM 页面**：https://www.npmjs.com/package/ccstatusline
**作者**：Matthew Breedlove（@sirmalloc）
