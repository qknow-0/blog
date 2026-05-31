# gstack：一个人如何像一支团队一样交付

> "I don't think I've typed like a line of code probably since December." — Andrej Karpathy, 2026

[gstack](https://github.com/garrytan/gstack) 是 Y Combinator CEO **Garry Tan** 开源的 AI 编程工具包。它的核心思路很简单：**把 Claude Code 变成一个完整的虚拟工程团队**。

## 背景：一个人的软件工厂

Garry Tan 的背景是：Palantir 早期工程师/PM/设计师，Posterous 联合创始人（后被 Twitter 收购），YC 内部社交网络 Bookface 的构建者。现在是 YC 的 CEO。

他公开了一组数据——用逻辑代码变更量（而非 AI 膨胀后的原始行数）衡量：

- **2026 年产出速率是 2013 年的 ~810 倍**（11,417 vs 14 逻辑行/天）
- 2026 年前 4 个月已经产出了 **2013 全年的 240 倍**
- 过去 60 天：3 个生产服务、40+ 个功能，兼职完成，主业是运营 YC

gstack 就是他实现这一切的方式。

## gstack 是什么

gstack 不是一个框架，而是一套**流程 + 角色 + 工具**的组合。它包含 23 个专业角色和 8 个增强工具，通过 Claude Code 的斜杠命令调用，全部 Markdown 定义，MIT 开源。

核心哲学：**Think → Plan → Build → Review → Test → Ship → Reflect**。每一步的输出是下一步的输入，不会出现信息断裂。

## 完整角色体系

### 思考阶段

| 命令 | 角色 | 职责 |
|------|------|------|
| `/office-hours` | YC Office Hours | 起点。6 个强制性问题挑战你的产品定位，产出设计文档 |
| `/plan-ceo-review` | CEO/创始人 | 重新思考问题。4 种模式：扩展、选择性扩展、保持范围、缩减 |
| `/plan-eng-review` | 工程经理 | 锁定架构、数据流、边界情况、测试矩阵 |
| `/plan-design-review` | 高级设计师 | 每个设计维度打分 0-10，说明满分长什么样，AI 糟粕检测 |
| `/plan-devex-review` | 开发者体验负责人 | 20-45 个强制问题，3 种模式，对标竞品 TTHW |

### 构建阶段

| 命令 | 角色 | 职责 |
|------|------|------|
| `/design-shotgun` | 设计探索者 | 生成 4-6 个变体，浏览器中并排对比，收集偏好，迭代优化 |
| `/design-html` | 设计工程师 | 将设计稿转化为生产级 HTML/CSS，30KB 零依赖，自适应布局 |
| `/autoplan` | 审查管线 | 一条命令串联 CEO→设计→工程审查，只把品味决策留给你 |

### 审查阶段

| 命令 | 角色 | 职责 |
|------|------|------|
| `/review` | 资深工程师 | 找到 CI 通过但生产会炸的 bug，自动修复明显的，标记完整性缺口 |
| `/codex` | 第二意见 | 用 OpenAI Codex 做独立审查。三种模式：审查门禁、对抗挑战、开放咨询 |
| `/cso` | 首席安全官 | OWASP Top 10 + STRIDE 威胁模型。17 个误报排除规则，8/10+ 置信度门槛 |
| `/design-review` | 会写代码的设计师 | 审查后直接修复，原子提交，before/after 截图 |

### 测试阶段

| 命令 | 角色 | 职责 |
|------|------|------|
| `/qa` | QA 负责人 | 打开真实浏览器，点击测试流程，发现 bug，原子提交修复，生成回归测试 |
| `/qa-only` | QA 报告员 | 只报告，不改代码 |
| `/browse` | QA 工程师 | 给 AI 装上眼睛。真实 Chromium 浏览器，真实点击，真实截图 |

### 交付与反思

| 命令 | 角色 | 职责 |
|------|------|------|
| `/ship` | 发布工程师 | 同步 main，运行测试，覆盖率审计，推送，开 PR |
| `/land-and-deploy` | 发布工程师 | 合并 PR，等待 CI 和部署，生产验证 |
| `/canary` | SRE | 部署后监控，控制台错误、性能回退、页面故障 |
| `/benchmark` | 性能工程师 | 基准测试 Core Web Vitals，每次 PR 前后对比 |
| `/retro` | 工程经理 | 周回顾。每人细分、交付连续记录、测试健康趋势 |

### 安全与保障

| 命令 | 功能 |
|------|------|
| `/careful` | 拦截危险命令（rm -rf、DROP TABLE、force-push） |
| `/freeze` | 锁定编辑范围到一个目录 |
| `/guard` | 两者同时启用，生产环境最大安全 |

---

## 实战：一个完整 Sprint 的真实流程

Garry 在 README 中展示了一个从想法到 PR 的完整流程，这是 gstack 最有说服力的地方：

```
你：我想做一个日历每日简报 App。

你：/office-hours

Claude：[追问痛点 — 要具体例子，不要抽象描述]

你：多个 Google 日历，事件信息过时，位置经常是错的。
    准备工作巨耗时，最终效果也不行...

Claude：我要挑战你的问题定义。你说的是"每日简报 App"，
        但你真正描述的是一个个人幕僚长 AI。
        [提取了 5 个你自己都没意识到的能力需求]
        [挑战了 4 个前提假设 — 你同意/反对/修正]
        [生成了 3 种实现方案，标注了工作量]
        建议：先做一个最窄的可用版本，明天就交付，
        在真实使用中学习。完整愿景是 3 个月的项目。
        先做一个真正有效的每日简报。
        [输出设计文档 → 自动输入下游技能]

你：/plan-ceo-review
    [读取设计文档，挑战范围，执行 10 段式审查]

你：/plan-eng-review
    [架构的 ASCII 图、状态机、错误路径]
    [测试矩阵、故障模式、安全问题]

你：批准计划。退出规划模式。
    [输出 2400 行代码，跨越 11 个文件。约 8 分钟。]

你：/review
    [自动修复] 2 个问题。[询问] 竞态条件 → 你批准修复方案。

你：/qa https://staging.myapp.com
    [打开真实浏览器，点击测试流程，发现并修复了一个 bug]

你：/ship
    测试：42 → 51（+9 新增）。PR：github.com/you/app/pull/42
```

你说的是"每日简报 App"，AI 听到的是"你在做一个幕僚长 AI"——因为它听的是痛点，而不是功能描述。8 条命令，端到端。这不是副驾驶，这是一支团队。

---

## 设计管线：从头脑风暴到可交付页面

gstack 最特别的地方是设计管线的设计：

1. **`/design-shotgun`** — 描述你想要什么，AI 生成 4-6 个方案，在浏览器中并排对比。你选出喜欢的，留下反馈（"留白再多一点"、"标题加粗"），AI 生成下一轮。几轮之后**品味记忆**开始起作用，自动偏向你真正喜欢的风格。

2. **`/design-html`** — 把选中的设计稿变成可交付的 HTML/CSS。不是那种只在一个宽度能看的 AI HTML——用的是 Pretext 计算布局，文字真的会随缩放换行，高度自适应内容。检测你的框架（React/Svelte/Vue），输出对应格式。

---

## 并行 Sprint：真正的生产力来源

gstack 在单个 Sprint 中已经很强了。但一个 Sprint 变成 10 个并行时，才是质变。

结合 [Conductor](https://conductor.build) 这样的工具，可以在独立工作空间中同时运行：
- 一个在 `/office-hours` 探索新想法
- 一个在 `/review` 审查 PR
- 一个在实施功能
- 一个在 `/qa` 测试预发布环境
- 还有 6 个在处理其他分支

**流程体系是并行的关键**。没有流程，10 个 Agent 就是 10 个混乱源。有了流程（思考→规划→构建→审查→测试→交付），每个 Agent 都知道该做什么、什么时候停。

---

## 安全机制：不只追求快

gstack 在安全上投入了不亚于效率的工程：

- **Prompt 注入防御**：22MB ML 分类器 + Claude Haiku 转录检查 + 随机金丝雀令牌 + 双模型共识判决
- **`/careful`**：拦截所有破坏性命令，避免 AI 误操作
- **`/freeze`**：锁定编辑范围，调试时不会意外修改无关代码
- **`/cso`**：独立安全审计，17 个误报排除规则，每个发现附具体利用场景

---

## 安装与使用

### 前提条件
- Claude Code
- Git
- Bun v1.0+

### 30 秒安装

在 Claude Code 中粘贴执行：

```
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

### 团队模式（推荐）

```bash
(cd ~/.claude/skills/gstack && ./setup --team) && \
  ~/.claude/skills/gstack/bin/gstack-team-init required && \
  git add .claude/ CLAUDE.md && \
  git commit -m "require gstack for AI-assisted work"
```

每个 Claude Code 会话启动时自动检查更新（每小时限流一次，网络失败安全，完全静默）。

---

## 适用场景

- **创始人和 CEO** — 尤其是技术背景、还想亲自交付的
- **首次使用 Claude Code** — 结构化的角色体系替代了空白提示框
- **Tech Lead 和资深工程师** — 每个 PR 都有严谨审查、QA 和发布自动化

---

## 总结

gstack 解决了一个核心问题：**AI 编程助手给你的是能力，但给不了工作流**。你当然可以让 Claude 帮你写代码，但没有结构的情况下，质量和一致性高度依赖你的提示技巧。

gstack 把 YC 级别的产品思维和工程纪律编码成了一套可复用的命令体系。它不是一个让你写更多代码的工具，而是一个让你写更少代码、但产出更高质量成品的系统。

在 AI 编程工具满天飞的 2026 年，gstack 代表的方向可能比任何单一模型的能力提升都重要——**不是更聪明的 AI，而是更聪明的 AI 协作方式**。

> 官方仓库：[https://github.com/garrytan/gstack](https://github.com/garrytan/gstack)
> MIT 开源，永久免费。
