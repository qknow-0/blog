# 网络底层

TCP/IP 传输层与网络层——连接怎么建立、数据怎么可靠送达、包怎么找到路。

配套：[HTTP 应用层系列](../http/index.md) 已覆盖应用层协议。

## 阅读路径

```mermaid
flowchart LR
    A["01 分层模型<br>地图"] --> B["02 TCP 握手与挥手<br>连接管理"]
    B --> C["03 TCP 可靠传输<br>不丢不乱不堵"]
    C --> D["04 UDP<br>不靠谱被偏爱"]
    D --> E["05 DNS<br>域名到 IP"]
    E --> F["06 IP 寻址<br>包怎么找路"]
    F --> G["07 Socket 抓包实战<br>亲手验证一切"]
```

## 文章列表

| # | 主题 | 解决什么问题 |
|---|------|-------------|
| [01](01-layering.md) | 网络分层模型 | 协议太多怎么组织 |
| [02](02-tcp-handshake.md) | TCP 三次握手与四次挥手 | 连接怎么建立和关闭 |
| [03](03-tcp-reliability.md) | TCP 可靠传输 | 不丢、不乱、不堵 |
| [04](04-udp.md) | UDP | 为什么实时应用偏爱"不靠谱" |
| [05](05-dns.md) | DNS | 域名怎么变成 IP |
| [06](06-ip-addressing.md) | IP 与寻址 | 数据包怎么找到目的地 |
| [07](07-socket-debug.md) | Socket + 抓包实战 | 用 tcpdump 亲眼验证理论 |
