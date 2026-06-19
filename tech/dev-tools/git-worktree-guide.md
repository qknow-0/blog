# Git Worktree：同一个仓库，多个工作区同时干活

> `git stash` → 切分支 → 改东西 → `git stash` → 切回去 → `git stash pop`……这套操作你一定很熟。但有一种更好的方式——同一份代码，同时打开多个工作目录，互不干扰。

## 是什么

`git worktree` 让你在**同一个仓库**上同时拥有**多个独立的工作目录**：

```text
~/project/                      # 主工作区，在 main 分支，正在重构
~/project/.worktrees/hotfix/    # worktree 1，在 hotfix 分支，紧急修 bug
~/project/.worktrees/feature/   # worktree 2，在 feature 分支，写新功能
```

三个目录，三套文件，各自独立操作——但背后共享同一个 `.git` 对象数据库。

## 为什么需要它

假设你在 `feature/new-api` 分支上写了一半，突然生产环境炸了要紧急修 bug：

```bash
# 传统方式
git stash                    # 暂存当前未完成的改动
git checkout main
git checkout -b hotfix/crash  # 切去修 bug
# ... 修好了，commit
git checkout feature/new-api  # 切回来
git stash pop                 # 恢复之前写到一半的代码
# 祈祷 stash pop 不冲突 🙏
```

每一步都是**上下文切换的成本**。更糟的是：

- `stash` 可能跟目标分支冲突
- 如果你忘了 stash，checkout 直接失败
- 切回来之后脑子里的上下文已经丢了一半
- 同时跑两个以上的任务几乎不可能

Worktree 解法：

```bash
# 不停当前工作，直接开新 worktree
git worktree add -b hotfix/crash ../project-hotfix main
cd ../project-hotfix
# 修 bug，commit，完事
git worktree remove ../project-hotfix
# 原工作区纹丝不动，上下文全在
```

**零上下文切换**——这才是 worktree 真正的价值。

## 核心原理

普通 clone 一个仓库，`.git` 目录包含所有数据：

```text
.git/
  objects/     ← 所有 commit、tree、blob 都存在这里（几十 MB 到几 GB）
  refs/        ← 分支、标签的指针
  HEAD         ← 当前分支
  index        ← 暂存区
```

`git worktree add` 不会重新 clone——它做的是：

```text
主 worktree (~/project/)
  .git/
    objects/       ← 完整的对象数据库（共享）
    refs/
    HEAD           ← ref: refs/heads/main
    index          ← main 分支的暂存区
    worktrees/     ← 存放其他 worktree 的元数据
      project-hotfix/
        HEAD       ← ref: refs/heads/hotfix/crash
        index      ← hotfix 分支的暂存区

新 worktree (~/project-hotfix/)
  .git              ← 一个文本文件，指向主仓库的 .git
  src/              ← hotfix 分支 checkout 出来的文件
  README.md
```

关键点：

- **对象数据库共享**——不重新下载、不占额外磁盘空间（除了 checkout 文件）
- **创建几乎瞬间完成**——只需要把目标分支的文件 checkout 到新目录
- **每个 worktree 有独立的 index 和 HEAD**——git 操作完全隔离

## 常用命令

### 创建 worktree

```bash
# 基于已有分支创建
git worktree add ../project-hotfix hotfix/crash

# 创建新分支 + worktree（一步到位）
git worktree add -b feature/payment ../project-payment main

# 基于某个 commit 创建（detached HEAD）
git worktree add --detach ../project-experiment v2.0.0

# 从远程分支创建
git worktree add -b fix/typo ../project-typo origin/main
```

### 查看和管理

```bash
# 列出所有 worktree
git worktree list
# 输出示例：
# /Users/me/project             fdedac3 [main]
# /Users/me/project-hotfix      e5b1ee4 [hotfix/crash]
# /Users/me/project-payment     08725ec [feature/payment]

# 查看某个 worktree 的状态
git -C ../project-hotfix status

# 加 --porcelain 做脚本化
git worktree list --porcelain
```

### 删除 worktree

```bash
# 删除 worktree（改动必须先 commit 或 discard）
git worktree remove ../project-hotfix

# 强制删除（丢弃未提交的改动）
git worktree remove --force ../project-hotfix

# 清理已手动删除目录的 worktree 记录
git worktree prune
```

### 锁定 worktree

```bash
# 锁定——防止被 prune 误删（适合长期保留的 worktree）
git worktree lock ../project-hotfix --reason "等 CI 通过后再合并"

# 解锁
git worktree unlock ../project-hotfix
```

## 实战场景

### 场景 1：紧急修 bug，不打断当前工作

```bash
# 当前在 feature/refactor 分支上改写了一大堆，还没法 commit
# 生产告警来了——某接口 5xx

git worktree add -b hotfix/panic ../project-hotfix main
cd ../project-hotfix
# 定位问题 → 修复 → 测试 → commit → push
cd ~/project
git merge hotfix/panic
git worktree remove ../project-hotfix
git branch -d hotfix/panic
# 回到之前的重构，上下文完全没丢
```

### 场景 2：同时跑多个 AI Agent

这是 worktree 最前沿的应用场景——Orca IDE 的核心抽象：

```bash
# 三个 Agent，三个 worktree，三个独立任务
git worktree add -b agent/fix-auth  ../project-auth  main
git worktree add -b agent/new-api   ../project-api   main
git worktree add -b agent/refactor  ../project-refactor main

# 各自在各自的 worktree 里跑
cd ../project-auth    && claude "修复 JWT 刷新逻辑"
cd ../project-api     && claude "给 /users 加分页接口"
cd ../project-refactor && claude "把 ORM 从 Diesel 换成 SeaORM"

# 各自 commit，最后由你合并
```

### 场景 3：长时间构建不阻塞编辑

```bash
# CI 上某个平台的编译挂了，要本地复现
git worktree add --detach ../project-build ci-failed-commit

cd ../project-build
# 跑一个要 20 分钟的编译
make build-all-platforms

# 主工作区继续写代码，完全不受影响
```

### 场景 4：Code Review 时跑代码验证

```bash
# PR #42 的改动很大，你想本地跑一下试试
git worktree add ../project-pr42 main
cd ../project-pr42
git fetch origin pull/42/head:pr-42
git checkout pr-42
npm test && npm start  # 跑起来看看

# 主工作区不受影响
```

### 场景 5：版本对比

```bash
# 同时打开 v2.0 和 v3.0，对比行为差异
git worktree add ../project-v2 v2.0.0
git worktree add ../project-v3 v3.0.0

# 两个终端并排，一边看 v2 输出一边看 v3 输出
```

## Worktree vs 其他方案

| 场景 | git stash | 重新 clone | git worktree |
|---|---|---|---|
| 修紧急 bug | stash → 切分支 → 改 → stash pop | clone → 修 → push → 回来 | add → 修 → remove |
| 磁盘开销 | 无 | 完整复制（几百 MB~几 GB） | 只 checkout 文件（几十 MB） |
| 创建速度 | 即时的 | 慢（网络下载） | 几乎即时（本地 checkout） |
| 上下文保持 | ❌ stash pop 可能冲突 | ✅ 但隔离过头了 | ✅ 隔离但共享 Git 数据 |
| 多任务并行 | ❌ 只能一个 | ✅ | ✅ |
| 适用任务数 | 1 个 | 1~2 个 | 无限制 |

**什么时候用哪种**：

- **stash**：临时切换，改动很小，马上切回来。比如「等一下我切个分支看个东西」
- **clone**：完全独立的工作——不同目录、不同 IDE 窗口、甚至不同机器
- **worktree**：需要隔离工作区但共享 Git 历史——多任务、多 Agent、构建验证

## 常见坑

### 1. 同一个分支不能在两个 worktree 同时 checkout

```bash
# ❌ 报错
git worktree add ../dup main
# fatal: 'main' is already checked out at '/Users/me/project'

# ✅ 用 -b 创建新分支
git worktree add -b my-work ../dup main
```

### 2. 子模块需要额外处理

Worktree 创建时会复制子模块，但建议每个 worktree 里单独 `git submodule update --init`。

### 3. 忘记清理

Worktree 删了目录但没 `git worktree remove`，会残留记录：

```bash
# 定期清理
git worktree prune

# 查看过期记录
git worktree list
```

### 4. 不要在 worktree 目录里 `git init` 或删 `.git` 文件

Worktree 的 `.git` 是一个文件（不是目录），指向主仓库。删了它 worktree 就断了。

## 小结

Git worktree 是一个被严重低估的命令。大多数人知道 `stash`、`branch`、`checkout`，但不知道 worktree 能让你**同时存在于多个分支上**。

核心价值就一句话：**隔离工作区，共享 Git 数据**。没有上下文切换、没有 stash 冲突、没有等待。

AI Agent 时代的到来让 worktree 从「偶尔有用的技巧」变成了「基础设施级别的原语」——Orca 这类多 Agent IDE 把它作为架构基础不是偶然，而是因为 Agent 之间的隔离需求天然匹配 worktree 的隔离模型。

---

**相关阅读：**
- [Orca：为并行 AI Agent 设计的下一代 IDE](../ai-tooling/orca-guide.md)
- [Claude Code 完全指南](../claude-code/index.md)
- [开发工具索引](index.md)
