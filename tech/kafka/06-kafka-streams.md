# Kafka Streams：流处理入门

> 基于 Apache Kafka 3.x。Kafka Streams 是 Java 库，Node.js 生态中可用 ksqlJS 或 Faust（Python）替代。

## 一句话

Kafka Streams 是一个 Java 库——不是独立服务，不需要额外集群。你的应用本身就是一个流处理器，直接消费 Kafka Topic、处理、写回 Kafka。

## 核心概念

```mermaid
flowchart LR
    INPUT["Input Topic"] --> STREAM["KStream<br/>无界数据流"]
    STREAM --> PROCESS["处理逻辑<br/>filter/map/aggregate"]
    PROCESS --> OUTPUT["Output Topic"]
```

| 概念 | 一句话 |
|---|---|
| **KStream** | 无界数据流，每条消息独立处理 |
| **KTable** | 变更日志流，每条消息是某个 Key 的最新值 |
| **GlobalKTable** | 每个实例都有完整副本 |
| **Topology** | 处理拓扑图（DAG） |

## 入门示例

```java
StreamsBuilder builder = new StreamsBuilder();

builder.stream("input-topic", Consumed.with(Serdes.String(), Serdes.String()))
    .mapValues(value -> value.toUpperCase())
    .to("output-topic", Produced.with(Serdes.String(), Serdes.String()));

KafkaStreams streams = new KafkaStreams(builder.build(), config);
streams.start();
```

## KStream vs KTable

```java
// KStream：每条消息独立
KStream<String, String> stream = builder.stream("events");
// → 消息：("user1", "click"), ("user1", "view"), ("user1", "click")

// KTable：每个 Key 的最新值
KTable<String, String> table = builder.table("user-profiles");
// → Key="user1" 的最新值
```

## 窗口聚合

```java
builder.stream("clicks")
    .groupBy((key, value) -> value)
    .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
    .count()
    .toStream()
    .to("click-counts");
```

## 小结

Kafka Streams = 无状态 + 有状态 + 窗口聚合。不需要 Flink/Spark，你的 Java 应用本身就是流处理器。

> **Node.js 替代方案：** [ksqlDB](https://ksqldb.io/)（SQL 接口）、[BullMQ](https://docs.bullmq.io/)（Redis-based）、[Faust](https://github.com/robinhood/faust)（Python）。
