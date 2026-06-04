#!/bin/bash
# setup.sh — 新机初始化脚本，幂等（已安装的跳过）
set -e

echo "===== 基础工具 ====="

# Homebrew
if ! command -v brew &>/dev/null; then
    echo "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew 已安装"
fi

# Git
if ! command -v git &>/dev/null; then
    echo "安装 Git..."
    brew install git
else
    echo "Git 已安装"
fi

echo ""
echo "===== 容器运行时 ====="

# OrbStack
if ! command -v orb &>/dev/null; then
    echo "安装 OrbStack..."
    brew install orbstack
else
    echo "OrbStack 已安装"
fi

# Docker CLI（OrbStack 需要）
if ! command -v docker &>/dev/null; then
    echo "安装 Docker CLI..."
    brew install docker
else
    echo "Docker CLI 已安装"
fi

echo ""
echo "===== 编辑器 ====="

# Zed
if ! command -v zed &>/dev/null; then
    echo "安装 Zed..."
    brew install --cask zed
else
    echo "Zed 已安装"
fi

echo ""
echo "===== AI 编程助手 ====="

# Claude Code
if ! command -v claude &>/dev/null; then
    echo "安装 Claude Code..."
    curl -fsSL https://claude.ai/install.sh | bash
else
    echo "Claude Code 已安装"
fi

echo ""
echo "===== 包管理器 ====="

# uv
if ! command -v uv &>/dev/null; then
    echo "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "uv 已安装"
fi

# Bun
if ! command -v bun &>/dev/null; then
    echo "安装 Bun..."
    curl -fsSL https://bun.sh/install | bash
else
    echo "Bun 已安装"
fi

echo ""
echo "===== AI 工具链 ====="

# Spec-Kit
if uv tool list 2>/dev/null | grep -q specify-cli; then
    echo "Spec-Kit 已安装"
else
    echo "安装 Spec-Kit..."
    uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
fi

# gstack
if [ -d ~/.claude/skills/gstack ]; then
    echo "gstack 已安装"
else
    echo "安装 gstack..."
    git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
    cd ~/.claude/skills/gstack && ./setup
fi

# RTK
if command -v rtk &>/dev/null; then
    echo "RTK 已安装"
else
    echo "安装 RTK..."
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/main/install.sh | bash
fi

# code-review-graph
if command -v code-review-graph &>/dev/null; then
    echo "code-review-graph 已安装"
else
    echo "安装 code-review-graph..."
    pip install code-review-graph
    code-review-graph install
fi

# ccstatusline
if [ -d ~/.claude/skills/ccstatusline ]; then
    echo "ccstatusline 已安装"
else
    echo "安装 ccstatusline..."
    git clone --single-branch --depth 1 https://github.com/sirmalloc/ccstatusline.git ~/.claude/skills/ccstatusline
    cd ~/.claude/skills/ccstatusline && ./setup
fi

# agentmemory
if [ -d ~/.claude/skills/agentmemory ]; then
    echo "agentmemory 已安装"
else
    echo "安装 agentmemory..."
    git clone --single-branch --depth 1 https://github.com/rohitg00/agentmemory.git ~/.claude/skills/agentmemory
fi

echo ""
echo "初始化完成"
