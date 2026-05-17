# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目说明

纯 Markdown 个人知识库，零构建、零依赖。通过 Git 与 GitHub 同步。

## 目录结构

```
blog/
├── README.md           # 知识库导航首页
├── tech/               # 技术笔记（框架、工具）
├── languages/          # 编程语言（语法、特性）
├── project-retro/      # 项目复盘
├── architecture/       # 架构设计、技术方案
├── reading/            # 阅读笔记（书、文章、视频）
├── source-read/        # 源码阅读（开源项目的源码分析）
└── thoughts/           # 随想、非技术思考
```

每个目录下有 `index.md` 作为文章索引。

## 工作约定

- 新文章放到对应分类目录下，文件名使用英文 kebab-case（如 `spec-kit-guide.md`）
- 写完文章后更新对应 `index.md`，并在 `README.md` 对应分类下添加缩进链接，格式：`  - [标题](分类/文件名.md) — YYYY-MM-DD`
- 博文使用中文撰写，Markdown 格式
- languages/ 下的语言语法文章，开头需注明基于的语言版本（如「本文基于 Python 3.12」），文中涉及特性标注最低支持版本
- 技术类文章尽量包含真实实操场景：具体命令、终端输出、浏览器截图、实际运行效果等，避免纯理论描述
- 图形使用 Mermaid 绘制，根据内容选择合适的图型：层次分类用 mindmap，流程/数据流用 flowchart
- 实战场景控制在 1-2 个以内，一般一个就够了，不要堆砌过多案例
- 提交时按文件名逐个 `git add`，避免使用 `git add -A` 误提交敏感文件
- 提交信息格式：`docs: <描述>`
- 尽量每天备份，commit 并 push 当天所有变更后，执行 `./scripts/backup.sh` 将内容备份到坚果云
- **禁止自动推送**：commit 后不要主动 push，等用户确认后再推送
- **禁止读取 .env 文件**：任何时候都不要读取项目的 .env 文件内容
