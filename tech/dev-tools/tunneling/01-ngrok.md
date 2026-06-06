# ngrok：把 localhost 暴露到公网的最快方式

> 本地跑了一个 webhook receiver，想测试第三方回调？做了个 demo 想给远程的同事看一眼？ngrok 做的事就一件：给你的 `localhost:3000` 分配一个公网 URL，外部请求通过加密隧道直达你本机。

## 一句话定位

```bash
ngrok http 3000
# https://abc123.ngrok-free.app → http://localhost:3000
```

你的本地服务从 `localhost` 变成了全世界可访问的 HTTPS URL。不需要配路由器端口转发、不需要改防火墙、不需要申请公网 IP。

## 安装

```bash
# macOS
brew install ngrok

# 或者直接下载二进制
# https://ngrok.com/download

# 注册免费账号，拿到 authtoken
ngrok config add-authtoken <your-token>
```

免费账号的限制：
- 一个在线 tunnel
- 随机子域名（每次启动会变）
- 每分钟 40 个连接
- 不支持自定义域名

对日常开发调试足够了。需要固定域名或更多 tunnel 就付费。

## 基本用法

```bash
# HTTP 服务
ngrok http 3000

# 指定协议
ngrok http http://localhost:3000

# HTTPS only
ngrok http https://localhost:3000

# 多个端口
ngrok http 3000 8080

# TCP 隧道——比如暴露本地 PostgreSQL
ngrok tcp 5432
# tcp://0.tcp.ngrok.io:12345 → localhost:5432

# TLS 隧道——端到端加密，ngrok 不解密
ngrok tls 8443
```

## 固定域名——不用每次换 URL

免费版每次启动隧道会随机分配一个子域名（`abc123.ngrok-free.app`）。测试 webhook 时每次都要去第三方平台更新回调地址。付费版用 `--domain` 锁定：

```bash
ngrok http --domain=myapp.ngrok.dev 3000
# https://myapp.ngrok.dev → http://localhost:3000
# 每次重启 URL 不变
```

## 配置化——ngrok.yml

```yaml
# ~/Library/Application Support/ngrok/ngrok.yml
version: "3"
agent:
  authtoken: <your-token>

tunnels:
  web:
    proto: http
    addr: 3000
    domain: web.myapp.ngrok.dev

  api:
    proto: http
    addr: 8080
    domain: api.myapp.ngrok.dev

  db:
    proto: tcp
    addr: 5432
```

```bash
# 启动所有隧道
ngrok start --all

# 只启动指定隧道
ngrok start web api
```

配置文件让多个隧道一次启动——本地一套微服务（前端 3000、API 8080、数据库 5432）同时暴露到公网，方便远程联调。

## 请求审查——Inspector

启动隧道后，打开 `http://127.0.0.1:4040`，能看到所有经过隧道的请求：

- 请求体、响应体全量展示
- Header 一览
- 耗时
- **Replay**——点一下按钮重放某个请求

这是调 webhook 最实用的功能——第三方回调过来的是什么 payload？在 Inspector 里直接看，不需要在代码里临时加 `print`。

```bash
# Web Interface（非付费版也可以用）
http://127.0.0.1:4040
```

## 实际场景

### 场景一：Webhook 本地调试

```bash
# 本地起一个 webhook receiver
python -m http.server 8000

# 暴露出去
ngrok http 8000
# https://abc123.ngrok-free.app → localhost:8000

# 把 https://abc123.ngrok-free.app/webhook 填到 Stripe/GitHub/Slack 的 webhook 设置里
# 在 http://127.0.0.1:4040 里看每一次回调的 payload
```

之前调试 Stripe webhook 的流程：部署到服务器 → 等 CI/CD → 改代码 → 再部署 → 再看日志。ngrok 把它变成：本地改代码 → 立刻看回调 → Replay 重放。

### 场景二：给远程同事看 demo

```bash
ngrok http 5173  # Vite dev server
# "Hey，打开这个链接看看我做的功能"
# https://abc123.ngrok-free.app
```

不需要部署到 staging 环境、不需要让同事连 VPN 到内网。一个临时 URL，demo 完就可以关掉。

### 场景三：移动端调试

```bash
ngrok http 3000 --domain=dev.myapp.ngrok.dev
# iOS 模拟器 / 真机上直接访问 https://dev.myapp.ngrok.dev
```

移动端 App 连 `localhost` 天然隔着一个网络层。ngrok 把本地服务变成真实 HTTPS URL，iOS/Android 真机直接用。

### 场景四：OAuth 回调

```bash
ngrok http 3000 --domain=auth.myapp.ngrok.dev
# Google OAuth redirect URI: https://auth.myapp.ngrok.dev/oauth/callback
```

OAuth 提供商（Google、GitHub、Auth0）要求回调地址必须是公网 URL。本地 `localhost:3000/oauth/callback` 填不进去。固定域名保证了每次重启不换 URL——OAuth 配置一次就行。

## 高级功能

### Basic Auth——加一层密码保护

```bash
ngrok http 3000 --basic-auth="user:password"
# 访问前先弹出 HTTP Basic Auth 对话框
```

临时的 demo 不想被搜索引擎索引或陌生人访问——加个密码就安全了。

### Request Header 修改

```yaml
tunnels:
  app:
    proto: http
    addr: 3000
    request_header:
      add:
        x-ngrok: "true"        # 后端知道请求经过了 ngrok
      remove:
        - x-internal-token      # 去掉内部用的 header
```

### IP 白名单

```yaml
tunnels:
  app:
    proto: http
    addr: 3000
    ip_restriction:
      allow_cidrs:
        - "203.0.113.0/24"     # 只允许公司 VPN 出口 IP
```

## ngrok vs 其他方案

| | ngrok | Cloudflare Tunnel | localtunnel | localhost.run |
|---|---|---|---|---|
| 安装 | brew / 二进制 | cloudflared | npm | ssh |
| 固定域名 | 付费 | 免费（需域名托管 CF） | 付费 | ❌ |
| Inspector | ✅ 自带 | ❌ | ❌ | ❌ |
| TCP 隧道 | ✅ | ❌ 仅 HTTP | ❌ | ✅ |
| 免费版限制 | 1 tunnel, 40 conn/min | 无硬性限制 | 随机子域名 | 随机子域名 |
| 自定义域名 | 付费 | 免费 | 付费 | ❌ |

**选 ngrok**：你要看请求内容（Inspector）、调 webhook、需要 TCP 隧道、不想折腾 Cloudflare 域名配置。

**选 Cloudflare Tunnel**：你有自己的域名托管在 Cloudflare、需要零成本固定域名、不需要 inspect 请求体。

## 总结

ngrok 的价值不是技术复杂度——SSH 反向隧道也能实现类似效果。它的价值是**开箱即用的体验**：自动 HTTPS 证书、Inspector 查请求、Replay 重放、固定域名、Basic Auth、配置文件管理。

下一篇看 Cloudflare Tunnel——如果你有自己的域名托管在 Cloudflare，它提供固定域名 + 零成本 + 不需要装额外 agent 的方案。

→ [（二）Cloudflare Tunnel：零成本的公网隧道方案](02-cloudflare-tunnel.md)
