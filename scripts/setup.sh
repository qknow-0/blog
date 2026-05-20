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
echo "初始化完成"
