# （四）Orbien：Rust 写的自托管内网穿透，5MB 的 frp 替代品

> 本文基于 Orbien 最新版本，写于 2026-08-23。

## 一句话总结

Orbien 是一个 Rust 写的内网穿透工具，架构和 frp 类似——服务端放公网，客户端放内网，两者之间建立隧道把内网服务暴露出去。但它比 frp 更轻（5MB vs 10MB+），支持更多传输协议（TCP/WebSocket/QUIC/KCP），而且自带桌面客户端和 Web 管理面板。

## 和前三篇的区别

前三篇讲的 ngrok、Cloudflare Tunnel、localtunnel 都是**SaaS 服务**——你不需要自己部署服务端，别人帮你跑好了中转服务器。Orbien 走的是**自托管路线**，你自己有一台公网服务器，在上面跑 orbien-server，内网机器上跑 orbien 客户端，数据完全经过你自己的服务器。

**什么时候用 Orbien 而不是 ngrok？**

- 你有公网服务器，不想把流量经过第三方
- 需要长期稳定的隧道，而不是临时调试
- 需要 UDP 转发（比如 DNS、游戏服务器）
- 需要自定义域名和 TLS 证书管理
- 对带宽和延迟有要求，不想被 SaaS 服务的免费额度限制

## 安装

去 [GitHub Releases](https://github.com/orbien-org/orbien/releases) 下载对应平台的二进制，解压即用。

服务端只需要 `orbien-server`，客户端只需要 `orbien`：

```bash
# 服务端（公网服务器）
wget https://github.com/orbien-org/orbien/releases/latest/download/orbien-server-x86_64-unknown-linux-gnu.tar.gz
tar -xzf orbien-server-x86_64-unknown-linux-gnu.tar.gz
./orbien-server --version

# 客户端（内网机器）
wget https://github.com/orbien-org/orbien/releases/latest/download/orbien-x86_64-unknown-linux-gnu.tar.gz
tar -xzf orbien-x86_64-unknown-linux-gnu.tar.gz
./orbien --version
```

macOS 用户也可以用 Homebrew（如果官方支持的话），或者直接下载 aarch64 版本。

## 快速开始：暴露内网 SSH

这是最经典的场景——你有一台没有公网 IP 的开发机，想在外面随时 SSH 上去。

### 第一步：启动服务端

在公网服务器上创建配置文件 `orbien-server.toml`：

```toml
listen = "0.0.0.0:9527"
```

启动：

```bash
./orbien-server -c orbien-server.toml
```

就这么简单。服务端只需要一个监听端口。

### 第二步：配置客户端

在内网机器上创建 `orbien.toml`：

```toml
server = "YOUR_SERVER_IP:9527"

[[tunnels]]
name = "ssh"
protocol = "tcp"
service = "127.0.0.1:22"
remotePort = 9000
```

启动：

```bash
./orbien -c orbien.toml
```

### 第三步：从外部访问

```bash
ssh -p 9000 user@YOUR_SERVER_IP
```

现在任何地方都能 SSH 到你的内网机器了。

### 多隧道

一个客户端可以配置多个隧道，每个隧道暴露一个内网服务：

```toml
server = "YOUR_SERVER_IP:9527"

[[tunnels]]
name = "ssh"
protocol = "tcp"
service = "127.0.0.1:22"
remotePort = 9000

[[tunnels]]
name = "mysql"
protocol = "tcp"
service = "127.0.0.1:3306"
remotePort = 9001

[[tunnels]]
name = "redis"
protocol = "tcp"
service = "127.0.0.1:6379"
remotePort = 9002
```

每个 `[[tunnels]]` 是一个独立的隧道，`name` 必须唯一。

## 安全加固

### Token 认证

上面那个配置谁都能连，不安全。加上 token 认证：

**服务端** `orbien-server.toml`：

```toml
listen = "0.0.0.0:9527"

[auth]
token = "your-secret-token-here"
```

**客户端** `orbien.toml`：

```toml
server = "YOUR_SERVER_IP:9527"

[auth]
token = "your-secret-token-here"

[[tunnels]]
name = "ssh"
protocol = "tcp"
service = "127.0.0.1:22"
remotePort = 9000
```

两端 token 必须一致。Orbien 不会把 token 明文发到服务端——它用 token 计算摘要来验证，所以不用担心 token 在传输过程中被截获。

### TLS 加密

控制通道（客户端和服务端之间的连接）默认不加密。加上 TLS：

**服务端**：

```toml
listen = "0.0.0.0:9527"

[transport.tls]
force = true
certFile = "/path/to/server.crt"
keyFile = "/path/to/server.key"
```

**客户端**：

```toml
server = "YOUR_SERVER_IP:9527"

[transport.tls]
enable = true
trustedCaFile = "/path/to/ca.crt"
serverName = "orbien.example.com"
```

如果你的服务端证书是自签名的，客户端可以省略 `trustedCaFile`，这样就只加密不验证证书：

```toml
[transport.tls]
enable = true
```

### mTLS（双向 TLS）

如果你想让服务端也验证客户端身份：

**服务端**加上 `trustedCaFile`：

```toml
[transport.tls]
force = true
certFile = "/path/to/server.crt"
keyFile = "/path/to/server.key"
trustedCaFile = "/path/to/ca.crt"
```

**客户端**提供自己的证书：

```toml
[transport.tls]
enable = true
certFile = "/path/to/client.crt"
keyFile = "/path/to/client.key"
trustedCaFile = "/path/to/ca.crt"
serverName = "orbien.example.com"
```

服务端一旦设置了 `trustedCaFile`，会自动强制 TLS 并验证客户端证书。

## HTTP 隧道：暴露 Web 服务

TCP 隧道只能转发端口，HTTP 隧道可以做域名路由、Basic Auth、Host 头改写等。

### 基础配置

**服务端**需要开启 HTTP 网关端口：

```toml
listen = "0.0.0.0:9527"
httpGwPort = 80
```

**客户端**配置 HTTP 隧道：

```toml
server = "YOUR_SERVER_IP:9527"

[[tunnels]]
name = "web"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["web.example.com"]
```

把 `web.example.com` 的 DNS 指向服务端 IP，然后访问 `http://web.example.com` 就能看到内网的 Web 服务。

### 短域名（子域名前缀）

如果你有一个根域名，不想为每个服务都配完整域名，可以这样：

**服务端**：

```toml
listen = "0.0.0.0:9527"
httpGwPort = 80
rootDomain = "example.com"
```

**客户端**：

```toml
server = "YOUR_SERVER_IP:9527"

[[tunnels]]
name = "blog"
protocol = "http"
service = "127.0.0.1:3000"
domains = ["blog"]

[[tunnels]]
name = "api"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["api"]
```

这样 `blog.example.com` 和 `api.example.com` 分别指向不同的内网服务。短域名和完整域名可以混用。

### HTTP Basic Auth

在隧道层面加一层认证，不需要改内网服务本身：

```toml
[[tunnels]]
name = "web-auth"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["web.example.com"]
basicAuthUser = "alice"
basicAuthPassword = "secret"
```

没有正确凭据的请求直接返回 401。

### 用户路由

同一个域名，根据 Basic Auth 的用户名分流到不同的内网服务：

```toml
[[tunnels]]
name = "web-alice"
protocol = "http"
service = "127.0.0.1:8081"
domains = ["web.example.com"]
routeByHTTPUser = "alice"
basicAuthUser = "alice"
basicAuthPassword = "secret"

[[tunnels]]
name = "web-default"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["web.example.com"]
```

alice 登录后看到的是 8081 端口的服务，其他用户（或不带认证的请求）走 8080 端口的默认服务。

### Host 头改写

有些内网服务绑定了特定的 Host 头，可以这样改：

```toml
[[tunnels]]
name = "web"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["web.example.com"]
hostHeaderRewrite = "127.0.0.1"
```

请求到达内网服务时，`Host` 头会被改写成 `127.0.0.1`。

## HTTPS 隧道

HTTPS 和 HTTP 类似，但服务端需要开启 HTTPS 网关端口：

```toml
listen = "0.0.0.0:9527"
httpsGwPort = 443
```

客户端配置和 HTTP 一样，只是 `protocol` 改成 `https`。Orbien 支持两种模式：

1. **透明转发**：HTTPS 流量原样转发到内网服务，由内网服务自己处理 TLS
2. **客户端 TLS 终止**：Orbien 客户端代为处理 TLS，内网服务接收的是明文 HTTP

具体配置参考官方文档的 HTTPS 隧道章节。

## UDP 隧道：DNS、游戏服务器

TCP 隧道覆盖不了 UDP 场景——DNS 查询、游戏服务器、VoIP 都是 UDP。Orbien 支持 UDP 隧道：

```toml
[[tunnels]]
name = "dns"
protocol = "udp"
service = "127.0.0.1:53"
remotePort = 9000
```

从外部测试：

```bash
dig @YOUR_SERVER_IP -p 9000 example.com
```

UDP 隧道有一个额外参数 `udpPacketSize`（默认 1500），控制最大 UDP 包长度：

```toml
[[tunnels]]
name = "dns"
protocol = "udp"
service = "127.0.0.1:53"
remotePort = 9000
udpPacketSize = 4096
```

## 传输协议选型

Orbien 支持四种传输协议，不同场景选不同的：

| 协议 | 适用场景 | 特点 |
|------|----------|------|
| **TCP** | 默认，绝大多数场景 | 可靠、稳定，支持 TCP 多路复用 |
| **WebSocket** | 需要穿透 HTTP 代理 | 与 TCP 共用服务端端口，CDN 友好 |
| **QUIC** | 高丢包网络 | 基于 UDP，0-RTT 握手，弱网优化 |
| **KCP** | 高延迟、高丢包网络 | 比 TCP 快 30%-40%，但消耗更多带宽 |

### 切换传输协议

**WebSocket**：

```toml
# 客户端
[transport]
protocol = "websocket"
```

**QUIC**：

```toml
# 客户端
[transport]
protocol = "quic"
```

**KCP**：

```toml
# 客户端
[transport]
protocol = "kcp"
```

服务端不需要修改——TCP 和 WebSocket 共用同一个 `listen` 端口，QUIC 和 KCP 需要服务端单独配置端口（参考官方文档）。

### TCP 多路复用（tcpMux）

默认开启，多条隧道复用一条 TCP 连接，减少连接数和握手开销：

```toml
# 客户端
[transport]
tcpMux = true
```

关闭 tcpMux 后每条隧道独立连接，需要配心跳：

```toml
[transport]
tcpMux = false
heartbeatInterval = 30
heartbeatTimeout = 90
```

## 带宽限制

如果不想让某个隧道占满带宽：

```toml
[[tunnels]]
name = "download"
protocol = "tcp"
service = "127.0.0.1:80"
remotePort = 9000

[transport]
bandwidth = 10        # 限制 10 Mbps
bandwidthLimitSide = "client"
```

`bandwidthLimitSide` 可以选 `"client"` 或 `"server"`，决定在隧道哪一端限速。

## PROXY Protocol

如果你的服务端前面还有一层反向代理（如 Nginx、HAProxy），需要保留真实客户端 IP：

```toml
[[tunnels]]
name = "web"
protocol = "tcp"
service = "127.0.0.1:8080"
remotePort = 9000

[transport]
proxyProtocolVersion = "v2"
```

支持 v1 和 v2 两个版本，v2 支持更多协议（包括 UDP）。

## 管理面板

Orbien 自带一个轻量 Web 管理面板，可以查看隧道状态、流量统计等。在服务端配置中开启（具体配置见官方文档的 Dashboard 章节）。

另外还有一个跨平台桌面客户端 **Orbien Desktop**，用 Rust 写的原生 GUI，可以在图形界面里管理隧道，不需要手写 TOML 配置文件。

## 环境变量注入

所有配置项都可以通过环境变量覆盖，适合 Docker 部署和 CI/CD 场景：

```bash
export ORBIEN_SERVER="YOUR_SERVER_IP:9527"
export ORBIEN_AUTH_TOKEN="your-secret-token"
./orbien -c orbien.toml
```

环境变量的映射规则参考官方文档的环境变量章节。

## 和 frp 的对比

| 维度 | Orbien | frp |
|------|--------|-----|
| 语言 | Rust | Go |
| 二进制大小 | ~5MB | ~10MB+ |
| 传输协议 | TCP/WebSocket/QUIC/KCP | TCP/WebSocket/QUIC/KCP |
| 隧道协议 | TCP/UDP/HTTP/HTTPS | TCP/UDP/HTTP/HTTPS/STCP |
| TCP 多路复用 | ✅ | ✅ |
| TLS/mTLS | ✅ | ✅ |
| 桌面客户端 | ✅ Rust 原生 GUI | ❌ |
| Web 管理面板 | ✅ | ✅ |
| Java SDK | ✅ | ❌ |
| 内存占用 | 低（无 GC） | 中（Go GC） |
| 社区规模 | 新兴，较小 | 成熟，75k+ stars |

Orbien 的核心优势是 Rust 带来的性能和无 GC 停顿，以及原生桌面客户端。frp 的优势是社区更大、文档和教程更多、STCP（secret TCP）等额外功能。

## 实战场景

### 场景一：远程开发

开发机在公司内网，回家后想继续写代码：

```toml
server = "YOUR_VPS_IP:9527"

[[tunnels]]
name = "ssh"
protocol = "tcp"
service = "127.0.0.1:22"
remotePort = 9000

[[tunnels]]
name = "code-server"
protocol = "http"
service = "127.0.0.1:8080"
domains = ["code.example.com"]
```

SSH 连进去写代码，或者用 code-server 在浏览器里写。

### 场景二：自建服务暴露

家里 NAS 上跑着 Jellyfin、Home Assistant 等自建服务，想把它们暴露到公网：

```toml
server = "YOUR_VPS_IP:9527"

[[tunnels]]
name = "jellyfin"
protocol = "http"
service = "192.168.1.100:8096"
domains = ["jellyfin.example.com"]

[[tunnels]]
name = "homeassistant"
protocol = "http"
service = "192.168.1.100:8123"
domains = ["ha.example.com"]
```

### 场景三：临时演示

给客户演示本地正在开发的项目，用短域名快速暴露：

```bash
# 服务端
./orbien-server -c orbien-server.toml  # httpGwPort = 80, rootDomain = "demo.example.com"

# 客户端
./orbien -c orbien.toml
```

```toml
# 客户端配置
server = "YOUR_VPS_IP:9527"

[[tunnels]]
name = "demo"
protocol = "http"
service = "127.0.0.1:3000"
domains = ["client-demo"]
```

客户访问 `http://client-demo.demo.example.com` 就能看到你的本地项目。

## 总结

Orbien 是一个设计很现代的内网穿透工具。Rust 带来的性能优势、四种传输协议的灵活组合、桌面客户端和 Web 面板的开箱即用，让它比 frp 更有"产品感"。

**选 Orbien 如果**：你想要最轻量的二进制、想要原生桌面 GUI、在意内存占用、需要 Java SDK。

**选 frp 如果**：你需要更成熟的社区生态、更多的文档和教程、STCP 等高级功能。

**选 ngrok/Cloudflare Tunnel 如果**：你没有公网服务器，只需要临时隧道，不想维护任何服务端。

Orbien 目前还在快速迭代中，社区规模不如 frp，但基础功能已经很扎实了。如果你有一台闲置的 VPS，值得一试。