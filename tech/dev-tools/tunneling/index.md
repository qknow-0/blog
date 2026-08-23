# 内网穿透系列

把 `localhost` 暴露到公网的三种方案——从功能最全的 ngrok 到最轻量的 localtunnel。

## 阅读顺序

1. **[（一）ngrok：把 localhost 暴露到公网的最快方式](01-ngrok.md)** — 2026-06-06
   - Inspector、Replay、固定域名、Basic Auth、配置文件

2. **[（二）Cloudflare Tunnel：零成本的公网隧道方案](02-cloudflare-tunnel.md)** — 2026-06-06
   - 永久固定域名、Cloudflare Access SSO、临时 trycloudflare.com 域名

3. **[（三）localtunnel 与轻量替代方案](03-localtunnel.md)** — 2026-06-06
   - localtunnel、bore、localhost.run、serveo——零注册方案 + 最终选型指南

4. **[（四）Orbien：Rust 写的自托管内网穿透，5MB 的 frp 替代品](04-orbien.md)** — 2026-08-23
   - 自托管架构、TCP/UDP/HTTP/HTTPS 隧道、TLS/mTLS、四种传输协议、桌面客户端
