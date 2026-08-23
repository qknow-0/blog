# git-cliff：用 Git 提交历史自动生成 CHANGELOG

> 基于 [git-cliff](https://github.com/orhun/git-cliff)，Rust 实现，Apache-2.0/MIT 双许可。

## 一句话

git-cliff 是一个 Rust 写的 changelog 生成器——读取你的 git commit 历史，按 conventional commits 分类（feat/fix/refactor），用 Tera 模板渲染成 Markdown/JSON/HTML 格式的 CHANGELOG。一条命令生成，不需要手写。

## 安装

```bash
# macOS
brew install git-cliff

# Cargo
cargo install git-cliff

# npm
npm install -g git-cliff

# GitHub Releases
curl -L https://github.com/orhun/git-cliff/releases/latest/download/git-cliff-x86_64-unknown-linux-gnu.tar.gz | tar xz
```

## 基本用法

```bash
# 在项目根目录运行——自动从 git log 生成 CHANGELOG.md
git cliff

# 生成从 v1.0.0 到 v2.0.0 之间的 changelog
git cliff v1.0.0..v2.0.0

# 只生成最新未发布版本的 changelog（unreleased）
git cliff --unreleased

# 输出为 JSON
git cliff --output - --format json

# 指定输出文件
git cliff -o CHANGELOG.md

# 追加到已有文件（不覆盖）
git cliff --prepend CHANGELOG.md
```

## 配置文件：cliff.toml

git-cliff 的所有行为由 `cliff.toml` 控制。首次运行 `git cliff --init` 生成默认配置：

```toml
[changelog]
# 文件头部模板（Tera 模板语法）
header = """
# Changelog\n
All notable changes to this project will be documented in this file.\n
"""

# 每个 commit 的渲染模板
body = """
{% if version %}\
    ## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}\
    ## [unreleased]
{% endif %}\
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        - {% if commit.breaking %}[**breaking**] {% endif %}{{ commit.message | upper_first }}\
    {% endfor %}
{% endfor %}\n
"""

footer = ""
trim = true

[git]
# 解析 conventional commits
conventional_commits = true
filter_unconventional = true
# 自定义正则解析（可选）
# commit_parsers = [
#     { message = "^feat", group = "Features" },
#     { message = "^fix", group = "Bug Fixes" },
# ]
# 忽略的标签
# ignore_tags = ".*-rc.*"
# 按提交时间排序
sort_commits = "oldest"
```

## 模板语法：Tera

git-cliff 用 [Tera](https://keats.github.io/tera/)（Rust 的 Jinja2 等价物）做模板渲染。模板中可以访问的变量：

| 变量 | 含义 |
|---|---|
| `{{ version }}` | 当前 tag 版本 |
| `{{ message }}` | commit 消息（去掉 type/scope 前缀后的描述） |
| `{{ group }}` | 分组名（Features、Bug Fixes 等） |
| `{{ timestamp }}` | 提交时间戳 |
| `{{ breaking }}` | 是否是 breaking change |
| `{{ scope }}` | conventional commit 的 scope |

### 自定义 commit 分组

默认情况下，git-cliff 按 conventional commit 的 type 分组（`feat` → Features，`fix` → Bug Fixes）。你也可以自定义：

```toml
[git]
commit_parsers = [
    { message = "^feat", group = "🚀 Features" },
    { message = "^fix", group = "🐛 Bug Fixes" },
    { message = "^perf", group = "⚡ Performance" },
    { message = "^refactor", group = "🔧 Refactoring" },
    { message = "^docs", group = "📝 Documentation" },
    { message = "^chore", group = "📦 Chores", skip = true },  # 跳过 chore
]
```

## 生成效果

假设你有这些 commit：

```
feat: add dark mode support
feat(api): add rate limiting
fix: resolve crash on startup
fix(auth): token refresh race condition
perf: optimize database queries
refactor: extract auth module
docs: update README
chore: update dependencies
```

运行 `git cliff` 后生成：

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-07-21

### 🚀 Features
- Add dark mode support
- (api) Add rate limiting

### 🐛 Bug Fixes
- Resolve crash on startup
- (auth) Token refresh race condition

### ⚡ Performance
- Optimize database queries

### 🔧 Refactoring
- Extract auth module
```

`chore` 被 `skip = true` 跳过了。`docs` 如果没在 commit_parsers 里定义，也不会出现在输出中。

## 实用场景

### 1. 追加到已有 CHANGELOG

```bash
# 不覆盖，追加到文件头部
git cliff --prepend CHANGELOG.md
```

### 2. GitHub Actions 自动生成

```yaml
# .github/workflows/release.yml
- name: Generate Changelog
  uses: orhun/git-cliff-action@v4
  with:
    args: --unreleased --tag ${{ github.ref_name }}
  env:
    OUTPUT: CHANGELOG.md
```

### 3. 只生成两个 tag 之间的差异

```bash
git cliff v1.5.0..v2.0.0 -o RELEASE_NOTES.md
```

### 4. Monorepo：只生成某个子目录的 changelog

```bash
git cliff --include-path "packages/core/**" -o packages/core/CHANGELOG.md
```

### 5. 过滤特定作者的 commit

```toml
[git]
# 忽略 bot 的 commit
commit_filters = [
    { author = "dependabot", skip = true },
    { author = "renovate", skip = true },
]
```

## 和 conventional-changelog 的对比

| | git-cliff | conventional-changelog |
|---|---|---|
| 语言 | **Rust**（单二进制） | Node.js（需要 npm 环境） |
| 速度 | **快**（Rust 解析 git log） | 慢（JS + 子进程调用 git） |
| 模板引擎 | Tera（编译时模板） | Handlebars |
| 配置 | `cliff.toml`（TOML） | `.versionrc` / package.json |
| 输出格式 | **Markdown / JSON / HTML** | 主要 Markdown |
| 依赖 | **零**（静态编译二进制） | 需要 node_modules |
| 学习成本 | 低（一条命令就能用） | 中（需要配置 commitlint 等） |

git-cliff 最大的优势：**零依赖**。不需要装 Node.js，不需要 `npm install`，一个二进制文件搞定。在 CI 环境里特别方便——Docker 镜像里直接放一个 git-cliff 二进制就行。

## 和 standard-version / release-please 的区别

git-cliff **只生成 changelog**——不改 package.json 版本号、不打 tag、不发布。它和 standard-version（改版本号 + 打 tag + 生成 changelog 三合一）的定位不同：

| | git-cliff | standard-version | release-please |
|---|---|---|---|
| 生成 changelog | ✅ | ✅ | ✅ |
| 自动 bump 版本号 | ❌ | ✅ | ✅ |
| 打 tag | ❌ | ✅ | ✅ |
| 创建 GitHub Release | ✅（`--tag` 参数） | ❌ | ✅ |
| 适用场景 | 只要 changelog | 完整的 release 流程 | GitHub 自动 release |

如果你只需要 changelog（版本号自己管），git-cliff 是最简单的选择。

## 小结

```bash
# 三条命令记住 git-cliff
git cliff                    # 生成 CHANGELOG.md
git cliff --unreleased       # 只生成未发布部分
git cliff --init             # 生成默认配置
```

零依赖、Rust 写的、模板驱动、conventional commits 开箱即用。如果你的项目已经用 conventional commits（`feat:`、`fix:`、`refactor:`），加一条 `git cliff` 到 CI 就能自动维护 CHANGELOG。
