# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目说明

纯 Markdown 个人知识库，零构建、零依赖。通过 Git 与 GitHub 同步。

## 目录结构

```
blog/
├── README.md           # 知识库导航首页
├── tech/               # 技术笔记（语言、框架、工具）
├── project-retro/      # 项目复盘
├── architecture/       # 架构设计、技术方案
├── reading/            # 阅读笔记（书、文章、视频）
└── thoughts/           # 随想、非技术思考
```

每个目录下有 `index.md` 作为文章索引。

## 工作约定

- 新文章放到对应分类目录下，文件名使用英文 kebab-case（如 `spec-kit-guide.md`）
- 写完文章后更新对应 `index.md` 中的文章列表，格式：`- [标题](文件名.md) — YYYY-MM-DD`
- 博文使用中文撰写，Markdown 格式
- 提交信息格式：`docs: <描述>`
