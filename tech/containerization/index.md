# 容器化系列

从单机容器到集群编排的完整演进路线。每篇可以独立阅读，但建议按顺序来——每一篇的痛点都是下一篇存在的原因。

## 阅读顺序

1. **[Docker 核心：不止是「跑个容器」](docker-core.md)** — 2026-05-30
   - 容器 ≠ 轻量级虚拟机，理解 namespace + cgroups + 分层文件系统
   - 把 Python 应用容器化的完整实操
   - 网络原理：bridge 模式、内置 DNS、端口映射

2. **[Docker Compose：从单容器到多容器协作](docker-compose.md)** — 2026-05-30
   - 多容器服务栈的声明式编排、healthcheck 正确用法、环境变量设计

3. **[Kubernetes 入门：当「单机」不够用的时候](kubernetes-intro.md)** — 2026-05-30
   - 从 Compose 的三个致命短板出发，理解 Pod/Service/Deployment 核心抽象
   - 实战：把 Compose 栈翻译成 K8s 资源 + 体验滚动更新

4. **[从 Compose 到 K8s 的思维切换](compose-to-k8s.md)** — 2026-05-30
   - 过程式 vs 声明式、网络模型对比、配置管理对比、什么时候用哪个的决策框架

5. **[Helm：Kubernetes 的包管理器](helm.md)** — 2026-05-30
   - K8s YAML 碎片化的解法、Chart 模板化、多环境管理、helm rollback 的版本控制能力
