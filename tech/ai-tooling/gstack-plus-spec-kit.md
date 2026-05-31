# gstack + Spec-Kit：打造 AI 编程的完整工作流

单独使用 Spec-Kit 或 gstack 已经能显著提升效率。但两者组合使用，会形成一条从**想法到生产**的完整流水线——Spec-Kit 负责"做对的事"，gstack 负责"把事做对"。

## 分工逻辑

```
Spec-Kit（前半段）              gstack（后半段）
────────────────────            ──────────────────
规范驱动，防止跑偏               角色驱动，防止遗漏
模板约束 → 制品质量              多维审查 → 交付质量
结构化生成 → 一致性              浏览器测试 → 真实验证
```

一张图看清：

```
想法 ──→ /speckit.constitution  （定原则）
  │
  ├──→ /speckit.specify         （写规范）
  │       │
  │       ▼
  │     /office-hours           （挑战产品定位）
  │     /plan-ceo-review        （CEO 视角审查范围）
  │       │
  │       ▼
  ├──→ /speckit.plan            （技术计划）
  │       │
  │       ▼
  │     /plan-eng-review        （工程架构把关）
  │     /plan-design-review     （设计维度打分）
  │       │
  │       ▼
  ├──→ /speckit.tasks           （任务分解）
  ├──→ /speckit.implement       （执行实现）
  │       │
  │       ▼
  │     /review                 （代码审查）
  │     /cso                    （安全审计）
  │       │
  │       ▼
  │     /qa                     （浏览器 E2E 测试）
  │       │
  │       ▼
  └──→   /ship                  （发布）
        /land-and-deploy        （部署验证）
        /retro                  （周回顾）
```

## 为什么需要两者配合

### Spec-Kit 的局限

Spec-Kit 的 `/speckit.implement` 执行完就结束了。它没有：
- **代码审查**：实现是否符合规范？有没有隐藏 bug？
- **浏览器测试**：UI 真的能点吗？页面真的渲染正常吗？
- **安全审计**：用户输入有没有被正确转义？权限检查有没有遗漏？
- **发布流程**：测试覆盖率够吗？CI 过了吗？PR 写了吗？

### gstack 的局限

gstack 的 `/office-hours` 能产出很好的设计文档，但它是自由格式的。它没有：
- **强制模板**：规范一定包含验收标准吗？用户故事格式统一吗？
- **自动分支管理**：每次新功能自动创建 `001-feature-name` 分支？
- **制品版本化**：规范、计划、任务放在 `specs/` 下随代码一起版本控制？

两者正好互补。

---

## 实战：用组合流程做一个功能

以下是一次完整的真实操作——用 gstack + Spec-Kit 开发一个"邮件订阅"功能。

### Step 1：建立原则（Spec-Kit）

```text
/speckit.constitution 创建项目原则：
- TDD 强制，80% 测试覆盖率
- 所有 API 需要 rate limiting
- 禁止硬编码密钥
- 优先使用框架内置功能，不过度抽象
```

输出：`.specify/memory/constitution.md`

### Step 2：编写规范（Spec-Kit）

```text
/speckit.specify 添加邮件订阅功能：
- 用户在页面输入邮箱，点击订阅
- 后端验证邮箱格式，去重后存入数据库
- 发送确认邮件到用户邮箱
- 用户点击确认链接激活订阅
- 支持一键退订
```

Spec-Kit 自动创建分支 `002-email-subscription`，生成 `spec.md`，内含完整的用户故事和验收标准。

### Step 3：产品视角挑战（gstack）

```text
/office-hours 我刚写完一份邮件订阅功能的规范，
帮我审视一下产品定位。
```

Agent 的输出：

```
我读了你的规范，想挑战几个点：

1. 你写的是"邮件订阅"，但用户真正想要的是
   "不错过重要更新"。订阅只是手段。
   如果用户其实更想要 RSS 或者 Telegram
   通知呢？你有没有问过？

2. 确认邮件这个环节——行业平均流失率 20-30%。
   你确定要在这里设门槛吗？如果是冷启动阶段，
   建议先用一步订阅（single opt-in）快速积累
   用户，后续再升级为双重确认。

3. 退订体验你没有写。这是法律要求（CAN-SPAM），
   也是用户信任的关键。退订要一步完成，
   不要搞"输入邮箱确认"那一套。

建议：先验证用户到底想要什么渠道——
做一个落地页，放 3 个选项（邮件/RSS/Telegram），
看用户选哪个。而不是假设邮件是最好的。
```

### Step 4：技术计划（Spec-Kit）

```text
/speckit.plan Next.js 14 App Router + Resend API 发邮件
+ Prisma + SQLite。邮箱验证用 JWT token。
退订用 hash 参数不要登录。
```

Spec-Kit 生成 `plan.md`、`data-model.md`、`contracts/api-spec.json`。

### Step 5：工程审查（gstack）

```text
/plan-eng-review
```

Agent 输出：

```
架构审查结果：

数据流：
  POST /api/subscribe → 验证 → Prisma upsert → Resend.send()
  GET /api/confirm?token=xxx → JWT 验证 → 激活
  GET /api/unsubscribe?hash=xxx → 查找 → 标记退订

发现的潜在问题：
1. JWT token 存在 URL 参数中会被服务器日志记录。
   建议改用 POST body。
2. Resend API key 需要加入 .env.example 并在
   constitution 中明确管理方式。
3. 确认链接过期策略没有定义——建议 7 天。

测试矩阵：
  [P0] 正常订阅 → 收到确认邮件 → 点击激活
  [P0] 重复订阅 → 提示已订阅（不泄露用户状态）
  [P1] 过期 token → 提示重新订阅
  [P1] 退订后重新订阅 → 可以重新激活
  [P2] Resend API 故障 → 优雅降级提示
```

### Step 6：任务分解与实现（Spec-Kit）

```text
/speckit.tasks
/speckit.implement
```

Spec-Kit 按用户故事分组，TDD 方式实现，约 8 分钟输出完整代码。

实现完成后：

```
git log --oneline -5
d7e2f1a feat: 添加退订功能（hash 验证，无需登录）
c4a8b3d feat: 添加确认邮件激活流程
a1d2e3f feat: 添加订阅 API（邮箱验证 + Resend 集成）
```

### Step 7：代码审查（gstack）

```text
/review
```

Agent 输出：

```
审查 commit d7e2f1a ~ a1d2e3f（邮件订阅功能）

[自动修复] 2 个问题：
1. unsubscribe API 缺少 rate limiting
   → 已添加每分钟 10 次限制
2. 邮箱验证正则不允许新 TLD（如 .studio）
   → 已修复为更宽松的校验

[询问] 1 个需要你决策：
你当前的实现中，JWT 的 secret 是从
process.env.JWT_SECRET 读的，但如果这个
环境变量未设置，没有启动时的检查。
建议在 app bootstrap 阶段加一个校验，
要我修复吗？

[完整性检查]
- ✅ 单元测试：12 个
- ✅ 订阅 API 有输入验证
- ✅ 确认/退订使用幂等操作
- ⚠️ 确认邮件模板是纯文本（没有 HTML 版本）
```

输入 `yes`，Agent 自动修复 JWT secret 检查。

### Step 8：浏览器测试（gstack）

```text
/qa http://localhost:3000
```

Agent 启动 Chromium：

```
测试 1: 首页订阅表单
  [✓] 找到邮箱输入框
  [✓] 输入 test@example.com
  [✓] 点击订阅按钮
  [✓] 显示"确认邮件已发送"提示
  [截图] subscription-success.png

测试 2: 重复订阅
  [✓] 再次输入 test@example.com
  [✓] 显示"如果该邮箱已订阅，我们会发送提醒"（不泄露状态）
  [截图] duplicate-subscription.png

测试 3: 空输入
  [✓] 不输入内容直接点击
  [✓] 显示"请输入邮箱地址"
  [截图] empty-input.png

测试 4: 无效邮箱
  [✓] 输入 "not-an-email"
  [✓] 显示"请输入有效的邮箱地址"
  [截图] invalid-email.png

所有测试通过。发现页面在移动端有轻微布局问题：
订阅按钮在 375px 宽度下换行到输入框下方。
已自动修复（flex-wrap → 添加 min-width）。
[截图] mobile-before.png → mobile-after.png
```

### Step 9：安全审计（gstack）

```text
/cso
```

Agent 输出：

```
OWASP Top 10 + STRIDE 审计结果

[PASS] Injection (SQL) — Prisma 参数化查询
[PASS] Broken Auth — 订阅无需登录，设计合理
[PASS] Sensitive Data Exposure — 无敏感日志
[PASS] CSRF — Next.js App Router 默认保护
[FIX] XSS (Stored) — 邮箱地址未做 HTML 转义就存入数据库
  → 已自动修复：添加 zod email 校验 + 输出转义
[FIX] Rate Limiting — 退订端点未限制频率
  → 已自动修复：添加每分钟 5 次限制
[PASS] Supply Chain — 无新依赖引入
[INFO] Security Headers — CSP 未配置，建议后续添加

STRIDE 威胁模型：
[S] Spoofing: 退订 hash 理论上可暴力枚举
  → 建议：hash 用 HMAC-SHA256，不加盐足够
[T] Tampering: JWT 签名已保护
[R] Repudiation: 建议添加操作日志
[I] Info Disclosure: ✅
[D] Denial of Service: ✅（rate limiting 已添加）
[E] Elevation of Privilege: ✅（无权限操作）

2 个问题已自动修复，无 HIGH/CRITICAL 遗留。
```

### Step 10：发布（gstack）

```text
/ship
```

Agent 输出：

```
GitHub PR 已创建：https://github.com/you/app/pull/43

PR 摘要：
feat: 邮件订阅功能
- 订阅 API（邮箱验证 + Resend 集成）
- 确认邮件 + JWT 激活
- 一键退订（hash 验证）
- 12 个单元测试，6 个 E2E 测试
- 测试覆盖率：87%

等待 CI 通过。CI 通过后运行 /land-and-deploy。
```

---

## 组合使用的最佳实践

### 1. Spec-Kit 规范先过 gstack 审查再实现

不要在 `/speckit.specify` 后直接 `/speckit.plan`。先跑一遍 `/office-hours` 或 `/plan-ceo-review`，用产品视角挑战需求本身。很多规范在这个环节被大幅简化甚至推翻——这恰恰是最有价值的时刻。

### 2. gstack 审查结果反馈回 Spec-Kit 规范

`/review` 和 `/cso` 发现的架构级问题，不要只修复代码，也要更新 `spec.md` 和 `plan.md`。否则下一次 `/speckit.implement` 会继续生成同样的 bug。

### 3. 根据功能类型选择 gstack 审查

| 功能类型 | 必跑审查 |
|----------|----------|
| 涉及 UI 的功能 | `/plan-design-review` + `/qa` |
| 后端 API | `/plan-eng-review` + `/cso` |
| 面向开发者的 SDK/CLI | `/plan-devex-review` + `/devex-review` |
| 所有功能 | `/review` |

### 4. 并行使用但要串行决策

`/office-hours` 和 `/speckit.specify` 可以分别在两个 Agent 中运行，但合并结果需要人工判断。不要让两个 AI 互相覆盖对方的工作。

---

## 总结

| 维度 | Spec-Kit 单独 | gstack 单独 | 组合使用 |
|------|:---:|:---:|:---:|
| 规范结构化 | ✅ | ⚠️ | ✅ |
| 产品定位挑战 | ❌ | ✅ | ✅ |
| 工程架构审查 | ⚠️ | ✅ | ✅ |
| 自动分支/版本化 | ✅ | ❌ | ✅ |
| 代码质量审查 | ❌ | ✅ | ✅ |
| 浏览器测试 | ❌ | ✅ | ✅ |
| 安全审计 | ❌ | ✅ | ✅ |
| 发布流程 | ❌ | ✅ | ✅ |
| 周回顾/度量 | ❌ | ✅ | ✅ |

单独使用各有所长，组合使用几乎没有死角。Spec-Kit 保证你在造**正确的东西**，gstack 保证你造出来的东西**经得起考验**。

> Spec-Kit：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
> gstack：[https://github.com/garrytan/gstack](https://github.com/garrytan/gstack)
