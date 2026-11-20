# TypeScript / Node 项目结构：src 是源码，exports 才是门

> 本文基于 Node.js 22.22.2、npm 10.9.7、TypeScript 7.0.2；示例在 macOS arm64 上实际运行。
> 系列：各语言项目结构最佳实践（TypeScript / Node 分册）。

## 目录

- [先给结论](#先给结论)
- [生活比喻：前店后厂](#生活比喻前店后厂)
- [三个概念：包、源码、产物](#三个概念包源码产物)
- [单包项目：src/ + dist/ + package.json](#单包项目src-dist-packagejson)
- [tsconfig：编译范围不是包边界](#tsconfig编译范围不是包边界)
- [exports：真正的门](#exports真正的门)
- [库、应用、CLI 分别怎么放](#库应用cli-分别怎么放)
- [monorepo：apps/ + packages/](#monorepoapps-packages)
- [feature 还是 layer](#feature-还是-layer)
- [真实仓库之一：zod 的 packages 与子路径导出](#真实仓库之一zod-的-packages-与子路径导出)
- [真实仓库之二：shadcn/ui 的 apps + packages](#真实仓库之二shadcnui-的-apps-packages)
- [对照：Express 的 lib/ + index.js](#对照express-的-lib-indexjs)
- [关键争议速查](#关键争议速查)
- [反模式](#反模式)
- [决策清单](#决策清单)
- [骨架代码与验证](#骨架代码与验证)
- [结语](#结语)
- [参考资料](#参考资料)

## 先给结论

Node.js 和 TypeScript 都没有官方强制的项目布局。真正能约束你的，主要是两个边界：

1. **构建边界**：`src/` 是编译输入，`dist/` 是编译产物；`tsconfig.json` 决定哪些文件参与编译。
2. **包边界**：`package.json` 决定这个包怎么被安装、哪些文件会被发布、外部能 import 哪些子路径。

所以这一篇的主线是：

> **`src/` 只说明源码放哪；`exports` 才决定外部能从哪里进来。**

很多项目把 `src/` 整理得很漂亮，却让外部用户直接 import `package/src/internal/foo`。这种结构在仓库里看着整齐，在包边界上等于没有门。

## 生活比喻：前店后厂

把 npm 包想成一家前店后厂的店铺：

| 目录/文件 | 店铺里的角色 | 作用 |
|-----------|--------------|------|
| `src/` | 后厂 | 源码、半成品、内部工具 |
| `dist/` | 前店货架 | 编译后的 JS、类型声明、source map |
| `package.json` | 营业执照 + 上架清单 | 包名、版本、入口、依赖、发布文件 |
| `exports` | 正门和柜台目录 | 外部能从哪个子路径进来 |
| `files` | 打包清单 | 哪些东西能装进 tarball |
| `tsconfig.json` | 工厂生产范围 | 编译哪些文件、输出到哪 |
| `node_modules/` | 别人的仓库 | 依赖，不是你的源码 |

`src/` 里可以有后门、仓库、员工通道；但顾客只能走 `exports` 开的那扇门。**后厂再整洁，门没锁好，也不叫边界。**

## 三个概念：包、源码、产物

先分清三个经常被混用的东西：

| 概念 | 由什么定义 | 回答什么问题 |
|------|------------|--------------|
| **package** | `package.json` | 安装、发布、依赖的单元是什么？ |
| **source tree** | `src/` + `tsconfig.json` | 编译输入是什么？ |
| **build output** | `outDir`（通常 `dist/`） | 运行时实际加载什么？ |

一个 package 可以：

- 只有一个入口：`src/index.ts` → `dist/index.js`；
- 有多个入口：`src/index.ts`、`src/cli.ts`，通过 `exports` 暴露不同子路径；
- 有多个编译目标：ESM、CJS、类型声明，分别输出到不同目录或文件；
- 同时是库和 CLI：`src/index.ts` 给库用户，`src/cli.ts` 给命令行。

这些都不是靠目录名决定的，而是靠 `package.json` 的字段和构建配置决定的。

```mermaid
flowchart LR
    S["src/*.ts<br/>源码"] -->|"tsc / bundler"| D["dist/*.js + *.d.ts<br/>构建产物"]
    D --> P["package.json<br/>exports + files"]
    P --> C["消费者<br/>import 'shop'"]
    C -.->|"import 'shop/internal'"| X["ERR_PACKAGE_PATH_NOT_EXPORTED"]

    style S fill:#16213e,stroke:#e94560,color:#fff
    style D fill:#0f3460,stroke:#e94560,color:#fff
    style P fill:#533483,stroke:#e94560,color:#fff
    style C fill:#1a2e1b,stroke:#53d769,color:#fff
    style X fill:#3e1a1a,stroke:#e94560,color:#fff
```

### `main`、`module`、`types`、`exports`

老项目常见：

```json
{
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts"
}
```

新项目更推荐把入口集中到 `exports`：

```json
{
  "type": "module",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    }
  }
}
```

几个关键点：

- `exports` 是**包级别**的子路径映射，优先级高于 `main`/`module` 这类 legacy 字段；
- `types` 条件要放在前面，TypeScript 才能正确解析类型；
- `import` / `require` 条件用于区分 ESM 和 CJS；
- `exports` 只限制“通过包名 import”的路径，不限制包内部用相对路径互相 import；
- `files` 决定 tarball 里有什么；`exports` 决定外部能 import 什么。两者不是一回事。

**发布前至少跑一次 `npm pack --dry-run`。** 它会告诉你用户实际会拿到什么，比看 `.gitignore` 靠谱。

## 单包项目：src/ + dist/ + package.json

一个最小的 TypeScript 库：

```text
shop/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── pricing.ts
│   └── internal.ts
├── tests/
│   └── pricing.test.ts
└── dist/                 # 构建生成，不提交
```

```text
src/index.ts       公开入口：export { total } from "./pricing.js"
src/pricing.ts     业务实现
src/internal.ts    内部实现，不从 index.ts 导出
```

对应的 `package.json`：

```json
{
  "type": "module",
  "exports": { ".": "./dist/index.js" },
  "files": ["dist"]
}
```

完整字段见后面的骨架代码。这个结构里有三条边界：

1. **源码边界**：`src/` 是输入，`dist/` 是输出；不要手改 `dist/`，也不要提交它。
2. **公共 API 边界**：`src/index.ts` 是公开入口；`internal.ts` 不导出，外部不应该依赖。
3. **发布边界**：`files: ["dist"]` 让 tarball 只包含构建产物和 `package.json`，不把 `tests/`、`src/` 一起发出去。

**不要因为“库用 src”就给所有项目加 `src/`。** 一个只部署到 Docker 的服务，`app/` 或根目录扁平结构完全可以；关键是它的部署产物是不是一个明确的镜像/构建输出。库、应用、CLI 的差异后面单独讲。

## tsconfig：编译范围不是包边界

示例 `tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": "src",
    "outDir": "dist",
    "declaration": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

逐项看：

| 配置 | 作用 | 常见坑 |
|------|------|--------|
| `rootDir` | 源码根目录 | 和 `outDir` 混用会让输出多一层 `src/` |
| `outDir` | 编译输出目录 | 不写可能把 `.js` 生成到源码旁边 |
| `module` / `moduleResolution` | 模块解析规则 | `NodeNext` 下相对 import 要写 `.js` 扩展名 |
| `declaration` | 生成 `.d.ts` | 库必须开；否则类型用户没法用 |
| `include` / `exclude` | 参与编译的文件 | 把测试文件编进 `dist` 是最常见的污染 |
| `paths` | 编译期路径别名 | 运行时不一定认识；跨包不要靠它 |

### `NodeNext` 和 `.js` 扩展名

在 `NodeNext` 模式下，TypeScript 会按照 Node 的 ESM 规则解析模块。源码里写：

```ts
export { total } from "./pricing.js";
```

虽然当前文件叫 `pricing.ts`，但 import 要写 `pricing.js`——因为编译后运行时看到的是 `.js`。这不是笔误，是 Node ESM 的规则。

如果你的项目用 bundler（Vite、Next.js、webpack），通常用 `moduleResolution: "Bundler"`，就不需要写 `.js` 扩展名。**选哪种，取决于运行时和构建工具，不是个人偏好。**

### `paths` 别名不是包边界

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

`paths` 只影响 TypeScript 的类型解析和编译；运行时（Node、bundler、测试工具）未必认识它。跨包引用时，别名还会绕过 `exports` 和构建产物，制造“仓库里能跑、发布后挂掉”的问题。

**跨包引用用 workspace 包名和 `exports`，不要用 `../../packages/ui/src/...`。**

## exports：真正的门

`exports` 是 Node.js 的包入口映射。它不只决定“主入口是哪个文件”，还决定**哪些子路径可以被外部 import**。

### 一个入口

```json
{
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    }
  }
}
```

外部只能：

```ts
import { total } from "shop";
```

不能：

```ts
import { internal } from "shop/internal";
```

即使 `dist/internal.js` 确实存在于 tarball 里，`exports` 没有声明 `./internal`，Node 也会拒绝。

### 多个子路径

```json
{
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    },
    "./mini": {
      "types": "./dist/mini/index.d.ts",
      "import": "./dist/mini/index.js"
    }
  }
}
```

这就允许：

```ts
import { z } from "shop";
import { mini } from "shop/mini";
```

**`exports` 是公共 API 的一部分。** 加一个子路径，等于承诺维护它；删一个子路径，就是 breaking change。

### 一个容易误解的点

`exports` 不是沙箱。它只约束“通过包名 import”的解析：

- 包内部用相对路径 `./internal.js` 仍然能访问任何文件；
- 用户如果拿到文件路径（比如 monorepo 里直接指向 `src`），也可能绕过；
- 真正的隔离还需要 `files`、构建配置、workspace 依赖规则一起配合。

但对正常的 npm 消费者，`exports` 就是那扇门。**门后面的文件在不在 tarball 里，和门开不开，是两件事。**

## 库、应用、CLI 分别怎么放

### 库

```text
packages/ui/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── button.tsx
│   └── internal/
└── tests/
```

- `src/index.ts` 是公共 API；
- `exports` 声明公开子路径；
- `files` 只发布 `dist`；
- `peerDependencies` 放 React 这类由宿主提供的依赖，避免重复安装；
- 测试可以放 `tests/`，也可以和源码同目录，但不要编进 `dist`。

### Web 应用

```text
web/
├── package.json
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── app/
│   ├── features/
│   └── shared/
└── public/
```

应用通常不需要 `exports`，因为它不是给别人 import 的包；它的交付物是镜像或平台构建产物。此时结构主要服务于**路由、功能和团队导航**。

### CLI

```json
{
  "bin": {
    "shop": "./dist/cli.js"
  }
}
```

```ts
#!/usr/bin/env node
// src/cli.ts
import { total } from "./pricing.js";

console.log(total(1250, 3));
```

CLI 的入口是 `bin`，不是 `exports`。如果它同时是库，再给库入口加 `exports`；两个入口分开，不要混在一个文件里。

### 框架优先

- **Next.js App Router**：`app/` 目录就是路由，`app/orders/[id]/page.tsx` 对应 URL；路由私有组件可以放在路由目录旁边的 `_components/`，共享组件放 `components/`，工具放 `lib/`。不要为了“领域驱动”把 `app/` 改成完全自定义的结构——Next.js 的路由发现依赖它。
- **NestJS**：`src/orders/orders.module.ts`、`orders.controller.ts`、`orders.service.ts` 是框架约定的 feature 结构；模块边界同时承担依赖注入边界。
- **Express**：框架不规定结构，所以你才需要自己决定 feature 还是 layer；这也是下面要讨论的。

## monorepo：apps/ + packages/

当仓库里有多个**可独立部署或发布**的产物时，monorepo 才开始划算：

```text
repo/
├── package.json          # private，workspaces
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.base.json
├── apps/
│   ├── web/              # 部署到 Vercel/容器
│   └── admin/            # 另一个部署单元
└── packages/
    ├── ui/               # 共享组件库
    ├── config/           # 共享 ESLint/TS 配置
    └── db/               # 共享数据库访问
```

两个目录的职责：

| 目录 | 放什么 | 判断标准 |
|------|--------|----------|
| `apps/` | 最终部署的应用、服务、CLI | 有独立启动/部署方式 |
| `packages/` | 可复用的库、配置、设计系统 | 被多个 app import，或独立发布 |

monorepo 的几条硬规则：

1. **包之间用包名引用**，不要用 `../../packages/ui/src/button`；后者绕过 `exports` 和构建。
2. **每个包有自己的 `package.json`、`tsconfig.json`、`exports`**；根目录只放共享配置和任务编排。
3. **根 lockfile 只有一份**；依赖版本尽量统一，避免同一个 React 装出两份。
4. **共享包用 `peerDependencies` 声明宿主依赖**（React、Vue 等），否则容易出现多实例。
5. **`turbo.json` / Nx 只负责任务编排**，不负责模块边界；边界还是靠 workspace + `exports`。

什么时候不该 monorepo？

- 只有一个应用、一个团队、一个部署单元：单包更简单；
- 包之间没有真正复用，只是“看起来应该拆”：先别拆；
- 拆完之后每个 PR 都要改 5 个包：说明边界切错了。

## feature 还是 layer

后端常见两种：

```text
# layer-first
src/
├── controllers/
├── services/
├── repositories/
└── models/
```

```text
# feature-first
src/
├── orders/
│   ├── order.controller.ts
│   ├── order.service.ts
│   ├── order.repository.ts
│   └── order.schema.ts
└── billing/
    ├── invoice.controller.ts
    └── invoice.service.ts
```

前端也类似：

```text
# layer-first
src/
├── components/
├── hooks/
└── utils/
```

```text
# feature-first
src/
├── features/
│   ├── orders/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api.ts
│   └── billing/
└── shared/
    ├── ui/
    └── lib/
```

判断标准不是“哪个更高级”，而是：

> **一次业务改动，通常要打开几个目录？**

- 小 CRUD、框架脚手架：layer-first 更直观；
- 业务复杂、多人协作：feature-first 减少跨目录跳转；
- 设计系统/基础组件：按 `shared/ui` 或独立 package，不要塞进某个 feature。

**不要把所有东西都放进 `shared/`。** 共享是有成本的：它把多个 feature 绑在一起。只有当两个以上 feature 真的需要同一份实现时，才提升为 shared。

## 真实仓库之一：zod 的 packages 与子路径导出

[zod](https://github.com/colinhacks/zod) 是一个 TypeScript 运行时校验库。它的仓库顶层是：

```text
zod/
├── package.json
├── pnpm-lock.yaml
├── packages/
│   ├── zod/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vitest.config.ts
│   │   └── src/
│   │       ├── index.ts
│   │       ├── v3/
│   │       ├── v4/
│   │       ├── mini/
│   │       └── locales/
│   ├── mini/
│   ├── bench/
│   ├── docs/
│   └── tsc/
```

（只列部分；main 分支，2026-11-18 快照，commit `e32e08836e45`。）

它的核心包 `packages/zod` 的 `package.json` 用 `exports` 暴露多个子路径，例如：

```json
{
  "exports": {
    ".": { "types": "./index.d.ts", "import": "./index.js", "require": "./index.cjs" },
    "./mini": { "...": "..." },
    "./v3": { "...": "..." },
    "./v4": { "...": "..." },
    "./v4/mini": { "...": "..." }
  }
}
```

（为便于阅读省略了条件的完整内容。）

值得学的点：

1. **`packages/zod` 是一个完整的包边界。** 它有自己的 `package.json`、`tsconfig`、测试配置和 `src/`；仓库根目录不替它决定内部结构。
2. **`src/` 里的版本目录不自动等于公共 API。** 外部用户看到的是 `zod/v4`、`zod/mini` 这些 `exports` 子路径；`src/v4/...` 是内部路径。
3. **子路径导出是兼容性承诺。** `zod/v3` 和 `zod/v4` 并存，是显式的版本策略，不是把源码目录直接暴露给用户。

**结论：库的公共结构写在 `exports` 里，不写在 `src/` 的目录名里。**

## 真实仓库之二：shadcn/ui 的 apps + packages

[shadcn/ui](https://github.com/shadcn-ui/ui) 是一个 TypeScript monorepo：

```text
ui/
├── package.json
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.json
├── apps/
│   └── v4/                 # 文档/展示站点，可独立部署
├── packages/
│   ├── shadcn/             # CLI
│   ├── react/              # 组件实现
│   ├── registry/           # 组件注册表
│   ├── helpers/
│   └── tests/
├── templates/
└── scripts/
```

（只列部分；main 分支，2026-11-19 快照，commit `f50887ae68d0`。）

`pnpm-workspace.yaml` 的声明很直接：

```yaml
packages:
  - "apps/*"
  - "packages/*"
  - "!**/test/**"
  - "!**/fixtures/**"
  - "!**/temp/**"
```

值得学的点：

1. **`apps/` 和 `packages/` 的分工是部署/发布边界。** `apps/v4` 是可部署站点；`packages/shadcn` 是可发布的 CLI；`packages/react` 是共享组件实现。
2. **`packages/tests` 是独立的测试包。** 测试不硬塞进某个产品包，避免测试依赖进入运行时依赖。
3. **根目录只做编排。** `turbo.json`、`pnpm-workspace.yaml`、根 `tsconfig.json` 负责协调；每个包仍然有自己的 `package.json` 和 `tsconfig`。
4. **`templates/` 是脚手架产物，不是运行时包。** 它不被 workspace 当成普通包发布，但仍然在仓库里统一维护。

**结论：monorepo 不是“把代码放进 packages/”，而是“把独立发布/部署的单元放进 apps/ 或 packages/”。**

## 对照：Express 的 lib/ + index.js

[Express](https://github.com/expressjs/express) 是更老的 Node 项目（JavaScript，不是 TypeScript）：

```text
express/
├── package.json
├── index.js
├── lib/
├── test/
└── examples/
```

（master 分支，2026-11-19 快照。）

它没有 `src/`，入口是根目录的 `index.js`，实现放 `lib/`，测试放 `test/`。这是很多老 Node 包的习惯，不是“错误”。

**如果你在维护这类项目，不要为了统一而强行搬进 `src/`。** 迁移的成本包括：构建流程、发布入口、source map、测试路径、下游用户的 deep import。只有在确实需要 TypeScript、构建步骤或公共 API 重构时，才值得动。

## 关键争议速查

| 争议 | 我的建议 | 理由 |
|------|----------|------|
| 新项目要不要 `src/` | 库和需要构建的应用要；纯脚本可不要 | `src/` 让输入/输出分离，但小脚本不需要 |
| `exports` 还是 `main` | 优先 `exports`，保留 `main`/`types` 兼容老工具 | `exports` 能限制子路径，是现代入口 |
| 测试放 `tests/` 还是同目录 | 库放 `tests/`；应用可同目录 `*.test.ts` | 关键是别编进 `dist` |
| 要不要 monorepo | 有多个独立部署/发布单元时再上 | 单应用单团队用 monorepo 只增加协调成本 |
| feature 还是 layer | 小项目 layer；中大型 feature | 按“一次改动打开几个目录”判断 |
| `paths` 别名还是 workspace | 跨包用 workspace 包名；包内可用别名 | 别名是编译期的，运行时未必认 |
| ESM 还是 CJS | 新项目优先 ESM；需要兼容再 dual build | 双格式会增加 `exports` 条件和测试成本 |
| 要不要提交 `dist` | 不提交；CI 构建 | 提交产物会漂移、冲突、掩盖构建问题 |
| 要不要 barrel `index.ts` | 公共入口要；内部目录别到处建 | barrel 方便但容易造成循环依赖 |
| 库的 React 放哪 | `peerDependencies` | 避免宿主和库各装一份 React |

## 反模式

### 1. 应用直接 import 另一个包的 `src/`

```ts
import { Button } from "../../packages/ui/src/button";
```

这绕过了 `exports`、构建产物和版本边界。正确做法是通过 workspace 包名：

```ts
import { Button } from "@repo/ui";
```

### 2. 把 `dist` 提交进 Git

`dist/` 是构建产物。提交它会带来冲突、过期文件和“本地能跑、CI 构建失败”的假象。发布由 CI 构建，不靠提交产物。

### 3. 测试文件被编进 `dist`

```json
{
  "include": ["src", "tests"]
}
```

结果 tarball 里多出一堆测试代码。用独立的 `tsconfig.build.json`，或者让 `include` 只覆盖 `src`。

### 4. `paths` 别名跨包引用

```json
{
  "paths": {
    "@ui/*": ["../packages/ui/src/*"]
  }
}
```

TypeScript 能过，运行时可能找不到；即使打包器能处理，也绕过了包的 `exports` 和构建边界。跨包请用 workspace 包名。

### 5. 一个巨大的 `utils.ts` 或 `components/index.ts`

所有东西都从 `utils` 导出，最后任何模块都 import 它，循环依赖和打包体积一起上来。按用途拆模块，公共 API 只保留真正稳定的部分。

### 6. 多份 React / 多份核心依赖

monorepo 里如果每个包都 `dependencies: { "react": "^19" }`，可能装出两份 React，hooks 直接报错。UI 库应把 React 放 `peerDependencies`，由宿主应用提供。

### 7. `type: module` 和 CJS 配置混用

`package.json` 写了 `"type": "module"`，但 `tsconfig` 输出 CJS，或者 `require` 加载 ESM，运行时就会炸。先决定模块格式，再统一 `tsconfig`、`exports` 和测试配置。

### 8. 发布前不看 `npm pack --dry-run`

`files` 配错、`dist` 没构建、测试被带进 tarball，都能在发布前发现。`npm pack --dry-run` 是最便宜的发布检查。

## 决策清单

| 场景 | 推荐结构 | 关键动作 |
|------|----------|----------|
| 只给自己用的脚本 | 根目录单文件或扁平目录 | 不建 `src/`、不建 package |
| 要发布到 npm 的库 | `src/index.ts` + `dist/` + `exports` | `npm pack --dry-run` 检查 tarball |
| 内部共享库 | `packages/ui/` + `exports` | 用 workspace 包名引用，配置 `peerDependencies` |
| 单体 Web 应用 | `src/` 或框架 `app/` | Docker/平台构建产物是边界 |
| Next.js 应用 | `app/` + `components/` + `lib/` | 路由目录跟框架，不要硬改 |
| NestJS 应用 | `src/<feature>/<feature>.module.ts` | 用框架 module 表达 feature 边界 |
| 多应用 monorepo | `apps/` + `packages/` + workspace | 根 lockfile、共享配置、包名引用 |
| 库 + CLI | `src/index.ts` + `src/cli.ts` + `bin` | 两个入口分别验证 |

## 骨架代码与验证

下面是我实际跑过的单包 TypeScript demo。

### 目录树

```text
shop/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── internal.ts
│   └── pricing.ts
└── dist/                 # 构建生成
```

### `package.json`

```json
{
  "name": "shop",
  "version": "0.1.0",
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build": "tsc"
  },
  "devDependencies": {
    "typescript": "7.0.2"
  }
}
```

### `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": "src",
    "outDir": "dist",
    "declaration": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

### 源码

```ts
// src/index.ts
export { total } from "./pricing.js";
```

```ts
// src/pricing.ts
export function total(unitCents: number, quantity: number): number {
  if (unitCents < 0 || quantity < 0) {
    throw new Error("unit price and quantity must be non-negative");
  }
  return unitCents * quantity;
}
```

```ts
// src/internal.ts
export const internal = "not part of the public API";
```

### 构建与运行

```bash
$ npm install
added 2 packages in 6s

$ npm run build
> tsc

$ node --input-type=module -e "import { total } from './dist/index.js'; console.log(total(1250, 3))"
3750

$ npm pack --dry-run
npm notice Tarball Contents
npm notice 38B dist/index.d.ts
npm notice 38B dist/index.js
npm notice 62B dist/internal.d.ts
npm notice 54B dist/internal.js
npm notice 76B dist/pricing.d.ts
npm notice 200B dist/pricing.js
npm notice 353B package.json
npm notice total files: 7
```

注意：`dist/internal.js` 在 tarball 里，但 `exports` 没有开放 `./internal`。

### 在另一个包里验证入口

把 tarball 安装到消费者项目后：

```bash
$ node --input-type=module -e "import { total } from 'shop'; console.log(total(1250, 3))"
3750

$ node --input-type=module -e "import 'shop/internal'"
Error [ERR_PACKAGE_PATH_NOT_EXPORTED]: Package subpath './internal' is not defined by "exports" in .../node_modules/shop/package.json imported from .../[eval1]
    at exportsNotFound ...
    ...
Node.js v22.22.2
```

（输出有删节，错误前的路径做了简化。）

这就是 `exports` 的价值：**文件存在，不代表它是公共入口。** 公共入口是被显式声明的，删除或修改它就应该被当成 breaking change。

## 结语

TypeScript / Node 的项目结构，可以用三句话收束：

1. **`src/` 是后厂，`dist/` 是前店。** 不要把后厂当货架，也不要把货架当源码。
2. **`package.json` 是合同，`exports` 是门。** 外部能 import 什么，由合同决定，不由目录名决定。
3. **monorepo 只在有多个独立发布/部署单元时成立。** 否则只是把单包拆成很多包，增加协作成本。

下一篇看 Rust：一个把“包、crate、module、测试、示例、基准”都写进工具链的语言，为什么仍然需要判断什么时候拆 workspace。

## 参考资料

- [Node.js：Packages and exports](https://nodejs.org/api/packages.html)
- [TypeScript：tsconfig Reference](https://www.typescriptlang.org/tsconfig/)
- [TypeScript：Modules Reference](https://www.typescriptlang.org/docs/handbook/modules/reference.html)
- [npm：package.json](https://docs.npmjs.com/cli/v11/configuring-npm/package-json)
- [pnpm：Workspaces](https://pnpm.io/workspaces)
- [Turborepo 文档](https://turborepo.com/docs)
- [Next.js：Project Structure](https://nextjs.org/docs/app/getting-started/project-structure)
- [NestJS：Modules](https://docs.nestjs.com/modules)
- [zod 源码](https://github.com/colinhacks/zod)
- [shadcn/ui 源码](https://github.com/shadcn-ui/ui)
- [Express 源码](https://github.com/expressjs/express)
