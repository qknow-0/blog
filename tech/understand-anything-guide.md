# Understand-Anything：新团队接手的第一个命令

刚加入一个新项目。200,000 行代码，80 个模块，没人替你梳理过架构。你打开代码库，grep 搜了几个关键词，读完 20 个文件，花了两个小时——还是不知道支付流程到底走了哪些函数。

Understand-Anything 做的事：打通 Claude Code 的多 Agent 管线，把代码库分析成一张可点的知识图谱，开一个可视化 Dashboard。不再是 grep 盲搜，而是像看地图一样看代码。

## 安装

Claude Code 原生插件，两条命令：

```
/plugin marketplace add Lum1104/Understand-Anything
/plugin install understand-anything
```

其他平台（Codex、Cursor、Copilot、Gemini CLI 等）用一行脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.sh | bash
```

## 核心命令

八个斜杠命令覆盖了从初探到深度分析的各种场景：

```
/understand                    # 首次分析：多 Agent 扫描全项目，构建知识图谱
/understand-dashboard          # 打开交互式可视化页面
/understand-chat 支付流程怎么工作？  # 基于图谱的对话式问答
/understand-diff               # PR 变更影响分析
/understand-explain src/auth/login.ts  # 单个文件深度解析
/understand-onboard            # 自动生成新人上手指南
/understand-domain             # 提取业务领域建模
/understand-knowledge ~/wiki   # 分析文档/知识库
```

一条平常用的最多的路径：

```
/understand              → 首次分析，建图
/understand-dashboard    → 打开可视化页面，全局浏览
/understand-chat ...     → 带着具体问题深入挖掘
```

之后每次代码变完再跑 `/understand`，增量模式只重分析改了的部分。加上 `--auto-update` 还可以挂到 post-commit hook 上自动更新。

## Dashboard：代码变成可点的地图

`/understand-dashboard` 打开一个 Web 页面，代码库被渲染成力导向图：

- 每个节点是一个文件、函数或类
- 边表示依赖、调用、继承关系
- 颜色按架构层级自动分组——API 层蓝色、Service 层绿色、Data 层橙色
- 点一个节点，右边弹出它的总结说明、上下游关系、代码片段

不用装额外工具，不用配数据库。Dashboard 就是一个本地 HTML 页面，浏览器直接打开。

## 不只是结构图——业务视角

大多数代码可视化工具给的是工程结构。`/understand-domain` 给的是业务视角——把代码里的领域概念提取出来，按业务流程重新组织：

```
认证领域
  └─ 登录流程
       ├─ 凭证验证
       ├─ Session 创建
       └─ 权限加载
  └─ 注册流程
       ├─ 邮箱验证
       ├─ 个人信息填写
       └─ 初始角色分配
```

对新接手业务的人，这张图比目录树有用得多。

## 中文友好

默认输出英文，加 `--language zh` 切到中文：

```
/understand --language zh
```

图谱节点描述、Dashboard UI 标签和提示、引导浏览的讲解——全变成中文。对英文不是阅读主语言的开发者，这个参数降了很多阅读成本。

## 和其他代码图谱工具的区别

| | Understand-Anything | CodeGraph | code-review-graph |
|------|:---:|:---:|:---:|
| 主要场景 | 代码库初探 | 日常开发探索 | PR 审查 |
| 可视化 | 交互式 Dashboard | 无 | D3.js 力导向图 |
| 安装 | Claude Code 插件 | npx | pip |
| 业务视角 | 域建模支持 | 无 | 无 |
| 多语言 | 6 种语言 | 无 | 无 |
| 新人上手 | onboard 命令 | 无 | 无 |

三个工具的定位互补：CodeGraph 做日常探索，code-review-graph 做代码审查，Understand-Anything 做代码库速通和团队上手。

## 适合什么场景

- 接手新项目，理解整体架构和关键路径
- 开源项目初探，快速定位感兴趣的模块
- 跨团队协作，让对方了解你的代码结构
- 新人入职，自动生成上手指南

不适合：日常小改动和单文件编辑——这种情况下 CodeGraph 更轻量。

> 仓库：[https://github.com/Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything)
> 演示：[https://understand-anything.com/demo/](https://understand-anything.com/demo/)
