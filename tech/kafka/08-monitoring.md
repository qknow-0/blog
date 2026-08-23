# Kafka 监控与指标：Lag、JMX、Consumer Group 健康

> 基于 Apache Kafka 3.x + KafkaJS（Node.js）。

## 三个核心指标

| 指标 | 含义 | 告警阈值 |
|---|---|---|
| **Consumer Lag** | 消费者落后生产者多少条消息 | > 10,000 条 |
| **Under-Replicated Partitions** | 副本同步落后的分区数 | > 0 |
| **ISR Shrink/Expand** | ISR 集合变化频率 | 频繁变化 → 网络/磁盘问题 |

## Consumer Lag 监控（KafkaJS）

```javascript
const { Kafka } = require('kafkajs');

const kafka = new Kafka({ clientId: 'monitor', brokers: ['localhost:9092'] });
const admin = kafka.admin();

async function getConsumerGroupLag(groupId, topic) {
  await admin.connect();

  // 获取 Topic 的所有分区
  const topicOffsets = await admin.fetchTopicOffsets(topic);

  // 获取 Consumer Group 的 committed offsets
  const groupOffsets = await admin.fetchOffsets({ groupId, topic });

  // 计算每个分区的 lag
  const lagPerPartition = topicOffsets.map(({ partition, offset: latestOffset }) => {
    const committed = groupOffsets.find(g => g.partition === partition);
    const committedOffset = committed ? parseInt(committed.offset) : 0;
    const lag = parseInt(latestOffset) - committedOffset;
    return { partition, latestOffset, committedOffset, lag };
  });

  const totalLag = lagPerPartition.reduce((sum, p) => sum + p.lag, 0);

  return { lagPerPartition, totalLag };
}

// 使用
const lag = await getConsumerGroupLag('order-processor', 'orders');
console.log(`Total lag: ${lag.totalLag}`);
lag.lagPerPartition.forEach(p => {
  console.log(`  Partition ${p.partition}: lag=${p.lag}`);
});

await admin.disconnect();
```

## JMX 指标导出

Kafka Broker 默认暴露 JMX 指标。用 JMX Exporter 转成 Prometheus 格式：

```yaml
# jmx-exporter-config.yml
rules:
  - pattern: "kafka.server<type=BrokerTopicMetrics, name=MessagesInPerSec><>Count"
    name: "kafka_messages_in_total"
    type: COUNTER

  - pattern: "kafka.server<type=ReplicaManager, name=UnderReplicatedPartitions><>Value"
    name: "kafka_under_replicated_partitions"
    type: GAUGE
```

```bash
java -javaagent:jmx_prometheus_javaagent.jar=7071:jmx-exporter-config.yml \
  -jar kafka_2.13-3.7.0.jar
```

## 关键 JMX 指标

| 指标 | 路径 | 含义 |
|---|---|---|
| 消息入站速率 | `kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec` | 每秒消息数 |
| 字节入站速率 | `kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec` | 每秒字节数 |
| 未同步分区 | `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` | 副本落后的分区数 |
| Leader 选举速率 | `kafka.controller:type=ControllerStats,name=LeaderElectionRateAndTimeMs` | Leader 选举频率 |
| 请求队列大小 | `kafka.network:type=RequestMetrics,name=RequestQueueTimeMs` | 请求排队时间 |

## Consumer Group 健康检查

```javascript
async function checkConsumerGroupHealth(groupId) {
  await admin.connect();

  const groups = await admin.describeGroups([groupId]);
  const group = groups.groups[0];

  const members = group.members.map(member => ({
    memberId: member.memberId,
    clientId: member.clientId,
    host: member.host,
    assignments: member.memberAssignment
      ? member.memberAssignment.topics.flatMap(t =>
          t.partitions.map(p => `${t.topic}:${p}`)
        )
      : [],
  }));

  // 检查是否有空闲消费者（分配了 0 个分区）
  const idleMembers = members.filter(m => m.assignments.length === 0);
  if (idleMembers.length > 0) {
    console.warn(`⚠️ ${idleMembers.length} idle consumers (more consumers than partitions?)`);
  }

  return {
    groupId,
    state: group.state,
    members,
    idleMembers: idleMembers.length,
  };
}
```

## 告警规则（Prometheus）

```yaml
groups:
  - name: kafka-alerts
    rules:
      - alert: KafkaConsumerLagHigh
        expr: kafka_consumer_lag > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Consumer group {{ $labels.group }} lag is high"

      - alert: KafkaUnderReplicatedPartitions
        expr: kafka_under_replicated_partitions > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $value }} under-replicated partitions"
```

## 小结

| 监控对象 | 工具 | 关键指标 |
|---|---|---|
| Consumer Lag | KafkaJS Admin API / Burrow | lag per partition |
| Broker 健康 | JMX Exporter + Prometheus | UnderReplicated, ISR |
| Consumer 健康 | KafkaJS describeGroups | idle members, assignments |
| 告警 | Prometheus AlertManager | lag > 10k, partitions > 0 |
