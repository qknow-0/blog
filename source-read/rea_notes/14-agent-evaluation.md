# Agent 评估：逆向任务没有标准答案，那怎么评

> 基于 [REA (morluto/rea)](https://github.com/morluto/rea) 源码分析。v6.4.0，commit `edf4624`。
> 系列：REA 源码阅读（14/15）。

## 一句话概括

REA 是给 AI agent 用的工具，所以**「agent 用得好不好」是产品质量的一部分**。

`src/evaluation/`（4 文件，1,153 行）+ `scripts/verify-agent-experience.mjs`（593 行）做这件事。

**但逆向工程任务没有标准答案**——「这个二进制里有没有后门」没有人知道正确答案。

**那怎么评？**

## 生活比喻：自己造赝品，考鉴宝

想考核一个鉴宝师，最直接的方法是拿一批东西让他判断真假。

**问题是：你怎么知道他判对了？** 除非你自己知道每件的真假。

于是有一条看起来绕、但唯一可行的路：

> **你自己仿制一批赝品。**
>
> 每一件怎么做出来的、破绽在哪、**你全都知道**——因为是你做的。
>
> 然后闭卷考他：**不许翻书、不许看你的笔记**，只许用你自己的鉴定工具。

**REA 的评估就是这条路。**

它不让 agent 去分析一个真实的二进制然后由人打分（那没有 ground truth），而是：

**评测方自己合成一个应用 → 打包 → 求哈希 → 把「真相」绑定到确切的字节上 → 然后让 agent 去分析它。**

## 被测的是谁

先澄清一个容易搞错的点：

**评的是 agent（默认 OpenAI Codex CLI）用 REA 做分析的表现，不是评 REA 本身。**

证据在报告的自我描述里（`scripts/verify-agent-experience.mjs:316-317`）：

```javascript
schemaVersion: 4,
evaluationScope: "routing_workflow_and_configured_fixture_claims",
```

**`routing_workflow_and_configured_fixture_claims`**——「路由、工作流、以及**配置了的** fixture 断言」。

**最后那个限定词是核心。**

## 靶子怎么造：三种 ground truth

### 方法一：自己合成靶子，真相是构造性已知的

```typescript
// src/evaluation/AgentEvaluationFixtures.ts:21-28（节选）
const desktopFixtureFiles = {
  "package.json": `${JSON.stringify({ name: "desktop-fixture", version: "1.0.0", main: "main.js" }, null, 2)}\n`,
  "main.js": '...new BrowserWindow({ webPreferences: { preload: ... } });\nipcMain.handle("profile:read", ...);\n',
  "preload.js": '...contextBridge.exposeInMainWorld("profileApi", { read: (id) => ipcRenderer.invoke("profile:read", id) });\n',
  // ...
};
```

**用代码内联生成一个完整的 Electron 桌面应用**，然后用 `@electron/asar` 打包：

```typescript
// AgentEvaluationFixtures.ts:57-65（节选）
return {
  javascript,
  javascriptSha256: createHash("sha256").update(await readFile(javascript)).digest("hex"),
};
```

**最后求哈希——把「真相」绑定到确切的字节上。**

**这样「这个 asar 里有几个 IPC handler」这个问题就有了确定答案：因为是我写的。**

### 方法二：差异已知的两个版本

```typescript
// AgentEvaluationFixtures.ts:48-55（概述）
// 把 tests/fixtures/replay/parser.mjs 与 parser-v2.mjs 复制成左右靶子
// 预期差异：给 heading 增加 depth: 1
```

**对比类任务用「仓库自有、差异已知」的两个版本。**

**因为差异是我制造的，我知道正确答案是「heading 多了个 depth」。**

### 方法三：诚实地说「这个场景没有答案」

```typescript
// AgentEvaluationFixtures.ts:281-288（概述）
// 只有 asar 和 javascript-export-shape 两个场景有 rubric
// 其余返回 undefined
```

而 `evaluateKnownAnswers` 对 undefined 返回 `not_assessed`。

**官方文档把这一点说得很直白**（`docs/testing.md:1328-1333`）：

> **A pass establishes only the configured claims, not unrestricted factual correctness.**
>
> **一次通过只能确立那些配置了的断言，不能确立不受限的事实正确性。**

## 优秀代码一：双记账式判分

### 问题

即使你造了靶子、定了标准答案，还有一层风险：

**模型可能不是从工具输出里推出的答案，而是从别处猜到的、或者干脆编的。**

**而它引用的「证据」可能是伪造的。**

### 源码

判分时同时查**两本账**：

```typescript
// src/evaluation/KnownAnswerEvaluation.ts:382-393
try {
  if (
    !sameJson(
      expected.source.select(evidence.normalized_result),   // 账目 B：从证据里现提取
      expected.expectedValue,                                // 账目 A：人工 oracle
    )
  )
    failures.push("source_assertion_mismatch");
} catch {
  // Producer-specific selectors may reject malformed representations; preserve a failed assessment.
  failures.push("selector_failed");
}
```

而 `select` 是一个**提取函数**，不是死值：

```typescript
// AgentEvaluationFixtures.ts:70-82（节选）
const singleObservation = (value, kind, include = () => true) => {
  const result = javascriptApplicationAnalysisResultSchema.safeParse(value);
  if (!result.success) return undefined;
  const candidates = result.data.graph.nodes
    .filter((node) => node.kind === kind)
    .flatMap((node) => node.observations)
    .filter(include);
  return candidates.length === 1 ? candidates[0] : undefined;   // ← 「恰好一个」才算数
};
```

### 好在哪

**① 两本账必须都平。**

| 账 | 内容 |
|---|------|
| **A：oracle** | 我造靶子时就知道的期望值 |
| **B：证据重提** | 判分时，用 `select` 从证据的 `normalized_result` **当场重新提取** |

**模型声明值必须同时等于 A 和 B 才对。**

**为什么需要 B？**

**因为 A 会「锈掉」。** 产品代码演进了，`normalized_result` 的形状变了——**如果只查 A，这个 fixture 会悄悄失效**（或者更糟：模型答对了旧值，而新版本产出的证据里根本没有那个东西）。

**而 B 会炸**：

```typescript
} catch {
  failures.push("selector_failed");
}
```

**注释说明了这是有意的**：

> **Producer-specific selectors may reject malformed representations; preserve a failed assessment.**
>
> **生产者相关的选择器可能拒绝畸形的表示；保留一个「评估失败」的结果。**

**注意 `preserve` 这个词——不是「跳过」，不是「当作通过」，是「保留失败」。**

**② 「恰好一个」这个约束。**

```typescript
return candidates.length === 1 ? candidates[0] : undefined;
```

**`select` 只在候选数量恰好为 1 时返回值，否则返回 `undefined`。**

而 `undefined !== expectedValue` → 判失败。

**为什么？**

**因为「有 3 个候选，我取第 1 个」是一种猜测。** 如果 fixture 的真值因为产品改动变成了「有 3 个匹配」，**那说明这个断言已经不再精确了**——**应该失败，而不是蒙一个。**

**③ 证据必须能在当前进程里重新认证。**

模型引用的 `evidence_id` 必须命中**已交付且已重新解析**的证据集。

`src/evaluation/KnownAnswerEvaluation.ts:250-258`（概述）：

```typescript
// 解析失败 → 丢弃
// tool !== evidence.operation → 丢弃
```

**而 `evidence_id` 是内容寻址哈希**（[第 5 篇](05-evidence-model.md)讲的）：

```typescript
const computeEvidenceId = (evidence: EvidenceWithoutId): string =>
  `ev_${digestCanonicalValue(semanticProjection(evidence), "Evidence")}`;
```

**并在认证 schema 里重算校验。**

**所以「伪造一个证据 ID」是不可能的**——你没法让 ID 和内容对得上，除非内容真的对。

**④ 递归下钻的边界意识。**

```typescript
// KnownAnswerEvaluation.ts:288-290（注释原文）
// An authenticated parent does not authenticate an embedded record's ID.
```

**「父证据被认证，不代表它里面嵌的记录也被认证。」**

嵌套的 inventory 证据**必须独立重解析**，而且其 ID 要出现在父的 `evidence_links` 里。

**⑤ 评测代码自己也吃这套。**

`scripts/verify-agent-experience.mjs:17-27` import 的是 **`../dist/evaluation/...`**——**编译产物**。

**评测逻辑本身也被打包发布，用的和生产同一套 schema。**

### 模式

**provenance re-authentication（出处再认证）**——**凡是要作为评分依据的数据，必须能在当前进程内用可信代码从原始源重建并自校验。**

### 骨架代码

```typescript
// 1) 只接受明确标记为「完成」的外部调用事件
// 2) 从其输出提取结构化载荷（多拼写别名一致 + 严格 JSON：无注释/尾逗号/重复键）
// 3) 用领域解析器重建对象，重算内容寻址 ID，校验对象与调用元数据一致
// 4) 按 ID 归集；同 ID 不同内容 → conflicts
// 5) 递归下钻的嵌套对象必须独立走 3)
const authenticate = (raw: unknown): Domain | undefined => { /* ... */ };

// 判分：两本账都要平
const judge = (claim, expected, evidence) =>
  sameJson(claim.value, expected.expectedValue) &&                    // 账 A
  sameJson(expected.source.select(evidence.normalized_result),        // 账 B
           expected.expectedValue);
```

**判断标准**：**只要评分依据来自「被测系统自己报告的数据」，就要问——我能独立重建它吗？**

## 优秀代码二：闭卷作答，只给形状不给值

### 源码

```typescript
// src/evaluation/AgentEvaluationFixtures.ts:309-313
"For this benchmark, return only one JSON object, without Markdown fences or surrounding prose.",
'The exact shape is {"claims": [{"id": string, "value": JSON value, "evidence_id": string, "confidence": string, "authority": string}]}.',
"Include exactly one claim per ID below, without additional fields or claims. Infer values only from REA tool results; do not read target files directly.",
"Each evidence_id must identify the successful REA result that supports its claim. Copy confidence and authority from that result's Evidence envelope.",
```

**中文**：

> 本次基准测试**只返回一个 JSON 对象**，不要 Markdown 围栏或前后散文。
>
> 确切的形状是 `{"claims": [{"id": string, "value": JSON value, "evidence_id": string, "confidence": string, "authority": string}]}`。
>
> **每个 ID 恰好一条 claim**，不要额外字段或 claim。**只从 REA 工具结果推断值；不要直接读目标文件。**
>
> 每个 `evidence_id` 必须指向支撑其 claim 的成功 REA 结果。**从那个结果的 Evidence 信封里复制 confidence 和 authority。**

而它的函数注释写着：

```typescript
/** Describe the strict answer contract without revealing any golden fixture values. */
```

**「描述严格的作答契约，但不泄露任何黄金 fixture 值。」**

### 好在哪

**① 把「评不动的自由散文」变成「评得动的闭卷 claim 集」。**

自由散文没法判分——你只能请另一个模型来打分（LLM-as-judge），**而那引入了新的不确定性**。

**REA 的做法是换问题**：不问「你怎么看这个应用」，问「**这个应用里有几个 IPC handler，分别叫什么**」。

**问题一变，判分就从「主观」变成了「比较 JSON」。**

**② 只给形状，不给值——防的是评估作弊。**

```typescript
"The exact shape is {"claims": [...]}"     // ← 给结构
// 但绝不写 {"value": "profile:read"}        // ← 不给值
```

**如果 prompt 里带了答案，模型抄一遍就通过了——而这个通过毫无意义。**

**③ 每个 claim 必须带 `confidence` 和 `authority`。**

```typescript
"Copy confidence and authority from that result's Evidence envelope."
```

**这是把[第 5 篇](05-evidence-model.md)的认识论模型，变成了评分项。**

**模型必须说清楚**：这条是**观测**还是**推断**？证据来自**发布产物**还是**分析者推断**？

**而这两项会被精确比对**（`:358-361`）：

```typescript
// claim_confidence_mismatch / claim_authority_mismatch
```

**也就是说：答案对但「认识论标签」错，照样失败。**

**为什么这个要求合理？**

**因为在逆向工程里，「我怎么知道这件事」和「这件事是什么」同等重要。**

**一个把「我猜的」说成「我看到的」的报告，是危险品**——哪怕猜对了。

### 14 种失败原因

`KnownAnswerEvaluation.ts:28-42` 列出了 14 种失败码，把「模型说谎的每种姿势」都命名了：

```
claim_missing | value_mismatch | claim_confidence_mismatch | claim_authority_mismatch
| unknown_evidence | conflicting_evidence | source_operation_mismatch
| source_confidence_mismatch | source_authority_mismatch | source_subject_mismatch
| source_parameters_mismatch | source_links_mismatch | source_assertion_mismatch
| selector_failed
```

**注意前一半是「claim 侧」的问题，后一半是「source 侧」（证据侧）的问题。**

**「模型答错了」和「证据对不上」被分开了**——**而这决定了问题出在 agent 还是出在产品。**

## 评估的另一半：路由和工作流

事实正确性只是两类指标之一。另一类是**过程指标**（`src/evaluation/CodexAgentEval.ts:22-46`）：

```typescript
export interface CodexAgentMetrics {
  readonly naturalUse: boolean;
  readonly correctFirstTool: boolean;
  readonly firstTool: string | null;
  readonly reaCalls: readonly CodexMcpCall[];
  readonly repeatedCallCount: number;
  readonly inputValidationFailureCount: number;
  readonly requiredToolSubsequenceMet: boolean;
  readonly inputTokens: number;
  readonly cachedInputTokens: number;
  readonly outputTokens: number;
  readonly finalMessage: string;
  readonly evidenceIds: readonly string[];
  /** Whether the answer contains a produced Evidence ID; claim support is not checked. */
  readonly finalCitesEvidence: boolean;
  /** Case-insensitive substring coverage, including terms in negated claims. */
  readonly answerTermCoverageMet: boolean;
  /** Text length, term/cue coverage, and configured transcript checks only. */
  readonly answerHeuristicsMet: boolean;
  /** Whether an epistemic keyword occurs; this does not establish honest authority use. */
  readonly epistemicCuePresent: boolean;
  /** Limited to configured fixture claims; free-form factual correctness is not assessed. */
  readonly factualCorrectness: KnownAnswerAssessment["status"];
}
```

**注意每一条的注释都在主动声明局限**：

- `claim support is not checked`
- `this does not establish honest authority use`
- `free-form factual correctness is not assessed`

**字段名和注释一起读，才知道这个指标能证明什么。**

**这在一个评估系统里是很罕见的自觉**——大多数指标的名字会让人高估它的能力。

### `repeatedCallCount` 的一个精细处理

```typescript
// CodexAgentEval.ts:227-228（注释原文）
// A status read before and after a successful target lifecycle change is useful
// verification, not a duplicate analysis
```

**「在目标生命周期变更前后各读一次状态，是有用的验证，不是重复分析。」**

**所以去重签名里带了 `targetRevision`**——`open_binary` / `close_binary` 成功后 revision +1，**同样的调用在两个 revision 下不算重复。**

**这条注释很有价值**：它区分了「重复劳动」和「确认变更」——**后者是好的行为，不该被惩罚。**

## 门禁：三态降级

```typescript
// src/evaluation/AgentEvaluationReport.ts:22-39
export const agentEvaluationPassed = (
  result: AgentEvaluationGateResult,
): boolean =>
  result.exitCode === 0 &&
  (result.expectedFirstTool === null
    ? !result.naturalUse
    : result.naturalUse) &&
  result.correctFirstTool &&
  result.repeatedCallCount === 0 &&
  result.inputValidationFailureCount === 0 &&
  result.requiredToolSubsequenceMet &&
  result.inputTokens > 0 &&
  (result.expectedFirstTool === null
    ? result.targetClarificationPassed === true
    : result.factualCorrectness === "passed" ||
      (result.factualCorrectness === "not_assessed" &&
        result.answerHeuristicsMet &&
        result.epistemicCuePresent));
```

**这个布尔合取的最后一段是精髓**：

```typescript
result.factualCorrectness === "passed" ||
  (result.factualCorrectness === "not_assessed" &&
    result.answerHeuristicsMet &&
    result.epistemicCuePresent)
```

**翻译成人话**：

- **有 rubric 的场景** → **必须 factual passed**
- **没有 rubric 的场景**（`not_assessed`）→ 退化为**启发式检查**

**「评不了的部分诚实降级，而不是假装评过。」**

**注意 `not_assessed` 不是「通过」，是一个显式的第三态。** 它允许门禁通过，但**报告里会明确写着这个场景没有被事实性评估**（`summarizeFactualCorrectness` 给出 `assessed / passed / failed / notAssessed` 四个计数）。

### 强调：没有 LLM-as-judge

全仓 grep `judge|llm as|rubric`，**没有任何 LLM 裁判调用。**

判分完全是确定性比较：

1. **规范化 JSON 深度相等**——`sameJson` 先过 schema，再对键按码点排序后 `JSON.stringify`
2. **枚举精确匹配**——authority 五值、confidence 三值
3. **内容寻址认证**——证据 ID 重算

**文本启发式（term coverage、epistemic cue 正则、长度 ≥ 80）只作降级和诊断用**：

> `docs/testing.md:1341-1342`: Their answer-text heuristics **are diagnostic and do not affect the gate**.

**等等——这句和上面门禁代码里的 `answerHeuristicsMet` 矛盾吗？**

**不矛盾**：`answerHeuristicsMet` **只在 `not_assessed` 分支里**参与门禁，也就是**没有 rubric 的场景**。**有 rubric 的场景它完全不参与。**

**这解释了为什么那句注释说「不影响门禁」**——指的是「在有事实性评估的地方，文本启发式不起作用」。

### 一个反直觉的场景：`missing-target`

10 个场景里有一个要求 agent **一个 REA 工具都不许调**：

```javascript
// verify-agent-experience.mjs:174-180（概述）
// expectedFirstTool: null
// 要求：目标不明确时，返回结构化的澄清 JSON，而不是瞎猜一个
```

**而门禁对它是**：

```typescript
result.expectedFirstTool === null ? !result.naturalUse : result.naturalUse
```

**`!result.naturalUse`——「没有自然使用」才是通过。**

**这一条在评「agent 知不知道该停手」。**

**大多数评估只测「该做的时候做了没有」，这条测的是「不该做的时候忍住没有」。**

## 隔离：一次性账户，只复制认证

```javascript
// verify-agent-experience.mjs:54-59（概述）
// 环境变量清洗：剔除所有 REA_ | CODEX_ | GHIDRA_ | HOPPER_ | IDA_ 前缀
// 再注入一次性 HOME / USERPROFILE / CODEX_HOME / XDG_*
```

```javascript
// :77-78（注释原文）
// User config, plugins, rules, history and skills must not make a fresh
// installed-skill trial pass accidentally.
```

**「用户的配置、插件、规则、历史和技能，不能让一次『全新安装技能』的试验意外通过。」**

**而只复制 `auth.json`（chmod 0600），不复制 `config.toml`**——配置强制写成：

```toml
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
[features] multi_agent = false
[history] persistence = "none"
```

**只借用户的认证，不借用户的环境。**

**而且走的是公开安装通道**（`:94-115`）：

```bash
scripts/rea.mjs setup --client codex --dry-run
scripts/rea.mjs setup --client codex --yes
# 然后断言装出来的 SKILL.md 版本等于 PRODUCT_IDENTITY.skillVersion
```

**测的是「用户实际的安装体验」，不是「开发者本地的样子」。**

**最后 `finally` 保证清理认证**：

```javascript
// :381-386（注释原文）
// Even a deliberately retained fixture directory must never retain auth.
```

**「即使刻意保留了 fixture 目录，也绝不能保留认证信息。」**

## 代价

### ① 只能评「有答案的部分」

这是最根本的限制，而且**代码自己承认了**。

> A pass establishes only the configured claims, **not unrestricted factual correctness.**

**10 个场景里只有 3 个有事实性 rubric。**

**「agent 会不会做真正的逆向分析」这个最核心的问题，这套评估答不了。**

**它能答的是**：路由对不对、工具调得对不对、引用的证据真不真、认识论标签诚不诚实。

**这些都是「过程正确性」，不是「结论正确性」。**

### ② 靶子是合成的，和真实目标有差距

合成的 Electron 应用只有几个文件。**真实的逆向目标是几 MB 到几百 MB 的二进制。**

**在玩具上看路由正确，不等于在真实目标上正确。**

代码部分对冲了这一点——`large-app` 场景有 **180 个干扰模块**。

### ③ 跑一次很贵

默认超时 **480 秒**，要起真实的 Codex CLI，跑 10 个场景。

**这是发布门禁级别的成本，不是每次提交都跑的。**

### ④ 指标口径要跟着产品改

14 种失败码、17 个指标字段——**产品加一个工具、改一个返回形状，评估代码要跟着改。**

**而评估代码自己不产出证据**：如果 rubric 写错了（期望值本身是错的），**没有任何东西会告诉你。**

（这正是 `select` 那个「恰好一个」约束在防的——期望值失效时会以 `source_assertion_mismatch` 炸出来。）

### ⑤ 只测了一个 agent

默认是 Codex。虽然支持 `REA_CODEX_CLI` / `REA_AGENT_EVAL_MODEL` 换客户端和模型，**但 10 个场景的门禁是针对 Codex 调出来的。**

**换一个 agent，同样的阈值未必合理。**

## 总结

| 结论 | 说明 |
|------|------|
| **评谁** | 评 **agent 用 REA 的表现**，不是评 REA |
| **没有标准答案怎么办** | **自己造靶子**——内联合成应用 + 打包 + 哈希绑定 |
| **双记账判分** | 期望值必须同时等于「人工 oracle」和「从证据现提取的值」 |
| **`select` 要「恰好一个」** | 多个候选 = 断言不再精确 = 失败，不蒙 |
| **闭卷** | **只给 JSON 形状，不给值** |
| **认识论也是评分项** | 每个 claim 必须带 `confidence` / `authority`，且精确比对 |
| **出处再认证** | 证据 ID 是内容寻址哈希，当前进程内重算校验 |
| **三态门禁** | 有 rubric 必须 pass；无 rubric 才允许启发式降级，且标记 `not_assessed` |
| **无 LLM-as-judge** | 全部可判定比较 |
| **反直觉场景** | `missing-target` 要求 agent **一个工具都不调** |
| **隔离** | 一次性账户，**只借认证不借配置** |

**一句话**：这套评估最值得学的不是「怎么造指标」，是**它在每一个地方都诚实标注了自己能证明什么**——

- `claim support is not checked`
- `this does not establish honest authority use`
- `A pass establishes only the configured claims`

**而 `missing-target` 那个场景我认为是整个设计里最有分量的一个：**

**它在测「知道什么时候不该动手」。**

大多数评估测的是能力——能不能做。**而这个场景测的是判断——该不该做。**

**在一个会执行代码、会启动进程、会读用户文件的分析工具上，后者的价值不比前者低。**

---

**下一篇**：[规格文档即约束](15-spec-as-constraint.md)——总结篇：这个仓库怎么把约定变成 CI 里会失败的东西。
