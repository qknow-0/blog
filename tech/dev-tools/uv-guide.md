# uv：让 Python 包管理快 100 倍的下一代工具

Python 生态的包管理一直是个痛点。pip 太慢，pip-tools 要维护两套文件，Poetry 的解析器偶尔卡住，pipenv 更是早已被社区放弃。**uv** 是 Astral（Ruff 的团队）用 Rust 重写的 Python 包与项目管理器，彻底解决了这些问题。

## 为什么是 uv

一句说完：**pip、pip-tools、pipx、poetry、pyenv、virtualenv 的所有功能，一个二进制文件搞定，快 10-100 倍**。

实际数字：

```bash
# 安装一个包的对比
pip install flask       # ~5 秒
uv pip install flask    # ~0.2 秒

# 创建虚拟环境
python -m venv .venv    # ~2 秒
uv venv                 # ~0.02 秒
```

uv 本身就是用 Rust 写的，依赖解析器也是 Rust 实现，靠 SIMD 和并行化把「等一会」变成了「瞬间」。

## 安装

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS Homebrew
brew install uv

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# pip（已有 Python 的话）
pip install uv
```

验证：

```bash
uv --version
# uv 0.10.x
```

## 核心功能实战

### 创建虚拟环境

```bash
uv venv
# 在当前目录创建 .venv，自动检测 Python 版本

uv venv --python 3.12
# 指定版本，如果没装会自动下载
```

### 安装包

```bash
# 全局工具（替代 pipx）
uv tool install ruff

# 项目内安装
uv pip install flask pytest

# 从 requirements.txt
uv pip install -r requirements.txt
```

### 项目管理（替代 Poetry）

```bash
# 初始化项目
uv init my-python-app
cd my-python-app

# 添加依赖
uv add flask
# 自动写入 pyproject.toml，自动创建或更新 uv.lock

# 开发依赖
uv add --dev pytest ruff

# 运行
uv run flask run

# 运行脚本
uv run python main.py

# 同步环境到 lock 文件
uv sync
```

### 锁定依赖

```bash
# 生成 uv.lock（替代 pip freeze）
uv lock

# 导出到 requirements.txt（给不支持 uv 的环境用）
uv export --format requirements-txt > requirements.txt
```

### Python 版本管理（替代 pyenv）

```bash
# 查看可用版本
uv python list

# 安装 Python 3.12
uv python install 3.12

# 指定项目 Python 版本
uv python pin 3.12
```

## 和现有工具的直接对应

| 你以前用 | 换成 uv |
|----------|---------|
| `python -m venv .venv` | `uv venv` |
| `pip install flask` | `uv pip install flask` |
| `poetry add flask` | `uv add flask` |
| `poetry run pytest` | `uv run pytest` |
| `pipx install ruff` | `uv tool install ruff` |
| `pip freeze > requirements.txt` | `uv export` |
| `pyenv install 3.12` | `uv python install 3.12` |
| `pip install -e .` | `uv pip install -e .` |

## 关键特性

- **所有依赖解析和安装都是异步并行**，网速不再是瓶颈
- **全局缓存**：同一个包（同一个 hash）只下载一次，跨所有项目共享
- **零拷贝安装**：硬链接而非复制文件，装几十个包瞬间完成
- **`pyproject.toml` 原生支持**：和 PEP 621 完全兼容
- **跨平台**：macOS、Linux、Windows 同等支持

## 实战：把一个 Poetry 项目迁到 uv

假设已有 Poetry 管理的项目：

```bash
cd my-existing-project

# 1. 初始化 uv（保留原有 pyproject.toml）
uv init . --no-readme

# 2. 把 Poetry 的依赖迁移过来
uv add $(cat pyproject.toml | grep -A100 '\[tool.poetry.dependencies\]' | grep '"' | sed 's/.*"\(.*\)".*/\1/')

# 3. 生成锁文件
uv lock

# 4. 删掉旧环境
rm -rf .venv poetry.lock

# 5. 重新同步
uv sync

# 6. 验证
uv run pytest
```

迁移后：
- 安装时间从 30-60 秒变成 1-3 秒
- `uv.lock` 替代 `poetry.lock`
- 不再需要 `poetry shell`，直接用 `uv run`

## 总结

uv 的终极目标是**让 Python 包管理从痛点变成幸福感**。它做到了几个关键点：

1. **快** — 快到你觉得没出 bug，因为以前这个操作要等好几秒
2. **统一** — 不再需要 pip/pipx/poetry/pyenv/venv 五套工具混用
3. **兼容** — 完全兼容现有的 `pip`、`requirements.txt`、`pyproject.toml` 生态
4. **内存友好** — Rust 的零成本抽象，用起来完全没有 Electron 工具那种"卡"

如果今天新开一个 Python 项目，uv 是最值得第一个 `pip install` 的工具。

> 官方仓库：[https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)
> 官方文档：[https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
