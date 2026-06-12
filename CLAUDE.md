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
├── thoughts/           # 随想、非技术思考
└── vocabulary/         # 计算机词汇学习（每天 10 个）
```

每个目录下有 `index.md` 作为文章索引。

## 工作约定

- 新文章放到对应分类目录下，文件名使用英文 kebab-case（如 `spec-kit-guide.md`）
- 写完文章后更新对应 `index.md`，并在 `README.md` 对应分类下添加缩进链接，格式：`  - [标题](分类/文件名.md) — YYYY-MM-DD`
- 博文使用中文撰写，Markdown 格式，专业名词保留英文（如 namespace、metaclass、decorator 等不做翻译）
- 文章需要有一定深度和个人理解，不只是罗列知识点——要说清楚 WHY 和背后的设计决策
- languages/ 下的语言语法文章，开头需注明基于的语言版本（如「本文基于 Python 3.12」），文中涉及特性标注最低支持版本
- 技术类文章尽量包含真实实操场景：具体命令、终端输出、浏览器截图、实际运行效果等，避免纯理论描述
- 图形使用 Mermaid 绘制，根据内容选择合适的图型：层次分类用 mindmap，流程/数据流用 flowchart
- 实战场景控制在 1-2 个以内，一般一个就够了，不要堆砌过多案例
- 提交时按文件名逐个 `git add`，避免使用 `git add -A` 误提交敏感文件
- 提交信息格式：`docs: <描述>`
- 尽量每天备份，commit 并 push 当天所有变更后，执行 `./scripts/backup.sh` 将内容备份到坚果云
- **词汇学习提醒**：每次打开这个项目时，提醒用户学习计算机词汇。检查 `vocabulary/index.md` 确认最新进度，准备下一批 10 个新词（存为 `vocabulary/day-NNN.md`），每个词需附带音标，学完后更新 index.md
- **禁止自动推送**：commit 后不要主动 push，等用户确认后再推送
- **脱敏处理**：发布前检查所有文章内容，将真实信息替换为通用示例：
  - 具体应用名称（如某闭源桌面软件）→ 通用描述或示例名（如 SomeApp）
  - 真实域名（如 `example.com` 的自有域名）→ 保留域名（如 `example.com`、`api.example.com`）
  - 真实 IP 地址 → RFC 5737 示例 IP（<目标服务器IP网段>）或私有 IP（`192.168.x.x`）
  - 个人路径（如 `/Users/mac/`）→ `~/`
  - 具体端口号或服务标识符 → 保留标准端口（443、8080），替换特殊端口
  - 保留示例数据、演示代码、通用工具名称——只去掉可追溯性
- **禁止读取 .env 文件**：任何时候都不要读取项目的 .env 文件内容
- `.gitignore` 中的条目需同步到 `scripts/backup.sh` 的 `--exclude` 列表中
- **user.md 与 memory.md 更新约定**：
  - `user.md`（稳定画像）更新频率低——每季度或技术栈/价值观明显转向时更新
  - `memory.md`（当下状态）更新频率高——每新增 10 篇以上文章或每两周，提醒用户是否需要刷新
  - 更新时需通读全库新增文章，而非增量补丁
  - 每次打开项目时，检查距离上次更新 `memory.md` 的文章增量，超过 10 篇则提醒
