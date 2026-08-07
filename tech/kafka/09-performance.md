# Kafka 性能调优：吞吐 vs 延迟

> 基于 Apache Kafka 3.x + KafkaJS（Node.js）。

## 核心矛盾

吞吐和延迟是跷跷板——优化一个必然牺牲另一个。

```
高吞吐：大批量、长等待、压缩 → 延迟高
低延迟：小批量、短等待、不压缩 → 吞吐低
```

## Producer 调优

### 吞吐优先

```javascript
const producer = kafka.producer({
  maxInFlightRequests: 5,      // 并发请求数
  transactionTimeout: 30000,
});

await producer.send({
  topic: 'events',
  messages: batchMessages,
  acks: 1,                      // 不等所有副本
  compression: 'lz4',           // 压缩减少网络传输
  timeout: 30000,
});
```

```properties
# Producer 配置
linger.ms=20         # 等 20ms 攒一批
batch.size=65536     # 64KB 批次
buffer.memory=67108864  # 64MB 缓冲区
compression.type=lz4
acks=1
```

### 延迟优先

```javascript
await producer.send({
  topic: 'orders',
  messages: [{ key: 'order-1', value: '...' }],
  acks: -1,                     // 等所有 ISR 副本
  compression: 'none',          // 不压缩
  timeout: 1000,
});
```

```properties
linger.ms=0          # 有消息就发
batch.size=16384     # 16KB
acks=all
compression.type=none
```

## Consumer 调优

### 吞吐优先

```javascript
const consumer = kafka.consumer({
  groupId: 'batch-processor',
  sessionTimeout: 30000,
  heartbeatInterval: 10000,
  maxBytesPerPartition: 1048576,  // 每分区每次拉 1MB
  minBytes: 1,                    // 有数据就返回
});

await consumer.subscribe({ topic: 'events' });
await consumer.run({
  eachBatchAutoResolve: true,
  eachBatch: async ({ batch, resolveOffset, heartbeat }) => {
    // 批量处理
    const messages = batch.messages;
    await processBatch(messages);
    resolveOffset(messages[messages.length - 1].offset);
    await heartbeat();
  },
});
```

### 延迟优先

```javascript
const consumer = kafka.consumer({
  groupId: 'realtime-processor',
  sessionTimeout: 10000,
  heartbeatInterval: 3000,
  maxBytesPerPartition: 524288,   // 每分区每次拉 512KB
  minBytes: 1,
});

await consumer.run({
  eachMessage: async ({ topic, partition, message }) => {
    // 逐条处理，最低延迟
    await processMessage(message);
  },
});
```

## 关键配置对比

| 配置 | 吞吐优先 | 延迟优先 |
|---|---|---|
| `linger.ms` | 10-100 | 0 |
| `batch.size` | 64KB-1MB | 16KB |
| `acks` | 1 | all |
| `compression` | lz4/zstd | none |
| `max.bytes.per.partition` | 1MB+ | 256KB-512KB |
| `session.timeout.ms` | 30000 | 10000 |

## Broker 调优

```properties
# server.properties

# 网络线程数
num.network.threads=8

# IO 线程数
num.io.threads=16

# 发送缓冲区
socket.send.buffer.bytes=102400

# 接收缓冲区
socket.receive.buffer.bytes=102400

# 日志段大小
log.segment.bytes=1073741824

# 日志保留时间
log.retention.hours=168

# 副本同步流量限制
replica.fetch.max.bytes=10485760
```

## 压缩算法选择

| 算法 | 压缩率 | CPU | 适用场景 |
|---|---|---|---|
| `none` | 1x | 最低 | 延迟优先 |
| `gzip` | 高 | 高 | 存储优先 |
| `snappy` | 中 | 低 | 平衡 |
| `lz4` | 中 | 最低 | **吞吐优先首选** |
| `zstd` | 高 | 中 | **综合最优** |

## 小结

```
吞吐优先：linger.ms=20 + batch.size=64KB + compression=lz4 + acks=1
延迟优先：linger.ms=0 + batch.size=16KB + compression=none + acks=all
综合：linger.ms=5 + batch.size=32KB + compression=zstd + acks=all
```
