# Node.js 错误处理：别让一个未捕获的异常崩了你的服务

> 一个 `throw` 没 catch，整个进程挂了。Node.js 的错误处理不是「多写几个 try-catch」的事——它需要从 Promise 链、EventEmitter、Stream 到进程边界四个层面都做对。

本文基于 Node.js v24。

## 错误处理的地图：你的防线在哪

把错误处理想象成一座城市的防洪系统：

```text
第一道防线：函数级别
  每个函数内部的 try-catch——就像每家每户门口的沙袋
  防小水，不防洪水

第二道防线：请求级别
  Express/Koa 的全局错误中间件——就像街道的排水沟
  一个请求内的错误在这里兜底

第三道防线：进程级别
  uncaughtException / unhandledRejection——就像城市的防洪堤
  防线前面的都没拦住，这里是最后的机会

第四道防线：进程外
  Docker restart policy / PM2 / K8s——就像救灾队
  堤坝也决了口，但城市会自动重建
```

防线逐层加深。**前一道防线能处理的，不要漏给后面**。

## 第一道防线：Promise 链

```javascript
// ❌ 一个未 catch 的 Promise rejection 会炸进程
app.get('/user/:id', async (req, res) => {
    const user = await db.query('SELECT * FROM users WHERE id = ?', req.params.id);
    // db.query 抛了异常 → 没人 catch → unhandledRejection → 💥
    res.json(user);
});

// ✅ 方案 1：每个 async 函数包 try-catch
app.get('/user/:id', async (req, res, next) => {
    try {
        const user = await db.query('SELECT * FROM users WHERE id = ?', req.params.id);
        res.json(user);
    } catch (err) {
        next(err);  // 交给 Express 全局错误中间件 —— 第二道防线
    }
});

// ✅ 方案 2：用 express-async-errors 自动包裹
// 不用每个路由写 try-catch，async 函数抛的异常自动传给 next(err)
require('express-async-errors');
app.get('/user/:id', async (req, res) => {
    const user = await db.query('...');
    res.json(user);  // 异常自动 → next(err)
});
```

对于 Express 项目，用 `express-async-errors` 一行省掉几百个 `try-catch`。就像在每家每户门口统一装了沙袋，不用住户自己扛。

## 第一道防线：不要把 Promise 和 callback 混用

```javascript
// ❌ 同一段代码里混用 callback 和 Promise——哪边出错都可能没处理
function readConfig(path, callback) {
    fs.readFile(path, (err, data) => {
        if (err) return callback(err);
        try {
            const config = JSON.parse(data);  // ← 这个异常 callback(err) 包不住！
            callback(null, config);
        } catch (e) {
            callback(e);
        }
    });
}
```

解法：选一边，不要两头靠。新代码全用 Promise/async-await，老 callback API 用 `util.promisify` 转：

```javascript
const readFile = require('util').promisify(fs.readFile);

async function readConfig(path) {
    const data = await readFile(path);
    return JSON.parse(data);  // 异常自然地沿 Promise 链传到调用者
}
```

## 第二道防线：EventEmitter 的 error 事件

EventEmitter 有一个致命陷阱——error 事件如果没有监听器，直接抛异常：

```javascript
const stream = fs.createReadStream('file.txt');

// ❌ 没有 error 监听器 → stream 出错 → uncaughtException → 💥
stream.on('data', (chunk) => { /* ... */ });

// ✅ 加了 error 监听器
stream.on('data', (chunk) => { /* ... */ });
stream.on('error', (err) => {  // 排水沟——水流到这就被引走了
    console.error('stream error', err);
});
```

**Stream 尤其是重灾区**。读文件、网络请求、数据库连接——只要涉及到 Stream，必须加 error 监听器。

## 第二道防线：Express 全局错误中间件

```javascript
// 正常路由 ──→ 全局错误中间件 ──→ 统一响应给客户端
app.get('/user/:id', async (req, res) => { /* ... */ });

// 最后一个中间件——所有 next(err) 最终到这里
app.use((err, req, res, next) => {
    // 区分已知错误和未知错误
    if (err.isOperational) {
        // 已知的业务错误：404、422 等——告诉客户端发生了什么
        return res.status(err.statusCode).json({
            error: { code: err.code, message: err.message }
        });
    }

    // 未知的程序错误：记录完整堆栈，返回通用 500
    console.error('UNEXPECTED ERROR', err);
    res.status(500).json({
        error: { code: 'INTERNAL_ERROR', message: '服务器内部错误' }
    });
});
```

什么是 Operational Error 你应该自己造：

```javascript
class AppError extends Error {
    constructor(message, statusCode, code) {
        super(message);
        this.isOperational = true;  // 标记：这是我预期的错误
        this.statusCode = statusCode;
        this.code = code;
    }
}

// 用的时候
throw new AppError('用户不存在', 404, 'USER_NOT_FOUND');
```

## 第三道防线：进程边界

前两道防线都没拦住——这是洪水冲过了排水沟，到了堤坝面前：

```javascript
// 最后防线——记录、优雅退出、让守护进程重启
process.on('uncaughtException', (err) => {
    console.error('FATAL: uncaught exception', err);
    // 不要在这里做异步操作——反正马上要死了
    process.exit(1);  // 堤坝决口，发出求救信号
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('FATAL: unhandled rejection', reason);
    process.exit(1);
});
```

但这里的核心原则是：**到了这道防线就不要恢复了**。进程内部状态可能已经坏了（内存被写花、连接池泄漏等），最好的做法是记录、退出、让守护进程重启一个干净的新进程。

## 第四道防线：优雅退出

```javascript
// 收到 SIGTERM 信号（K8s/Docker 发来的）——
// 不是错误处理，但是进程退出的最后一环
process.on('SIGTERM', async () => {
    console.log('收到 SIGTERM，开始优雅退出');

    // 1. 停止接收新请求
    server.close();

    // 2. 等待正在处理的请求完成（最多等 30 秒）
    setTimeout(() => {
        console.error('强制退出：有请求 30 秒内未完成');
        process.exit(1);
    }, 30000).unref();

    // 3. 关闭数据库连接
    await db.close();
});
```

## 错误处理检查清单

设计一个新服务时，问自己四个问题：

```text
□ 第一道防线——每个 async 函数有人 catch 吗？
   → express-async-errors 或 asyncWrap

□ 第二道防线——EventEmitter 有 error 事件监听器吗？
   → Stream、数据库连接、网络请求

□ 第二道防线——全局错误中间件设置了没？
   → 区分 isOperational 还是 unknown

□ 第三道防线——进程级错误能优雅退出吗？
   → uncaughtException / unhandledRejection + 记录 + 退出

□ 第四道防线——部署上有自动重启吗？
   → Docker restart: always / PM2 / K8s
```

## 几个常见的不要

**1. 不要用 try-catch 吞掉错误什么都不做**

```javascript
// ❌ 错误像小偷进了空房间——来去无声
try { await riskyOp(); }
catch (e) {}

// ✅ 至少记个日志
try { await riskyOp(); }
catch (e) { console.error('riskyOp failed', e); }
```

**2. 不要在回调里 throw**

```javascript
// ❌ 回调里的 throw 不会被外面的 try-catch 捕获
setTimeout(() => {
    throw new Error('boom');  // → uncaughtException → 💥
}, 1000);
```

**3. 不要把 uncaughtException 当恢复机制**

```javascript
// ❌ 这是最危险的陷阱——进程状态可能已经坏了
process.on('uncaughtException', (err) => {
    console.error(err);
    // 不要继续处理请求！process.exit(1) 是正确的做法
});
```

## 小结

Node.js 错误处理不是加 try-catch——是四道防线各司其职。做个类比：你家的安全不是只靠门锁（try-catch），还需要小区门禁（全局错误中间件）、报警器（uncaughtException）、保险公司（PM2/K8s 重启）。漏了任何一道，出了事你得自己扛。

---

**返回：** [Node.js 笔记](index.md)
