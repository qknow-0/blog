# Kafka 生产环境最佳实践

> 基于 Apache Kafka 3.x + KafkaJS（Node.js）。

## 一句话

Kafka 生产环境的核心：**分区数选对、副本数配够、Consumer Group 管好、监控告警到位**。

## 1. 分区数怎么选

| 考量 | 建议 |
|---|---|
| 并行度 | 分区数 ≥ 消费者数 |
| 吞吐 | 分区数 ≥ Broker 数 × 2 |
| 初始值 | **12-24 个分区**（大部分场景够用） |
| 上限 | 单 Topic 不超过 1000 个分区（管理开销） |

**坑：** 分区数只能增不能减。一开始设太多，后面想减少只能重建 Topic。

## 2. 副本配置

```properties
# server.properties
default.replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false
```

| 配置 | 含义 | 推荐值 |
|---|---|---|
| `replication.factor` | 副本数 | 3（至少 3 个 Broker） |
| `min.insync.replicas` | 最小同步副本数 | 2 |
| `acks`（Producer） | 等多少副本确认 | all |
| `unclean.leader.election.enable` | 允许非 ISR 副本成为 Leader | false |

## 3. 消息保留策略

```properties
# 按时间保留
log.retention.hours=168        # 7 天

# 按大小保留
log.retention.bytes=1073741824 # 1GB

# 段大小
log.segment.bytes=1073741824   # 1GB
```

## 4. Consumer Group 管理

```javascript
const consumer = kafka.consumer({
  groupId: 'order-processor',
  sessionTimeout: 30000,
  heartbeatInterval: 10000,
  maxWaitTimeInMs: 5000,
  rebalanceTimeout: 60000,
  partitionAssigner: [CooperativeAssigner],
});
```

| 配置 | 含义 | 推荐值 |
|---|---|---|
| `session.timeout.ms` | 心跳超时 | 30000（30s） |
| `heartbeat.interval.ms` | 心跳间隔 | 10000（10s） |
| `max.poll.interval.ms` | 两次 poll 最大间隔 | 300000（5min） |
| `rebalance.timeout.ms` | Rebalance 超时 | 60000（1min） |

## 5. 安全配置

```properties
# SSL/TLS
ssl.keystore.location=/path/to/kafka.server.keystore.jks
ssl.keystore.password=changeit
ssl.truststore.location=/path/to/kafka.server.truststore.jks
ssl.truststore.password=changeit
ssl.client.auth=required

# SASL
sasl.enabled.mechanisms=PLAIN,SCRAM-SHA-256
sasl.mechanism.inter.broker.protocol=PLAIN
```

## 6. 监控 Checklist

```javascript
// 每分钟检查
async function healthCheck() {
  // 1. Consumer Lag
  const lag = await getConsumerGroupLag('my-group', 'my-topic');
  if (lag.totalLag > 10000) alert('Consumer lag high');

  // 2. 未同步分区
  const metadata = await admin.fetchTopicMetadata({ topics: ['my-topic'] });
  const underReplicated = metadata.topics[0].partitions.filter(
    p => p.isr.length < p.replicas.length
  );
  if (underReplicated.length > 0) alert('Under-replicated partitions');

  // 3. Consumer Group 状态
  const groups = await admin.listGroups();
  // 检查是否有 REBALANCING 状态的组
}
```

## 7. 常见坑

| 坑 | 原因 | 解决方案 |
|---|---|---|
| 消息顺序乱 | 多 Partition | 同 Key 进同 Partition |
| Consumer 空闲 | 分区数 < 消费者数 | 分区数 ≥ 消费者数 |
| Rebalance 频繁 | 心跳超时太短 | 增大 session.timeout.ms |
| 消息重复 | At-Least-Once + 处理失败 | 幂等处理 |
| 磁盘爆满 | 保留时间太长 | log.retention.hours=168 |
| 连接数过多 | 每个应用独立连接 | 连接池 / 共享 Consumer |

## 小结

```bash
# 生产环境最小配置
default.replication.factor=3
min.insync.replicas=2
acks=all
log.retention.hours=168
session.timeout.ms=30000
heartbeat.interval.ms=10000
```

这 6 行配置覆盖了 Kafka 生产环境 80% 的问题。
