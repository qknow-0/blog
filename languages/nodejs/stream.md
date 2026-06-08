# Node.js Stream：数据不是一次性搬完的

> 本文基于 Node.js 24 LTS。

假设你要处理一个 2GB 的日志文件。

最直觉的写法：

```js
import { readFile } from 'node:fs/promises';

const data = await readFile('access.log', 'utf-8');
// 2GB 全读进内存
```

如果你的服务器只有 1GB 内存，这段代码跑不了几秒就 OOM 了。

但不是非得这样。Node.js 给你提供了另一种处理数据的方式：**不一次读完，而是一小段一小段地读，读一段处理一段。**

这就是流。

大多数 Node.js 开发者每天都在用流——HTTP 请求是流、文件读写是流、数据库查询结果也可以是流。但你很少直接去想它，因为它太底层了。只有当你真的需要处理大文件、实时数据、管道拼接时，Stream 才会从背景走到前台。

这篇文章不是 API 手册。目的是让你真正理解流在做什么、为什么这样设计、以及哪些地方容易踩坑。

## 流的本质：把数据切成小块，逐块消费

如果不使用流，想处理文件就只能全部读完后开始处理。

流做的事情很简单：

```mermaid
flowchart LR
    A[大文件<br/>2GB] --> B[小块<br/>64KB]
    B --> C[小块<br/>64KB]
    C --> D[小块<br/>64KB]
    D --> E[小块<br/>64KB]
    E --> F[...]
    F --> G[小块<br/>64KB]
```

每读一小段（chunk），你就可以立刻处理它。内存在任何时刻只占几十 KB，不管文件是 2GB 还是 200GB。

三种数据总是适合用 Stream 处理：

- 数据很大，不能一次装进内存
- 数据还在陆续产生，还没到齐
- 数据需要经过多层转换再输出

这三个场景在 Node.js 里极其常见。

## 四种流，本质都是 EventEmitter

Node.js 所有的流都扩展自 `EventEmitter`。没有魔法——它就是在特定时机 emit 特定事件。

```js
import { createReadStream } from 'node:fs';

const stream = createReadStream('huge.log');

stream.on('data', (chunk) => {
  console.log(`收到 ${chunk.length} 字节`);
});

stream.on('end', () => {
  console.log('读完了');
});

stream.on('error', (err) => {
  console.error('出错了', err);
});
```

`data` 事件每 emit 一次，意味着又有一个 chunk 可用。`end` 表示再无更多数据。`error` 不用解释。

基于事件驱动这个事实，Node.js 把流按功能分了四种：

### Readable — 可读流

数据从这里出来。比如：

- `fs.createReadStream()`
- `http.IncomingMessage`（即 HTTP 请求的 body）
- `process.stdin`

核心特征：你可以从它读数据，不能往它写。

### Writable — 可写流

数据往这里进去。比如：

- `fs.createWriteStream()`
- `http.ServerResponse`（即 HTTP 响应的 body）
- `process.stdout`

核心特征：你可以往它写数据，不能从它读。

### Duplex — 双工流

既可读又可写，且读写通道独立。比如：

- `net.Socket`（TCP 连接）
- `tls.TLSSocket`

你写的和读的不是同一份数据。

### Transform — 转换流

双工流的特殊子类：读写有关联关系。你往它写数据，它经过某种转换后，从另一端读出来。

比如 `zlib.createGzip()` 就是一个典型的 Transform 流——你把原始数据写进去，从另一端读出来的是压缩后的字节。

这四种类型中，Readable 和 Writable 是最基本的，Duplex 和 Transform 是它们的组合。

## 读完本文最该带走的概念：背压

假设你正在读一个大文件，同时往一个慢速网络连接里写。

```js
import { createReadStream } from 'node:fs';
import { request } from 'node:http';

const readStream = createReadStream('bigfile.iso');

readStream.on('data', (chunk) => {
  // 直接往 HTTP 请求体写
  req.write(chunk);
});
```

问题：文件读取远比网络写入快。如果你的读速是 500 MB/s，但写速只有 5 MB/s，那差距的 495 MB/s 数据去了哪里？

**它们会在内存里堆积，排队等待被写出去。**

这就是背压。

### 什么叫背压

背压是流机制中最重要的反馈信号。

- 可读流产生数据的速度，超过了可写流消费数据的速度
- 内存里积压的 chunk 越来越多
- 最终内存耗尽，进程崩溃

它本质上是一种反向压力信号：**后面还没处理完，前面别急着继续给。**

### 背压是怎么工作的

Node.js 用一条很简单的规则实现背压：

`stream.write(chunk)` 的返回值。

```js
const canContinue = writable.write(chunk);
// canContinue === false 时，可写流的内部缓冲区已满
// 此时应该暂停读取，直到 writable 发出 'drain' 事件
```

当 `write()` 返回 `false` 时：

- 意味着写操作不是立即完成的，数据进入了内部缓冲区
- 这时应该暂停可读流
- 等可写流缓冲区排空后，会发出 `drain` 事件
- 收到 `drain` 后，再恢复读取

手动处理背压的代码会非常繁琐。所以 Node.js 提供了 `pipe()` 和 `pipeline()`。

## pipe()：自动处理背压

```js
import { createReadStream, createWriteStream } from 'node:fs';

createReadStream('source.log')
  .pipe(createWriteStream('dest.log'));
```

`pipe()` 帮你自动处理了上面所有逻辑：

- 读一块、写一块
- 写入返回 `false` 时自动暂停读流
- 收到 `drain` 后自动恢复
- 读完自动结束写流

但 `pipe()` 有一个致命缺陷：**它不转发错误，不会自动清理。**

如果中间的某个流出错了，`pipe()` 不会自动销毁链条上的其他流，也容易留下内存泄漏和僵尸连接。

## pipeline()：现代的正确选择

从 Node.js 10 开始，推荐使用 `pipeline()`，它解决了 `pipe()` 的所有遗留问题：

```js
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip } from 'node:zlib';

try {
  await pipeline(
    createReadStream('source.log'),
    createGzip(),
    createWriteStream('source.log.gz'),
  );
  console.log('压缩完成');
} catch (err) {
  console.error('管道中某一步失败', err);
}
```

`pipeline()` 比 `pipe()` 好在哪里：

- 任一阶段出错，整个管道自动销毁，不留泄漏
- 支持 Promise，自然融入 async/await
- 链上任意多个流，中间可以嵌套 Transform
- 完成后自动 resolve

如果你今天在写流处理代码，默认应该用 `pipeline()`，除非有特别明确的理由必须回到 `pipe()`。

## Transform：流处理里最实用的武器

在很多日常任务里，你其实不需要自己构造完整的可读/可写流组合。中间那个“读一点、改一点、写一点”的行为，用 `Transform` 流就够了。

```js
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';

const toUpperCase = new Transform({
  transform(chunk, encoding, callback) {
    this.push(chunk.toString().toUpperCase());
    callback();
  },
});

await pipeline(
  createReadStream('source.txt'),
  toUpperCase,
  createWriteStream('dest.txt'),
);
```

每一块数据进来，上调到大写，再传出去。处理完一块才开始下一块，内存在任何时候都只占一个 chunk 的大小。

Transform 最常见的三类用途：

- 格式转换：CSV 转 JSON、行分割、编码转换
- 过滤：只保留某些行、去掉某些字段
- 压缩/解压：`zlib.createGzip()`、`zlib.createUnzip()`

### 更贴近实际的例子：逐行读取大 CSV 并筛选

假设你有一个几百 MB 的 CSV，只想保留评分超过某个阈值的行：

```js
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';

const filterHighRated = new Transform({
  transform(chunk, encoding, callback) {
    const lines = chunk.toString().split('\n');
    const filtered = lines.filter((line) => {
      const parts = line.split(',');
      return parseFloat(parts[2]) >= 4.5;
    });
    this.push(filtered.join('\n'));
    callback();
  },
});

await pipeline(
  createReadStream('ratings.csv'),
  filterHighRated,
  createWriteStream('filtered.csv'),
);
```

注意：这里用 `split('\n')` 简化了演示。生产级行处理用 `readline` 模块更可靠。但它说明了 Transform 流的核心价值：**你只需要定义“一块数据怎么变”，不用管读和写的细节。**

## 什么时候该用流

问题不是“要不要用流”，而是“默认该不该把它当流”。

### 不用犹豫，直接上流的场景

- 大文件读写（超过内存容量）
- 网络请求的 request/response body 处理
- 实时数据管道：日志收集、ETL、消息处理
- 多层数据转换：读 → 解压 → 解析 → 过滤 → 写
- 压缩/解压
- 音视频流处理

### 不需要流的场景

- 很小的 JSON 配置文件
- 一次性读入、整体分析的数据
- 简单 API 调用，返回体只有几百字节

不是说不能用流，而是没必要为了流而流。

### 一个判断标准

如果你的代码里出现了下面这种模式，你应该切换到流：

```js
// ❌ 你能感觉到不对劲——全量读入，处理完再全量写出
const all = await readFile('big.csv', 'utf-8');
const processed = doSomething(all);
await writeFile('output.csv', processed);
```

换成：

```js
// ✅ 读一块、处理一块、写一块——内存恒定
await pipeline(
  createReadStream('big.csv'),
  transform,
  createWriteStream('output.csv'),
);
```

流帮你把“一次性全部”变成了“一次一小块”。

## 几个容易忽视的细节

### 1. readable 事件 vs data 事件

`data` 事件是流动模式，数据一到就推给你。`readable` 事件是暂停模式，数据到了只通知你“有东西可读”，由你决定读多少。

大多数场景用 `data` 配合 `pipe()`/`pipeline()` 就够了。`readable` 用在需要精确控制消费速度的高级场景。

### 2. objectMode

默认情况下，流只处理 `Buffer` 和字符串。如果你的数据是一系列对象（比如每一块是一个解析好的 JSON 记录），可以打开 `objectMode`：

```js
const parseJSON = new Transform({
  readableObjectMode: false,
  writableObjectMode: true,
  transform(chunk, encoding, callback) {
    this.push(JSON.stringify(JSON.parse(chunk.toString())));
    callback();
  },
});
```

`objectMode` 改变了流的基本假设——不再逐字节推进，而是逐对象推进。对于结构化数据管道非常实用。

### 3. 流默认是异步的，但 transform 函数里的代码是同步回调

`transform(chunk, encoding, callback)` 里的 `callback()` 必须在处理完成后调用，它告诉内部机制当前 chunk 已处理完毕，可以接收下一个。

如果处理步骤本身是异步的（比如要调一次 API 再 push），你可以传 `callback` 为第三个参数并在异步完成后调用，或者直接用 async generator。

### 4. 不要忘记错误处理

`pipeline()` 已经帮你统一了错误处理，但如果你在用 `pipe()` 或自己管理事件，每个流都必须单独监听 `error` 事件。

```js
const readable = createReadStream('file');
const writable = createWriteStream('output');

readable.on('error', handleError);
writable.on('error', handleError);

readable.pipe(writable);
```

忘记绑定 `error` 的流一旦出错，默认行为是抛出一个未捕获异常——进程直接挂掉。

## 总结

流不是 Node.js 的附加功能，它就是 Node.js 处理数据的基本方式。

最核心的三个概念：

- **背压**：消费者通过 `write()` 返回值和 `drain` 事件来告诉生产者“慢一点”。不理解背压，就不理解流。
- **pipe/pipeline**：自动管理背压和生命周期，能用 `pipeline()` 就别用 `pipe()`。
- **Transform**：最常用的自定义流类型，只需定义“一块数据怎么变”。

用流处理数据的本质是：**把“把所有数据装进内存再做处理”这种思路，换成“数据像水流一样经过，处理完就走”的思路。**

如果你能从全量处理转向增量处理，Node.js 能稳定处理的数据规模会立刻提升不止一个数量级。
