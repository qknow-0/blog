# Node.js 最新版本实用特性盘点

> 本文基于 Node.js 24 LTS。

Node.js 近几年发版节奏加快，每个大版本都带着一批实用特性。很多以前要装 npm 包才能做的事，现在标准库直接提供。这篇文章挑最实用的几个讲。

## 1. 原生 .env 文件加载

以前最常用的 npm 包是 `dotenv`，周下载 4000 万次。现在不装了：

```js
// 命令行方式
node --env-file=.env app.js

// 代码方式
import { loadEnvFile } from 'node:process';
loadEnvFile('.env');
loadEnvFile('.env.local');  // 可加载多个，后者覆盖前者
```

```env
# .env
DATABASE_URL=postgres://localhost/mydb
API_KEY=sk-xxx
```

```js
// 直接读
console.log(process.env.DATABASE_URL);
// postgres://localhost/mydb
```

不需要 `require('dotenv').config()` 了。24 版本起稳定可用。

## 2. 原生 TypeScript 支持

24 版本起，直接跑 `.ts` 文件：

```bash
node --experimental-strip-types app.ts
```

它的原理是**只做类型擦除，不做类型检查**。把 `: string`、`interface`、`type` 这些去掉，剩下的 JavaScript 交给引擎跑。编译极快——比 ts-node 快 5-10 倍。

```ts
// app.ts
function greet(name: string): string {
    return `Hello, ${name}`;
}
console.log(greet("World"));
```

```bash
node --experimental-strip-types app.ts
# Hello, World
```

类型检查仍交给 `tsc --noEmit` 或编辑器。Node.js 只管跑，tsc 只管检查，职责分开。

## 3. 原生 WebSocket 客户端

以前装 `ws` 或 `socket.io`，现在标准库自带：

```js
import { WebSocket } from 'node:websocket';

const ws = new WebSocket('wss://echo.websocket.org');

ws.onopen = () => {
    ws.send('hello');
};

ws.onmessage = (event) => {
    console.log('收到:', event.data);
};

ws.onerror = (err) => {
    console.error('WebSocket 错误:', err);
};
```

API 和浏览器端的 `WebSocket` 完全一致——同一套代码跑在浏览器和 Node.js 里，零差异。24 版本 `node:websocket` 已是稳定模块。

## 4. 内置 watch 模式

不需要 `nodemon` 了：

```bash
node --watch app.js
```

改代码保存，自动重启。支持递归监听 `node_modules` 以外的所有目录。

```bash
# 只监听特定目录
node --watch-path=src --watch-path=config app.js
```

23 版本起稳定。

## 5. 权限模型

这是安全方面的大改进。限制某个脚本能访问什么：

```bash
# 禁止文件写入
node --experimental-permission \
  --allow-fs-read=/app/* \
  app.js
```

```js
// 代码里也可以检查
import { permission } from 'node:process';

if (permission.has('fs.write')) {
    // 有权限
}
```

权限粒度到文件路径级别。第三方依赖的脚本跑在受限环境下——即使被恶意代码尝试读 `/etc/passwd`，Node.js 进程层就拦了。

24 版本仍在实验阶段，生产环境建议等稳定。

## 6. 内置测试运行器

Jest/Vitest 不是必需品了。标准库自带 `node:test`：

```js
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('用户服务', () => {
    test('创建用户返回有效 ID', async () => {
        const user = await createUser({ name: 'Alice' });
        assert.ok(user.id);
        assert.strictEqual(user.name, 'Alice');
    });

    test('邮箱格式无效抛出错误', async () => {
        await assert.rejects(
            () => createUser({ name: 'Bob', email: 'invalid' }),
            { message: /邮箱格式/ }
        );
    });
});
```

```bash
node --test
# 或者指定文件
node --test tests/*.test.js
```

支持 `describe`、`beforeEach`、`mock`、覆盖率输出。API 和 Jest/Vitest 很像，迁移成本低。22 版本起稳定。

## 以前 vs 现在

| 需求 | 以前 | 现在（24） |
|------|------|------|
| 加载 .env | `npm i dotenv` | `--env-file` 或 `loadEnvFile()` |
| 跑 TS | `npx ts-node` | `--experimental-strip-types` |
| WebSocket 客户端 | `npm i ws` | `node:websocket` |
| 文件变化自动重启 | `npm i -g nodemon` | `--watch` |
| 测试框架 | `npm i jest` | `node:test` |
| 运行权限控制 | 无 | `--experimental-permission` |

六个 npm 包被标准库替代。不是说 npm 包不好——它们在 Node.js 内置之前填补了空白。但现在能少一个依赖就少一个：安全面小了、安装快了、升级不同步的风险也没了。

> 参考：[Node.js 24 发布公告](https://nodejs.org/en/blog/release/v24.0.0) · [Node.js 文档](https://nodejs.org/docs/latest/)
