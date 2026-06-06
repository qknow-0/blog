# 网文创作系统能用来做项目 plan 吗？——Story System 的通用一致性模式

> 上一篇介绍了 Webnovel Writer，一个用提交链 + 投影 + 检索来维护长篇网文一致性的 Claude Code 插件。这篇文章做一个思想实验——把它的 Story System 映射到项目管理上，聊聊哪些地方可以直接搬、哪些地方需要改。

## 一个意外发现

写完 Webnovel Writer 的分析之后，回头看自己的项目规划流程，发现结构和它出奇地相似：

```
网文创作流程：
  设定集 → 总纲 → 卷纲 → 写章 → 审查 → 提交事实 → 更新索引 → 下一章

项目管理流程：
  架构文档 → 路线图 → milestone → 实现 → review → 记录 ADR → 更新文档 → 下一个迭代
```

不是巧合。这两种活动共享同一个结构——**边推进边记录、边记录边校验、新决策前先查历史**。

## Story System 的核心抽象，改个名字就能用

Webnovel Writer 的 Story System 的核心概念，逐一映射到项目管理：

### 合同（Contract）→ 项目宪章

```
网文：.story-system/contracts/
  世界观基调、战力体系规则、主角性格约束

项目：
  项目宪章/架构决策记录/
  技术栈选择、API 设计原则、不允许做的事
```

网文的 contract 解决「不能写崩」——比如设定了「这个世界没有复活术」，那后面任何角色都不能突然复活。项目的 contract 解决「不能做崩」——比如「所有 API 必须是 RESTful」「不允许引入新的数据库」，后续所有 PR 都要对齐这个约束。

### 提交链（CHAPTER_COMMIT）→ Architecture Decision Record

```
网文：.story-system/commits/chapter_045.commit.json
  本章新事实：萧炎突破斗皇、药老沉睡、纳兰嫣然出场

项目：
  docs/adr/045-add-message-queue.md
  本次决策：引入 RabbitMQ、使用 topic exchange、消息格式 JSON
```

ADR（Architecture Decision Record）和 CHAPTER_COMMIT 完全同构：

- 记录了「什么时候做了什么决定」
- 决定了「后续设计的上游约束」
- 可以被检索和引用

两者的不同是：网文是每章自动生成 commit（data-agent 提取），项目是人工写 ADR。前者的自动化程度更高——这是我们可以偷师的地方。

### 五路投影 → 五路项目视图

```
网文                                  项目
state.json          →             项目状态仪表盘
  角色位置/战力/关系                  服务健康状态/当前 sprint/milestone 进度
index.db            →             可搜索的决策索引
  全文检索「萧炎的战力」             全文检索「为什么选了 gRPC」
summaries/          →             每周摘要/回顾
  每章 200 字摘要                   每周做了什么/下个 milestone 是什么
memory_scratchpad   →             团队经验库
  「战斗场景多写心理变化」            「这个库的性能瓶颈在序列化，别优化网络层」
vectors.db          →             语义相似决策
  「类似的道具在其他章怎么用的」       「类似的架构问题以前怎么解决的」
```

### 审查（review）→ 架构 review

网文的审查维度是爽点、一致性、OOC、节奏、追读力。换成项目就是：

| 网文审查维度 | 项目对应 |
|-------------|---------|
| OOC（角色偏离设定） | 架构偏离——新 PR 违背了当初的 ADR |
| 一致性（战力/时间线前后矛盾） | API 变更打破了向后兼容 |
| 伏笔追踪（登记→推进→回收） | issue/debt 从 open 到 close 的生命周期 |
| 追读力（Hook/Cool-point/微兑现） | 交付节奏——每个 sprint 有没有产出用户可感知的价值 |

### 追读力 → 交付节奏

网文的追读力四维体系换个说法就是 Sprint Retro 的交付健康度：

```
Hook         ← 每个 sprint 的 kickoff 有没有明确目标
Cool-point    ← 有没有值得 demo 的东西
微兑现        ← 小承诺（修 bug、文档更新）有没有兑现
债务追踪      ← 技术债有没有在还，还是只开新坑
```

## 直接用 Webnovel Writer 行不行

**不行**。它的 prompt 模板、审查维度和题材模板是面向网文创作的——拿它去规划后端项目，reviewer 会说你的接口设计「缺乏爽点节奏」。

但它的**系统骨架**是通用的：

1. **提交链 + 投影**：记录决策事实 → 派生出多路可查询视图
2. **preflight + doctor**：前置条件校验 + 分阶段诊断
3. **Agent 分工**：context agent 查历史、reviewer 对约束、data agent 记录事实

## 一个最小可行移植

如果要做一个「项目 plan 版 Story System」，最简方案：

```
project-root/
├── .project-system/
│   ├── contracts/         # 架构约束（不许引入新语言、API 格式标准）
│   │   └── architecture.json
│   ├── commits/           # ADR——每个重大决策一条
│   │   ├── adr_001_choose_grpc.json
│   │   └── adr_002_split_auth_service.json
│   └── projection_log.jsonl
├── .project/
│   ├── state.json         # 当前 sprint、milestone 进度、服务健康
│   ├── index.db           # 全文检索所有 ADR 和 design doc
│   ├── summaries/         # 每周摘要
│   └── memory.json        # 团队经验
├── docs/
│   ├── architecture/      # 架构设计文档
│   └── decisions/          # ADR 列表
└── roadmap.md
```

三条命令覆盖核心流程：

```bash
# 做决策前——查历史
/project-context "消息队列选型"
# → 检索之前的 ADR、相关的 design doc、团队经验

# 做决策后——登记
/project-commit --type adr --title "引入 RabbitMQ" --constraints "topic exchange, JSON 格式"
# → 登记 ADR，更新 state.json，重新索引

# 定期——一致性检查
/project-review --since "last sprint"
# → 检查新决策有没有违反架构约束、依赖有没有循环、债务有没有积累
```

## 真正有意思的不是工具，是模式

Webnovel Writer 最值得学习的东西不是它的 Python 代码或 prompt 模板——而是它让你意识到了**「一致性维护」是一个独立的问题域**。

不管场景是「写 200 章网文」还是「维护一个分布式系统」，核心挑战是一样的：

- 决策会积累 → 需要能被检索
- 约束会被遗忘 → 需要自动检查
- 状态会过期 → 需要推导式更新

传统的做法是文档 + 开会 + code review。Webnovel Writer 的做法是提交链 + 投影 + agent 流水线。后者能不能用到项目管理上？骨架完全可以。剩下的——prompt 模板、审查维度、题材系统——需要针对项目管理重新设计。

这个方向如果认真做，产出的不是「又一个项目管理工具」，而是一套把 Claude Code 的上下文窗口从「当前对话」扩展到「整个项目历史」的约束系统。不是让 AI 记住所有事——而是让 AI 在需要的时候，知道去哪查。
