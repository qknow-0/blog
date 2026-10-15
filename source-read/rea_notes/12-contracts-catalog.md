# 契约层：目录顺序永远不能决定用哪个操作

> 基于 [REA (morluto/rea)](https://github.com/morluto/rea) 源码分析。v6.4.0，commit `edf4624`。
> 系列：REA 源码阅读（12/15）。

## 一句话概括

`AGENTS.md:25` 有一句约束：

> Validate advertised JSON Schemas **after SDK conversion** against their declared dialect and actual clients. Bind handlers to named contracts with exact types; **catalog ordering must never select an operation or schema.**

**「目录顺序永远不能决定用哪个操作或 schema」**——这句在防一个具体而隐蔽的 bug 类。

`src/contracts/` 70 个文件、10,110 行，就是在保证这件事。

## 生活比喻：点名，不是数座位

老师点名：

| 方式 | 换座位之后 |
|------|-----------|
| 「第 5 排第 3 个」 | ❌ **叫到别人头上** |
| 「张小明」 | ✅ 还在 |

**按位置认人，位置一变就认错。**

代码里的对应物：**如果 handler 和 schema 靠「数组下标」对齐，那么任何一次重排都会静默错绑**——第 i 个 handler 拿到第 j 个操作的 schema。

**而「静默」是关键词**：程序不会崩，它会用一个错误的 schema 去校验一个正确的数据，**然后返回一个看起来正常的错误结果**。

## 一个完整契约长什么样

契约不是单一形态，是**三层合一**：

```typescript
// src/contracts/toolContractTypes.ts:42-61（节选）
/** Single source of truth for a public MCP tool. */
export interface ToolContract<
  Name extends string = string,
  InputSchema extends z.ZodType<Readonly<Record<string, unknown>>> = ...,
  OutputSchema extends z.ZodType<Readonly<Record<string, unknown>>> = ...,
> {
  readonly name: Name;
  readonly title: string;
  readonly description: string;
  readonly kind: ToolKind;
  readonly inputSchema: InputSchema;      // ← zod，canonical 源
  readonly outputSchema: OutputSchema;    // ← zod，canonical 源
  readonly effects: ToolEffects;
  readonly annotations: ToolAnnotations;
  readonly examples: readonly ToolExample[];
}
```

**注意 `name: Name` 是泛型参数。**

这行看起来只是类型体操，**实际上它是那句约束的类型层实现**——见下文。

一个实际的契约：

```typescript
// src/contracts/apktool/apktoolToolContracts.ts:10-42（节选）
export const APKTOOL_TOOL_CONTRACTS = [
  {
    name: "inspect_apktool_client",
    ...toolContractMetadata("inspect_apktool_client"),
    kind: "apktool-provider",
    inputSchema: apktoolInputSchemas.inspect_apktool_client,
    outputSchema: evidenceResultOf(apktoolResultSchemas.inspect_apktool_client),
    examples: [{ title: "Check the Apktool launcher", input: {} }],
  },
] as const satisfies readonly ToolContract[];
```

**三个细节**：

**① `...toolContractMetadata(name)` 展开 effects 和 annotations**

```typescript
// src/contracts/toolEffects.ts:566-577（概述）
const toolContractMetadata = (name) => {
  const audited = TOOL_EFFECTS[name];
  if (audited === undefined) throw new Error(`Missing effect audit for ${name}`);
  // ...
};
```

**缺审计项就抛错。** 172 个工具的 effects 集中在一张表里（`toolEffects.ts:55-540`），**新增工具忘了登记 = 模块加载失败。**

**② `evidenceResultOf(...)` 包装输出**

```typescript
// src/contracts/toolOutputSchemaPrimitives.ts:29
export const evidenceResultOf = <Schema extends z.ZodType>(schema: Schema) => ...
```

**所有工具的输出都被包成「Evidence 结果」**——这是[第 5 篇](05-evidence-model.md)证据模型在契约层的体现。

**③ `as const satisfies readonly ToolContract[]`**

**`as const` 保留字面量类型**（`name` 是 `"inspect_apktool_client"` 而不是 `string`），**`satisfies` 强制结构检查**。

**第 4 篇那个穷尽表的同一个手法**——保留字面量 + 强制完整。

## 「顺序不能决定语义」具体防什么

`src/contracts/toolContracts.ts:54-70`：

```typescript
/** Resolve a public contract by name while retaining its exact schema types. */
export const toolContract = <Name extends (typeof TOOL_CONTRACTS)[number]["name"]>(name: Name) =>
  Extract<(typeof TOOL_CONTRACTS)[number], { readonly name: Name }> => {
  const contract = TOOL_CONTRACTS.find((candidate): ... => candidate.name === name);
  if (contract === undefined) throw new Error(`Missing tool contract: ${name}`);
  // ...
};
```

**这个函数的返回类型是 `Extract<..., { name: Name }>`——把该契约的 input/output schema 类型窄化到具体类型。**

**于是「契约名 ∈ 服务的操作联合类型」成了编译期约束。**

### 全链路按名字寻址

| 环节 | 用什么找 | 源码 |
|------|---------|------|
| 解析契约 | `find(c => c.name === name)` | `toolContracts.ts:54-70` |
| 注册 | 显式列举名字 | `registerApktoolTools.ts:25-33` |
| 执行 | `contract.name` 读出来 | `contractToolHandler.ts:36-43` |
| 生成目录 | `new Map(tools.map(t => [t.name, t]))` | `generate-mcp-tool-catalog.mjs:83` |
| doctor 比对 | `Set(expectedNames)` vs `Set(observedNames)` | `mcpDoctor.ts:250-267` |
| 摘要计算 | **先按码点排序** | `catalogIdentity.ts:11-13` |

**六处，没有一处用到「第几个」。**

### 连摘要都先排序

```typescript
// src/catalogIdentity.ts:11-13
const sortedToolContracts = [...TOOL_CONTRACTS].sort((left, right) =>
  compareUnicodeCodePoints(left.name, right.name),
);
```

**目录摘要要先按 Unicode 码点排序再算。**

**否则重排一下目录顺序，摘要就变了**——而摘要是用来校验「客户端看到的目录和预期一致」的。

**用了第 2 篇那个手写的码点比较器**（locale 无关、可复现）。

### 最有力的证据：有一个测试把顺序反过来跑

```javascript
// tests/fixtures/contractPresentation.mjs:12-22
// Mutate only this child's presentation arrays, before importing registration.
if (process.argv[2] === "reversed") {
  for (const contracts of [
    BROWSER_TOOL_CONTRACTS,
    BROWSER_SCENARIO_TOOL_CONTRACTS,
    ELECTRON_TOOL_CONTRACTS,
    JAVASCRIPT_RUNTIME_OBSERVATION_TOOL_CONTRACTS,
    TOOL_CONTRACTS,
  ])
    contracts.reverse();
}
```

配套的断言（`tests/boundary/mcp/contractPresentation.test.ts:28`）：

```typescript
it("preserves advertised schemas and handler meaning when presentation order changes", ...)
```

**它做三件事**：

1. 按名字做 Set 相等
2. 按名字 find 比对 schema
3. **断言 handler 语义没错位**——错误响应里 `error.details.operation` 必须等于实际调用的名字

**第 3 条是关键**：它不只验证「schema 没变」，还验证「**执行到的是这个名字对应的操作**」。

**如果代码里有任何一处按下标对齐，这个测试就会红。**

**「我们把顺序反转一遍，结果必须完全一样」——这是那句约束最直接的机器化表达。**

## 优秀代码一：通过真实 SDK 往返生成目录

### 源码

```javascript
// scripts/generate-mcp-tool-catalog.mjs:65-87
async function sdkToolCatalog() {
  const server = new McpServer({ name: "rea-catalog-generator", version: "0" });
  for (const contract of TOOL_CONTRACTS)
    server.registerTool(
      contract.name,
      toolRegistrationOptions(contract),
      async () => ({ content: [{ type: "text", text: "Catalog-only handler" }], isError: true }),
    );
  const client = new Client({ name: "rea-catalog-generator", version: "0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  try {
    await server.connect(serverTransport);
    await client.connect(clientTransport);
    const { tools } = await client.listTools();
    return new Map(tools.map((tool) => [tool.name, tool]));
  } finally {
    await Promise.allSettled([client.close(), server.close()]);
  }
}
```

### 好在哪

**它生成的不是「源码里的 schema」，是「客户端实际收到的 schema」。**

这两者**不一样**——zod → JSON Schema 的转换发生在 **SDK 内部**，而且在 `tools/list` 时还会做一层「广告层」加工：

| 加工 | 在哪 |
|------|------|
| 加 `libraryOptions: { reused: "ref" }` 共享定义 | `toolSchemaMetadata.ts:56-73` |
| 注入 examples 和属性描述 | 同上 |
| 输出加**内容绑定 `$id`**（schema 变则身份变） | `toolSchemaMetadata.ts:87-96` |
| Moonshot 的 compact 改写 | `mcpInputSchemaPresentation` |

**不往返一次，这些全都捕获不到。**

**而「客户端实际收到什么」才是真问题**——因为 agent 是按那个来调用的。

### 用一个假 client 走真协议

```typescript
const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
```

**`InMemoryTransport`——零成本的真实 SDK 往返。**

不需要端口、不需要进程、不需要序列化到字节。**但它走的是真实的 SDK 代码路径。**

**handler 是占位的**（`text: "Catalog-only handler"`, `isError: true`）——**因为这一趟只关心 schema 长什么样，不关心工具做什么。**

### 生成完还要用 Ajv 验一遍

```javascript
// scripts/generate-mcp-tool-catalog.mjs:28-38
const advertisedTools = await sdkToolCatalog();
const ajv = new Ajv2020({ strict: false, validateFormats: false });
for (const tool of advertisedTools.values()) {
  for (const kind of ["inputSchema", "outputSchema"]) {
    const schema = tool[kind];
    if (schema !== undefined && !ajv.validateSchema(schema))
      throw new Error(`Invalid JSON Schema for ${tool.name}.${kind}: ${ajv.errorsText(ajv.errors)}`);
```

**「SDK 转换之后的 schema 是不是一份合法的 JSON Schema」——用第三方验证器独立验一遍。**

**因为 SDK 的转换可能产出合法但不符合声明的 JSON Schema 方言的东西。**

### 还有「双校验一致性」测试

```typescript
// tests/boundary/mcp/toolSchemaValidity.test.ts:59-61
const malformed = { ...example.input, __unexpected_root_key__: true };
expect(contract.inputSchema.safeParse(malformed).success, name).toBe(false);
expect(ajv.compile(tool.inputSchema)(malformed), name).toBe(false);
```

**同一个非法输入，zod 和转换后的 JSON Schema 必须都拒绝。**

**为什么？**

因为**运行时校验用 zod，客户端预校验用 JSON Schema**。

**如果两者不一致**，会出现：客户端认为合法的请求，服务端拒绝——**或者更糟：客户端认为非法而拒绝的请求，服务端其实会接受。**

**第二条意味着有人可以绕过客户端的预检。**

### 模式

**在真实边界上做 golden 捕获（conformance by reflection）**——用真实的协议往返产出可 diff、可 `--check` 的证据文件。

### 骨架代码

```javascript
// 你的项目中：任何「框架转换之后形态会变」的产物
async function captureAdvertisedSurface() {
  const server = new Framework.Server({ name: "catalog-generator", version: "0" });
  for (const contract of CONTRACTS)
    server.register(contract.name, toRegistration(contract), placeholderHandler);

  const client = new Framework.Client({ name: "catalog-generator", version: "0" });
  const [ct, st] = Framework.InMemoryTransport.createLinkedPair();
  try {
    await server.connect(st); await client.connect(ct);
    const { tools } = await client.listTools();        // ← 走真实转换路径
    return new Map(tools.map((t) => [t.name, t]));
  } finally {
    await Promise.allSettled([client.close(), server.close()]);
  }
}
// 再用独立验证器验一遍 + ensureGeneratedFile({ check: true }) 做新鲜度门禁
```

**判断标准**：**只要你的产物经过了框架的转换（ORM 生成 SQL、IDL 生成代码、schema 生成校验器），就该在真实的转换路径上捕获一次结果，而不是自己推演转换结果。**

**你推演的转换，和框架实际的转换，迟早会分叉。**

## 优秀代码二：契约实例即能力令牌

### 源码

```typescript
// src/server/contractToolHandler.ts:28-43
export const createContractToolHandler =
  <TOperation extends string>(server, service, logger, recordEvidence?, withAdmittedAnalysis?) =>
  (contract: ToolContract<TOperation>) =>
    createEvidenceToolHandler(
      server,
      (input, options) => service.execute(contract.name, input, options),
      logger, recordEvidence, withAdmittedAnalysis,
    )(contract);
```

调用点：

```typescript
// src/server/registerApktoolTools.ts:25-33
const handler = createContractToolHandler(server, service, logger, recordEvidence, withAdmittedAnalysis);
for (const contract of [
  toolContract("inspect_apktool_client"),
  toolContract("decode_android_resources"),
] as const) {
  server.registerTool(
    contract.name,
    toolRegistrationOptions(contract),
    handler(contract),
  );
}
```

### 好在哪

**这是「按名字寻址」在类型层面的完成形态。**

**① 操作名不是重复写的字符串，是从契约值里读出来的。**

```typescript
service.execute(contract.name, input, options)
```

**对比一下常见的写法**：

```typescript
// ❌ 常见写法：名字写两遍，写错不会有编译错误
server.registerTool("inspect_apktool_client", opts, (i) => service.execute("inspect_apktool_client", i));
```

**REA 的写法里，`"inspect_apktool_client"` 只出现在一处**——`toolContract("inspect_apktool_client")`。**其余全部从 `contract.name` 取。**

**② `ToolContract<TOperation>` 把契约名和服务操作联合类型焊死。**

```typescript
export interface ContractToolService<TOperation extends string> {
  execute(operation: TOperation, input: unknown, options?: ExecutionOptions):
    Promise<Result<Evidence, AnalysisError>>;
}
```

而 `ApktoolOperation = keyof typeof apktoolInputSchemas`（`apktoolResourceAnalysis.ts:38`）。

**契约名写错、或者服务不支持某个操作 = 编译错误。**

**③ 闭包捕获的就是那个契约对象本身。**

```typescript
handler(contract)
```

**注册、执行、结果投递三处共用同一个值——没有可漂移的二次查表。**

**「通过位置对齐」在结构上不可能发生**，因为没有任何地方有位置。

### 模式

**契约实例即能力令牌（capability token by value）**——柯里化 + 幻影类型参数把 `name` ↔ `schema` ↔ `operation` 三者焊死。

### 骨架代码

```typescript
// 1) 按名取契约，保留精确类型
const contract = <N extends ContractName>(name: N): Extract<Contract, { name: N }> => {
  const found = CONTRACTS.find((c) => c.name === name);
  if (!found) throw new Error(`Missing contract: ${name}`);
  return found as Extract<Contract, { name: N }>;
};

// 2) 工厂柯里化：契约进，绑好的 handler 出
const makeHandler = <Op extends string>(service: Service<Op>) =>
  (c: Contract<Op>) =>
    wrap(c, (input) => service.execute(c.name, input));   // ← 名字从契约读

// 3) 注册处不出现第二次名字
for (const c of [contract("a"), contract("b")] as const)
  register(c.name, optionsOf(c), makeHandler(service)(c));
```

**判断标准**：**数一数你的代码里，同一个操作名／路由名／命令名出现了几次。** 超过一次的地方，就是一次「改了这处忘了那处」的机会。

## 一个副产品：为特定客户端裁剪 schema

REA 支持一个 `compact` 输入 schema profile，**专门给 Moonshot/Kimi 用**：

```typescript
// src/config/mcpInputSchemaProfile.ts:5-11（注释原文）
// Moonshot's function-calling API rejects requests while any single tool
// parameters schema exceeds its literal serialized size cap.
// ... 13 KiB leaves margin
export const COMPACT_INPUT_SCHEMA_BUDGET_BYTES = 13 * 1024;
```

**「只要有任何一个工具的 parameters schema 超过它的序列化大小上限，Moonshot 就拒绝整个请求。」**

于是 REA 把输入 schema **压扁**到 13 KiB 以内。

**关键是：只改「广告形态」，不改工具集，也不改校验。**

`docs/mcp-contracts.md:61`：

> The compact profile renders **the same tool set, output schemas, annotations, and canonical server-side validation**. It **changes only the advertised input JSON Schema**.

**中文**：compact profile 渲染**相同的工具集、输出 schema、注解和服务端 canonical 校验**。**它只改变对外广告的输入 JSON Schema。**

**也就是说：运行时校验还是原来那份 zod。**

**如果 compact 改写让「客户端认为合法、服务端认为非法」，那就出问题了**——所以有专门的测试（`compactInputSchemaMcp.test.ts:102-118`）：

```typescript
it("keeps compact schemas valid and accepting canonical examples", ...)
// ajv.validateSchema(tool.inputSchema) + 每个 canonical example 仍被接受
```

**而文档还诚实地写了这条的验证边界**（`docs/mcp-contracts.md:89`）：

> the actual Kimi Code CLI; **local captures do not establish Moonshot acceptance**
>
> **本地捕获不构成「Moonshot 会接受」的证据。**

**又是一次「明确说出我验证到了哪一步」。**

## 代价

### ① 三层形态之间要保持同步

| 层 | 形态 | 谁消费 |
|----|------|--------|
| canonical | zod schema | **运行时校验** |
| advertised | SDK 转换后的 JSON Schema | 客户端预校验 |
| compact | 进一步压缩的广告形态 | 特定客户端 |

**三层必须语义一致。** 代码用「双校验一致性测试」和「compact 也过 canonical examples」来保证——**但这是持续的约束，不是一次性的。**

### ② 172 个契约的样板

每个工具一个对象，带 name / description / inputSchema / outputSchema / examples。

**而 description 是硬编码的自然语言——effects 有审计表强制，描述没有。**

### ③ 生成物不提交，但必须可复现

`.cache/mcp-tool-catalog.json` 被 `.gitignore` 忽略。

**这意味着 CI 每次要现场生成，然后和实时注册的输出比对。** 生成慢，而且**生成环境和开发环境不一致时会出问题**（SDK 版本、Node 版本）。

### ④ 反转测试只覆盖已注册的契约

顺序反转测试有效，**但前提是测试把那份清单写全了**。

`contractPresentation.mjs:12-21` 里是**手工列举的数组列表**——**新增一个 contract 文件忘了加进去，那个文件就不受反转测试保护。**

**又是一处靠记性的地方**（和[第 6 篇](06-composition-root.md)那个 `MIGRATED_PROVIDER_ROOTS` 同类）。

## 总结

| 结论 | 说明 |
|------|------|
| **规模** | 70 文件 10,110 行；172 个工具契约 |
| **核心约束** | 目录顺序**永远不能**决定用哪个操作或 schema |
| **防什么** | 按下标对齐 → 重排后静默错绑（不崩，但用错 schema） |
| **实现方式** | 六处全按名字寻址；**连摘要都先按码点排序** |
| **类型层** | `toolContract<N>()` 返回 `Extract<..., {name: N}>`，schema 类型精确传递 |
| **最强证据** | 一个反转顺序重跑的测试，断言 schema 和 handler 语义都不变 |
| **目录是生成的** | 走**真实 SDK 往返**捕获「客户端实际收到什么」，再用 Ajv 独立验一遍 |
| **双校验一致** | 同一非法输入，zod 和转换后的 JSON Schema 必须都拒 |
| **契约即令牌** | 操作名只写一次，从 `contract.name` 读 |

**一句话**：这条约束防的 bug 有个特征——**它不会让程序崩溃，只会让程序用错的规则处理对的数据。**

而**「不崩溃」恰恰是它危险的原因**：一个崩溃会被立刻发现，一个用错 schema 校验通过的结果会一路走下去，最后出现在一份分析报告里。

**所以防线不能是「小心点」，必须是结构性的**——让「按下标对齐」在代码里根本写不出来（名字从契约值读），再配一个反转顺序的测试兜底。

而那句 `catalog ordering must never select an operation or schema` 之所以值得单独写进 AGENTS.md，是因为**它是一条「反直觉的架构约束」**：绝大多数列表处理代码天然是按下标写的，**而这里要求一处都不能有。**

---

**下一篇**：[Windows 原生扩展](13-windows-native.md)——全仓唯一的 C++，用 Job Object 把「事后证明」换成「事前归属」。
