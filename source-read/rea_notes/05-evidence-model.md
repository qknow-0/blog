# 证据模型：「未知」为什么不是一个枚举值

> 基于 [REA (morluto/rea)](https://github.com/morluto/rea) 源码分析。v6.4.0，commit `edf4624`。
> 系列：REA 源码阅读（5/15）。

## 一句话概括

`AGENTS.md:5` 有一句话：

> Distinguish **observations, derivations, inferences, and unknowns**; preserve Evidence provenance and session semantics through both adapters.

前三个是**一个三值枚举**。**第四个不是。**

```typescript
confidence: z.enum(["observed", "derived", "inferred"])   // 三值，unknown 不在其中
```

**`unknown` 是一个独立的一等实体**，有自己的 ID、修订链、状态机、消解条件。

**为什么不能把它塞进枚举里？** 这篇讲的就是这个设计决策。

## 生活比喻：证据袋和待查清单

侦探办案有两样东西：

| | 证据袋 | 待查清单 |
|---|--------|---------|
| **装什么** | 已经拿到的东西——指纹、监控、口供 | **还没查清的问题**——「凶器来源不明」 |
| **每条带什么** | 标签：「亲眼所见」「化验推出」「推测」 | 编号、优先级、**「查到什么程度算查清」** |
| **会变吗** | 拿到就固定了 | **会**——「调查中」→「受阻」→「已证实」/「已排除」 |
| **能重复吗** | 同一条证据只能有一份 | 同一个问题可以反复提出（同一个编号） |

**关键区别**：证据是**静态的**，问题是**有生命周期的**。

```
「我看到张三 21:00 在楼下」     ← 这条一旦记下就不变了。它只需要一个标签说明可信度。
「凶器从哪来的？」             ← 这个会一直变：在查、卡住了、排除了、证实了。
```

**把「凶器来源不明」当成一个标签贴在证据袋上，就没法记录它的进展了。**

这就是 REA 把 unknown 做成独立实体的原因。

## 两类维度：confidence 和 authority

先看证据本身。`src/domain/evidence.ts:110-129`：

```typescript
const evidenceBaseSchema = z
  .object({
    evidence_id: prefixedDigestSchema("ev"),
    subject: subjectSchema.nullable(),
    provider: providerSchema,
    analysis_profile: analysisProfileSchema.nullable(),
    predicate_type: z.string().min(1),
    operation: z.string().min(1),
    parameters: jsonObjectSchema,
    raw_result: jsonValueSchema.nullable(),
    normalized_result: jsonValueSchema,
    confidence: z.enum(["observed", "derived", "inferred"]),
    authority: evidenceAuthoritySchema,
    environment: executionEnvironmentSchema.nullable(),
    limitations: z.array(z.string()),
    relationship_coverage: relationshipCoverageSchema.nullable().default(null),
    locations: z.array(evidenceLocationSchema),
    evidence_links: z.array(prefixedDigestSchema("ev")),
  })
  .strict();
```

`confidence` 是**怎么得到的**：

| 值 | 含义 | 例子 |
|---|------|------|
| `observed` | 直接观测 | 「Ghidra 报告这个地址有 5 个调用者」 |
| `derived` | 由观测推导 | 「调用图可达，所以 A 能到 B」 |
| `inferred` | 推测 | 「命名风格相似，可能出自同一模块」 |

而 `authority` 是**从哪来的**——另一条正交的轴（`evidence.ts:95-101`）：

```typescript
const evidenceAuthoritySchema = z.enum([
  "shipped-artifact",       // 从发布产物里读的
  "controlled-replay",      // 受控重放实验得到的
  "historical-reference",   // 历史资料
  "external-service",       // 外部服务
  "analyst-inference",      // 分析者推断
]);
```

**两条轴正交**：一条证据可以是「`observed`（我直接看到的）+ `analyst-inference`（但它来自我的推断性操作）」。

这比单一「可信度分数」表达力强得多——**「怎么看出来的」和「从哪来的」是两个独立的问题。**

### 注意 `raw_result` 和 `normalized_result` 并存

```typescript
raw_result: jsonValueSchema.nullable(),
normalized_result: jsonValueSchema,
```

**两个都留着。** 归一化之后的版本方便程序消费，原始版本保留「引擎到底回了什么」。

**归一化会丢信息**——这是它的定义。把原始值一起存下来，才能在事后质疑归一化是否正确。

## 关键设计：unknown 是实体，不是标签

```typescript
// src/domain/residualUnknown.ts:44-83（节选）
const residualUnknownObjectSchema = z.object({
  unknown_id: unknownIdSchema,
  revision: z.number().int().min(1),
  previous_revision_digest: z.string().regex(/^[a-f0-9]{64}$/u).nullable(),
  revision_digest: z.string().regex(/^[a-f0-9]{64}$/u),
  scope_digest: z.string().regex(/^[a-f0-9]{64}$/u).nullable(),
  question: text,
  status: z.enum([
    "open",
    "investigating",
    "blocked",
    "contradicted",
    "resolved",
  ]),
  severity: z.enum(["low", "medium", "high", "critical"]),
  domain: text,
  supporting_evidence_ids: z.array(evidenceIdSchema),
  contradicting_evidence_ids: z.array(evidenceIdSchema),
  required_authority: z.enum([...]).nullable(),
  required_confidence: z.enum(["observed", "derived", "inferred"]),
  required_environment: environmentRequirementSchema.nullable(),
  recommended_probes: z.array(probeSchema),
  relationships: z.array(relationshipSchema),
  resolution: resolutionSchema.nullable(),
  mutation_evidence_ids: z.array(evidenceIdSchema).min(1),
});
```

**看它带了什么证据条带不了的东西：**

| 字段 | 证据为什么不需要 |
|------|----------------|
| `status` 五态 | 证据不会「卡住」 |
| `revision` + `previous_revision_digest` | 证据不可变，改了就是另一条 |
| `severity` | 「这个问题有多重要」是问题的属性 |
| `required_authority` / `required_confidence` | **这是关键——见下**
| `recommended_probes` | 「该用什么手段去查」 |

### 最妙的一处：unknown 复用了那个三值枚举

```typescript
required_confidence: z.enum(["observed", "derived", "inferred"]),
```

**同一个枚举，换个位置，意思完全不同。**

- 在证据上，它是**陈述**：「这条是怎么得到的」
- 在未知上，它是**要求**：「要消解我，你至少得拿出这个置信度的证据」

**「未知」被建模成「一个待满足的要求」**，而不是「一个缺口」。

这带来一个很强的性质：**每一个未知都自带验收标准。** 它不是「这里我不知道」，而是「这里我不知道，**而且我知道什么才算知道**」。

## 优秀代码一：消解闸门

### 源码

`src/domain/evidenceBundle.ts:454-481`：

```typescript
const evidenceQualifies = (
  unknown: ResidualUnknown,
  evidence: Evidence,
): boolean => {
  if (
    unknown.required_authority !== null &&
    evidence.authority !== unknown.required_authority
  )
    return false;
  const confidenceRank = { inferred: 1, derived: 2, observed: 3 } as const;
  if (
    confidenceRank[evidence.confidence] <
    confidenceRank[unknown.required_confidence]
  )
    return false;
  const requirement = unknown.required_environment;
  if (requirement === null) return true;
  if (evidence.environment === null) return false;
  return (
    (requirement.id === null || requirement.id === evidence.environment.id) &&
    (requirement.platform === null ||
      requirement.platform === evidence.environment.platform) &&
    (requirement.architecture === null ||
      requirement.architecture === evidence.environment.architecture) &&
    (requirement.isolation === null ||
      requirement.isolation === evidence.environment.isolation)
  );
};
```

### 好在哪

**三点。**

**① 置信度被显式排成序，而不是比较字符串。**

```typescript
const confidenceRank = { inferred: 1, derived: 2, observed: 3 } as const;
```

**「三个值的枚举」和「三个值有强弱关系」是两件事。** 排成 `Record` 之后：

- 比较变成一次数值比较
- **`as const` + `Record<Confidence, number>` 让「枚举少一个值」变成编译错误**

如果你写 `{ inferred: 1, derived: 2 }` 漏掉 `observed`，TS 会因为不满足 `Record` 而报错。**又是一个用类型系统保穷尽的例子。**

**② `authority` 是精确相等，不是偏序。**

```typescript
if (unknown.required_authority !== null &&
    evidence.authority !== unknown.required_authority)
  return false;
```

**`controlled-replay`（受控重放）的证据，不能消解一个要求 `shipped-artifact`（发布产物）的问题。**

为什么？因为它们是**不同种类的证据**，不是强弱关系。文档 `docs/reconstruction-obligation-ledgers.md:318-321` 说得很直白：

> A green unit test cannot close a `packaged-process` obligation. A static-only source cannot close a runtime or process claim.
>
> **一个通过的单元测试，关不掉一条「打包后进程行为」的义务。只有静态分析，关不掉一条运行时断言。**

**这是整个证据模型最重要的一条规则**：**证据的种类必须匹配问题的种类，强弱排不上用场。**

**③ `null = 通配`的字段级语义。**

```typescript
(requirement.id === null || requirement.id === evidence.environment.id) &&
```

一个结构就能表达三档约束：

| 写法 | 含义 |
|------|------|
| `requirement = null` | 任意环境 |
| `{platform: "linux", id: null}` | 任意 Linux 环境 |
| `{platform: "linux", id: "fixture-linux", architecture: "x86_64", isolation: "process"}` | 精确匹配 |

**不需要为「宽松/严格」写两套类型。**

### 还有一道锁：元证据不能自我消解

消解校验里还有两个条件（`evidenceBundle.ts:357-378`）：

```typescript
const qualifies = unknown.resolution?.evidence_ids.some((evidenceId) => {
  const evidence = evidenceById.get(evidenceId);
  return (
    unknown.supporting_evidence_ids.includes(evidenceId) &&
    evidence !== undefined &&
    evidence.predicate_type !== "rea.residual-unknown-mutation" &&   // ← 关键
    evidenceQualifies(unknown, evidence)
  );
});
```

**`predicate_type !== "rea.residual-unknown-mutation"` 这一条在防什么？**

因为「**记录一个未知**」这个动作**本身也会产生一条 Evidence**：

```typescript
// src/application/investigation/UnknownEvidence.ts:24-47（节选）
export const unknownMutationEvidence = (target, mutation): Evidence =>
  createEvidence(target, UNKNOWN_REGISTRY_PROVIDER, {
    predicateType: "rea.residual-unknown-mutation",
    operation: mutation.operation,
    // ...
    confidence: "derived",
    authority: "analyst-inference",
    limitations: [
      "Registry mutation evidence records analyst intent, not proof of the answer.",
    ],
  });
```

**这条 limitation 写得极好**：

> 注册表变更证据记录的是**分析者的意图**，不是**答案的证明**。

**如果不排除它，就会出一个荒谬的循环**：「我登记了这个未知」→ 产生一条证据 → 这条证据可以消解这个未知。**登记一个问题就等于回答它。**

### 模式

**资格判定（qualification gate）**——把「什么算解决了」写成可执行的函数，而不是靠人判断。

### 骨架代码

```typescript
// 「要求」用 null = 通配表达，不需要多态
type Requirement = {
  authority: Authority | null;
  minConfidence: Confidence;
  environment: EnvRequirement | null;
};

// 置信度显式排序，避免字符串比较
const rank = { inferred: 1, derived: 2, observed: 3 } as const satisfies Record<Confidence, number>;

// 资格 = 三个正交维度全过
const qualifies = (req: Requirement, ev: Evidence): boolean =>
  (req.authority === null || ev.authority === req.authority) &&          // 种类必须匹配
  rank[ev.confidence] >= rank[req.minConfidence] &&                       // 只有这条有强弱
  (req.environment === null ||
    (ev.environment !== null && fieldsMatch(req.environment, ev.environment)));

// 应用时必须再加两条：证据得在 supporting 列表里，且不能是「登记动作」的元证据
```

**判断标准**：任何「这个问题算不算解决了」的判断，只要会被反复问，就值得写成函数。**靠人判断的验收标准，会随人而变。**

## 优秀代码二：内容寻址的证据 ID

### 源码

```typescript
// src/domain/evidence.ts:234-259（节选）
/** Hash semantic content, including raw results and excluding display-subject fields. */
const semanticProjection = (evidence: EvidenceWithoutId): JsonValue => ({
  subject:
    evidence.subject === null
      ? null
      : {
          digest: evidence.subject.digest,
          format: evidence.subject.format,
          architecture: evidence.subject.architecture,
          // 注意：name 和 local_path 被排除在外
        },
  provider: evidence.provider,
  // ...
});
```

```typescript
// src/domain/evidence.ts:234-263
const computeEvidenceId = (evidence: EvidenceWithoutId): string =>
  `ev_${digestCanonicalValue(semanticProjection(evidence), "Evidence")}`;
```

底层是 SHA-256 over RFC 8785 规范化 JSON。

### 好在哪

**「语义哈希」这四个字是字面意思——它刻意排除了展示字段。**

同一份二进制文件：

| 字段 | 进哈希？ | 为什么 |
|------|:---:|--------|
| `digest.sha256` | ✅ | 这是文件的**身份** |
| `format` / `architecture` | ✅ | 语义 |
| **`name`** | ❌ | 你把它叫 `app.apk` 还是 `my-app.apk`，**是同一份东西** |
| **`local_path`** | ❌ | 在你的机器上是 `~/Downloads/x`，在同事机器上是 `/tmp/y`，**还是同一份东西** |

**后果非常重要**：同一份产物在不同机器上、不同路径下，**产生同一个 `evidence_id`**。

这才让「跨会话导入证据包」成为可能——导入时靠 ID 去重，如果 ID 里含路径，**同一个文件在两个人那里会被当成两条不同的证据。**

### 顺带的三重好处

**① 防篡改是免费的。** 解析时重算 ID 并比对：

```typescript
// src/domain/evidence.ts:158-168（节选）
const authenticatedEvidenceSchema = evidenceSchema.superRefine((evidence, context) => {
  const { evidence_id: evidenceId, ...withoutId } = evidence;
  if (computeEvidenceId(withoutId) !== evidenceId)
    context.addIssue({
      code: "custom",
      path: ["evidence_id"],
      message: "Evidence semantic identifier does not match its record",
    });
});
```

**改了内容，ID 就对不上。** 不需要单独的校验和机制。

**② 去重是天然的。** 同 ID 同内容 = `duplicate`（不是错误），同 ID 不同内容 = `EvidenceIntegrityError`：

```typescript
// src/application/investigation/EvidenceLedger.ts:47-71（节选）
const existing = this.#records.get(evidence.evidence_id);
if (existing !== undefined) {
  if (existing === evidence) return ok("duplicate");
  return recordsAgree(existing, evidence)
    ? ok("duplicate")
    : err(new EvidenceIntegrityError("Conflicting evidence record"));
}
```

**③ 身份比较也用同一套投影**——比较两条证据是否「同一条」时，先抹掉 `name` 和 `local_path` 再比：

```typescript
// EvidenceLedger.ts:454-468（节选）
const withoutLocalPath = (evidence: Evidence): Evidence => ({
  ...evidence,
  subject: evidence.subject === null ? null : {
    ...evidence.subject,
    name: "<non-identity-name>",
    local_path: "<non-identity-local-path>",
  },
});
```

**「什么是身份」只定义一次，去重、比较、校验三处共用。**

### 构造时的一个性能技巧

计算 ID 需要先有一份完整对象，但 schema 校验又要求 `evidence_id` 存在。朴素的写法是校验两遍（一遍验证，一遍算完 ID 再验）——而 `normalized_result` 可能有几十 MB。

解法是**占位符先过，算完再回填**：

```typescript
// src/domain/evidence.ts:428-435 + :337-341
const normalized = selectedSchema.parse({
  ...semantic,
  evidence_id: `ev_${"0".repeat(64)}`,   // ← 占位符，满足 schema 格式
  subject,
});
// ...
const evidence = { ...normalized, evidence_id: computeEvidenceId(normalized) };
```

**`"0".repeat(64)` 正好满足 `ev_[a-f0-9]{64}` 的格式**，所以能通过校验。然后算真实 ID 回填。

**payload 只解析一次。** 这是个很小但很实在的优化。

### 模式

**内容寻址（content addressing）**——ID 从内容派生，而非从创建时间/随机数派生。

### 骨架代码

```typescript
// 1) 定义「语义投影」：只含参与身份的内容
const semanticProjection = (v: T): JsonValue => ({
  digest: v.digest,
  format: v.format,
  // 刻意排除：展示名、本地路径
});

// 2) ID = sha256(canonicalJson(projection))，带命名空间前缀
const computeId = (v: T): string =>
  `ev_${createHash("sha256").update(canonicalize(semanticProjection(v))).digest("hex")}`;

// 3) 构造：占位符先 parse，再回填真实 ID（大 payload 只解析一次）
const normalized = schema.parse({ ...semantic, id: `ev_${"0".repeat(64)}` });
return { ...normalized, id: computeId(normalized) };

// 4) parse 时重算并拒绝不一致（免费防篡改）
schema.superRefine((v, ctx) => {
  const { id, ...rest } = v;
  if (computeId(rest) !== id) ctx.addIssue({ code: "custom", path: ["id"], message: "..." });
});
```

**判断标准**：只要你的记录需要**跨环境去重**，就该用内容寻址。**含路径、含时间戳的 ID，换台机器就失效。**

## 三态裁决：不把「不知道」说成「通过」

证据模型最后落到判断上。`src/domain/conformanceTrustGate.ts:355-359`：

```typescript
const verdict: TrustGateResult["verdict"] = hasFail
  ? "fail"
  : hasUnknown
    ? "unknown"
    : "pass";
```

**`unknown` 是独立终态，绝不被折叠成 `pass`。**

而下游的规则更硬（`docs/reconstruction-readiness.md:48-49`）：

> `fail` / `unknown` / `unsupported` / `truncated` / `skipped` **永不聚合为 `pass`**。

**五个「不通过」相关的状态，没有一个会因为其他部分通过而被冲淡。**

这和[第 2 篇](02-domain-layer.md)里 `buildCallPath` 那个 `status: exhaustive ? "not_found" : "unknown"` 是同一个原则，只是尺度从「一次搜索」扩大到「一次重建验证」。

**同一个价值观贯穿：不能证明的，不许说成确定的。**

## 代价

### ① 实体比枚举贵得多

一个 `ResidualUnknown` 有 **20 个字段**，要存、要校验、要传、要序列化。

而如果只是枚举里的一个值，成本是零。

**这个代价是刻意的**——因为「未知」在这个项目里需要**被追踪**，而不是被记录一下就算了。

### ② 校验链很长

导入一个证据包要过：

1. schema 校验
2. 重复 ID 检查
3. `validateUnknownGraph`——引用完整性、revision 链、消解资格
4. **依赖无环检测**（手写栈 DFS，避免深链爆调用栈）
5. **canonical 回比**——清单必须与重算结果逐字节一致

```typescript
// src/domain/evidenceBundle.ts:290-291
if (JSON.stringify(parsed) !== JSON.stringify(canonical))
  throw new TypeError("Evidence bundle manifests are not canonical");
```

**这套校验的成本随数据量增长，而它跑在导入路径上。**

### ③ 概念负担

`confidence` / `authority` / `status` / `severity` / `disposition`——**五个不同的分类维度**，每个都有自己的词表。

还有个真实的混淆风险：`confidence` 有三个值（observed/derived/inferred），而 `reconstructionCoverage.ts:30-36` 里另有一个**五值** `authority`（observed/derived/inferred/historical/external）——**同样的词，不同的集合，不同的文件。**

**这是设计演化留下的痕迹**，不是精心规划的。读懂它需要先在脑子里建一张表。

### ④ 一致性靠测试和校验，不靠约定

`status === "resolved"` 必须和 `resolution !== null` 同真同假，`contradicted` 必须带矛盾证据，同一条证据不能既支持又矛盾——**这些交叉约束全靠 zod 的 `refine` 逐条写出来。**

加一个状态就要想清楚它和所有既有字段的组合。**状态空间是乘法增长的。**

## 总结

| 结论 | 说明 |
|------|------|
| **三 + 一** | `observed/derived/inferred` 是一个枚举；**`unknown` 是独立实体** |
| **为什么** | 前三者是**陈述**（描述一条记录），unknown 是**有生命周期的问题**（修订、状态、消解） |
| **两条正交轴** | `confidence`（怎么得到的）× `authority`（从哪来的） |
| **自带验收标准** | unknown 复用 `confidence` 枚举，但语义变成**要求**：「要消解我，至少拿出这个」 |
| **种类必须匹配** | authority 是精确相等，不是偏序——**单元测试关不掉运行时断言** |
| **内容寻址** | ID 是语义哈希，排除 `name`/`local_path`，跨机器可去重 |
| **元证据排除** | 「登记一个问题」产生的证据，不能消解它自己 |
| **三态裁决** | `fail` / `unknown` / `pass`，**unknown 永不折叠为 pass** |

**一句话**：这套证据模型的核心不是「记录得很细」，是**把「不知道」建模成了可以推进的对象**——

**它不是一个空洞，是一个带编号、带优先级、带验收标准、带调查建议的待办事项。**

而 `required_confidence` 复用 `confidence` 枚举这个设计，是整个模型里最优雅的一处：**陈述和要求用同一套词表，于是「这条证据够不够格」变成了一个纯粹的类型判断，不需要人解释。**

**「我不知道」和「我不知道什么算知道」，是两个完全不同的问题。** 大多数系统只回答了前一个。

---

**下一篇**：[组装根](06-composition-root.md)——23 个文件、542 行，为什么组装这根可以这么薄。
