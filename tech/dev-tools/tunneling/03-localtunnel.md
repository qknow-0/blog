# localtunnel 与轻量替代方案

> ngrok 要注册、Cloudflare Tunnel 要域名托管。有时候你只是想要一条命令、一个临时 URL、不注册任何账号——这就是 localtunnel 的用武之地。这一篇把轻量方案全列出来，并做一个最终的对比和选型指南。

## localtunnel——零配置，一条命令

```bash
# 安装
npm install -g localtunnel

# 使用
lt --port 3000
# your url is: https://loud-fox-42.loca.lt
```

不需要注册、不需要 API Key、不需要域名。一条命令、一个随机子域名、`localhost:3000` 暴露到公网。

```bash
# 指定子域名
lt --port 3000 --subdomain myapp
# https://myapp.loca.lt → localhost:3000
# （前提是 myapp 没被别人占用）

# 自定义 host header
lt --port 3000 --local-host myapp.local
```

localtunnel 的架构很简单：npm 安装的客户端 → localtunnel.me 服务器 → 你本地。流量经过第三方服务器——和 ngrok 一样，不自己架设基础设施。

**注意**：`loca.lt` 域名申请不到 HTTPS 证书（Let's Encrypt 不支持 `.lt` 二级子域名），所以首次访问 localtunnel URL 时浏览器可能显示安全警告。访问者需要点一下「高级 → 继续访问」。对临时测试够用，对客户 demo 不太行。

## 更轻的替代方案

### bore——Rust 写的极简隧道

```bash
# 安装
cargo install bore-cli
# 或 brew install bore-cli

# 使用
bore local 3000 --to bore.pub
# bore.pub:12345 → localhost:3000
```

Rust 实现，二进制极小。`bore.pub` 是公共服务器，也是 MIT 开源的——你可以自己搭服务器。

### localhost.run——纯 SSH

```bash
ssh -R 80:localhost:3000 nokey@localhost.run
# https://xxxxxx.localhost.run → localhost:3000
```

不需要安装任何东西——只要你有 `ssh` 客户端。SSH 反向隧道 + 一个公网中转服务器。最轻的方案，也是最少功能的方案。

### serveo——SSH 方案，支持自定义域名

```bash
# 随机子域名
ssh -R 80:localhost:3000 serveo.net
# https://abc.serveo.net → localhost:3000

# 自定义子域名
ssh -R myapp:80:localhost:3000 serveo.net
# https://myapp.serveo.net → localhost:3000

# 用自己的域名——在 DNS 里加 TXT 记录验证所有权后
ssh -R yourdomain.com:80:localhost:3000 serveo.net
# https://yourdomain.com → localhost:3000
```

不需要安装任何客户端——只有 SSH。但稳定性不如 ngrok 和 Cloudflare Tunnel——serveo 是公益项目，服务器偶尔不可用。

### zrok——开源 + 自带 sharing 功能

```bash
brew install zrok
zrok enable     # 注册免费账号
zrok share public localhost:3000
```

zrok 比 localtunnel 多了分享管理能力——创建、分享、撤销 reserved share。开源（Apache 2.0），可以自己托管后端。

## 四款工具对比

| | ngrok | Cloudflare Tunnel | localtunnel | bore | localhost.run |
|---|---|---|---|---|---|
| 安装 | brew | brew | npm | cargo/brew | **不需要** |
| 注册 | ✅ 需要 | Cloudflare 账号 | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| 固定域名 | 付费 | ✅ 免费 | ❌ 随机 | ❌ 随机 | ❌ 随机 |
| HTTPS | ✅ 自动 | ✅ 自动 | ⚠️ 浏览器报警告 | ❌ 无 | ✅ 自动 |
| TCP 隧道 | ✅ | ❌ | ❌ | ✅ | ✅ |
| Inspector | ✅ | ❌ | ❌ | ❌ | ❌ |
| 访问控制 | Basic Auth | Cloudflare Access | ❌ | ❌ | ❌ |
| 开源 | agent 开源 | Apache 2.0 | MIT | MIT | ❌ |
| 自建服务器 | ❌ | ❌ | ✅ | ✅ | ❌ |
| 适合场景 | 全套体验 | 已有 CF 域名 | 临时测试 | 极简主义者 | 啥都不想装 |

## 选型指南

三步决策：

```
你要什么？
├── 最好的体验 → ngrok
│   有 Inspector、Replay、固定域名——全套工具链
│   缺点：固定域名要付费
│
├── 有域名托管在 Cloudflare → Cloudflare Tunnel
│   零成本固定域名、SSO 级别访问控制
│   缺点：没有 Inspector、不支持 TCP
│
├── 不想注册任何账号
│   ├── 有 npm → localtunnel（最简单）
│   ├── 有 cargo → bore（最轻）
│   └── 只有 ssh → localhost.run（零安装）
│
└── 需要自己掌控基础设施
    ├── 搭 bore server（Rust 实现）
    ├── 搭 localtunnel server（Node.js 实现）
    └── SSH 反向隧道 + nginx 反代
```

## 系列总结

三篇覆盖了从最强大的到最轻量的内网穿透方案：

```
ngrok              → 要体验最好的 → 用它
Cloudflare Tunnel  → 有 CF 域名 → 用它
localtunnel        → 不想注册 → 用它
localhost.run      → 啥都不想装 → 用它
```

核心选择其实就一个：**你愿不愿意注册一个账号？** 愿意 → ngrok。不愿意 → localtunnel。有 Cloudflare 域名 → Cloudflare Tunnel。啥都不想装 → `ssh -R`。

→ [回到系列导航](index.md)
