# superfile：Go 写的终端文件管理器，比 ranger 好看一百倍

> 基于 [yorukot/superfile](https://github.com/yorukot/superfile)，Go + Bubble Tea，MIT 协议。

## 一句话说清楚

superfile（`spf`）是一个 Go 写的终端文件管理器——用 Bubble Tea（Elm 架构 TUI 框架）构建，键盘优先操作，图标渲染，文件操作（复制/移动/删除/压缩/搜索）全在终端里完成。

它解决的不是"终端里能不能管文件"的问题（ranger/lf/vifm 都能），而是**"终端文件管理器能不能好看又好用的问题**"。

## 和 ranger / lf / vifm 的对比

| | superfile | ranger | lf | vifm |
|---|---|---|---|---|
| 语言 | **Go** | Python | Go | C |
| UI 框架 | **Bubble Tea（Elm 架构）** | curses | termbox | curses |
| 图标 | ✅ | ❌ | ❌ | ❌ |
| 配色主题 | ✅ 内置多种 | 需配置 | 需配置 | 需配置 |
| 文件预览 | ✅ 语法高亮 | ✅ | 部分 | 部分 |
| 学习成本 | **低**（直觉式快捷键） | 中（vim 风格） | 中 | 高（双面板） |
| 安装 | 单二进制 | 需要 Python 环境 | 单二进制 | 需要编译 |

superfile 最大的优势：**不需要学**。ranger 的快捷键是 vim 风格的（h/j/k/l），lf 也类似。superfile 用直觉式的键位——方向键导航，Enter 打开，Delete 删除。vim 用户也可以切换到 vim 键位配置。

## 安装

```bash
# macOS / Linux（一键脚本）
curl -fsSL https://superfile.fun/install.sh | bash

# Homebrew
brew install superfile

# Cargo（Rust 用户也可以用）
# 不对，superfile 是 Go 写的，用 go install
go install github.com/yorukot/superfile@latest

# 或者直接下载二进制
# https://github.com/yorukot/superfile/releases
```

Windows：
```powershell
irm https://superfile.fun/install.ps1 | iex
# 或 winget install superfile
# 或 scoop install superfile
```

## 使用

```bash
spf                    # 启动
spf ~/projects         # 打开指定目录
spf --config ~/.config/superfile/config.toml  # 指定配置
```

### 核心快捷键

| 键                     | 操作          |
| --------------------- | ----------- |
| `↑` / `↓` 或 `j` / `k` | 上下导航        |
| `→` / `←` 或 `l` / `h` | 进入目录 / 返回上级 |
| `Enter`               | 打开文件 / 进入目录 |
| `Space`               | 选中文件        |
| `a`                   | 全选          |
| `c`                   | 复制          |
| `x`                   | 剪切          |
| `p`                   | 粘贴          |
| `d` / `Delete`        | 删除          |
| `r`                   | 重命名         |
| `n`                   | 新建文件        |
| `N`                   | 新建目录        |
| `z`                   | 压缩选中文件      |
| `/`                   | 搜索          |
| `.`                   | 显示隐藏文件      |
| `?`                   | 显示帮助        |
| `q` / `Esc`           | 退出 / 取消     |

**文件操作逻辑：** 先用 `Space` 选中文件（可多选），然后按 `c`/`x`/`d`/`z` 等操作键——和桌面文件管理器的操作直觉一致。

## 配置：config.toml

```toml
# ~/.config/superfile/config.toml

# 主题（内置：default, dracula, tokyonight, catppuccin, nord 等）
theme = "default"

# 是否自动检查更新
auto_check_update = true

# 文件预览
preview = true

# 图标（需要终端支持 Nerd Font）
icon = true

# 排序方式
sort_by = "name"        # name, size, modified
sort_reverse = false

# vim 键位模式
# hotkeys = "vim"
```

### 主题

superfile 内置了多种配色主题，一行切换：

```toml
theme = "dracula"     # 德古拉
theme = "tokyonight"  # 东京之夜
theme = "catppuccin"  # Catppuccin
theme = "nord"        # Nord
theme = "gruvbox"     # Gruvbox
```

## 文件预览

打开 superfile 后，选中一个文件，右侧自动显示预览：

- **代码文件**：语法高亮（Go、Python、Rust、JavaScript 等）
- **图片**：终端内显示（需要终端支持，如 Kitty、iTerm2）
- **PDF**：文本内容预览
- **目录**：列出内容

## Bubble Tea 架构：Elm 模型

superfile 用 [Bubble Tea](https://github.com/charmbracelet/bubbletea)（Charm 团队的 Go TUI 框架）构建，遵循 Elm 架构：

```
Model（状态）→ Update（处理事件）→ View（渲染）
```

```go
// 简化的 superfile 架构
type Model struct {
    panels    []*FilePanel     // 文件面板（支持多面板）
    clipboard *Clipboard       // 剪贴板
    search    *SearchState     // 搜索状态
    theme     *Theme           // 当前主题
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        return m.handleKeyPress(msg)
    case tea.WindowSizeMsg:
        return m.handleResize(msg)
    }
    return m, nil
}

func (m Model) View() string {
    return m.renderPanels()  // 渲染所有面板 + 状态栏
}
```

Bubble Tea 的 Model-Update-View 循环让 UI 逻辑非常清晰——所有状态在 Model 里，所有事件在 Update 里处理，View 纯粹是渲染。这是 superfile 能保持代码可维护性的关键。

## 和 Tauri 桌面端的对比

superfile 是纯终端工具。如果你想要一个"看起来像桌面应用但跑在终端里"的文件管理器，它就是最好的选择。但如果你需要：

- 拖拽操作 → 需要桌面应用（Finder、Nautilus、Explorer）
- 鼠标右键菜单 → superfile 不支持（纯键盘）
- 图形化文件预览 → 终端限制，只能做文本/代码预览

## 小结

```bash
# 三条命令记住 superfile
spf                    # 启动
Space → c → p         # 选中 → 复制 → 粘贴
?                      # 不记得快捷键时按这个
```

superfile 的定位很清晰：**不想学 vim 快捷键，但想在终端里管文件的人**。它不是 ranger 的替代品——ranger 用户可能更喜欢 vim 键位的效率。superfile 是给"终端新手但想用终端"的人准备的。

单二进制、零依赖、主题好看、操作直觉。如果你的终端里有 Nerd Font，图标渲染让文件类型一目了然。
