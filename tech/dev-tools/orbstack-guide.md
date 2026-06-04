# OrbStack：macOS 上最丝滑的 Docker 替代方案

> OrbStack 是 macOS 上跑 Docker 容器和 Linux 机器的三方 App——原生 Swift 编写、2 秒冷启动、菜单栏就能管理所有容器。如果你觉得 Docker Desktop 太重、Colima 缺 GUI，OrbStack 正好卡在两者之间。

## 一句话定位

OrbStack = Docker Desktop 的速度 + Colima 的轻量 + 一个菜单栏。

它不是开源软件（Colima 是 MIT），但个人免费使用。如果你愿意用一个闭源但体验极好的工具来换回每天省下的几分钟等待时间，它就值得。

## 安装与迁移

```bash
brew install orbstack
# 或从 orbstack.dev 下载 .dmg
```

首次打开时会问要不要从 Docker Desktop 迁移——**点一下就行**。OrbStack 会自动：

1. 导入所有 Docker 镜像和容器
2. 迁移 Docker volumes 数据
3. 切换 `docker context` 到 orbstack
4. 迁移 Compose 项目

迁移完成后 Docker Desktop 就可以卸载了：

```bash
# OrbStack 里一键卸载 Docker Desktop
# 菜单栏 → OrbStack → Troubleshooting → Uninstall Docker Desktop
```

整个过程 2-3 分钟，不需要手动 `docker save/load`。

## 速度从哪来

OrbStack 不跑完整的 Linux 虚拟机。它在 macOS 上用一个**轻量级虚拟化层**来共享宿主内核资源：

```
Docker Desktop:
  macOS → HyperKit VM → Linux → dockerd → 容器
  冷启动：30-60 秒

Colima:
  macOS → Lima VM (Alpine) → dockerd → 容器
  冷启动：10-15 秒

OrbStack:
  macOS → 轻量虚拟化层 → dockerd → 容器
  冷启动：2 秒
```

它的虚拟化层做了几件关键优化：

- **文件共享**：不用 virtio-9p（慢），不用 virtiofs（需要 VM 内核支持），而是自研的文件系统层。`npm install` 在 bind mount 目录里跑，速度接近原生 macOS 文件系统
- **Rosetta 加速**：在 Apple Silicon 上跑 x86 容器时自动启用 Rosetta 2 二进制翻译，不需要额外配置
- **内存共享**：多个容器之间共享内核页面缓存，不是每个 VM 各自分一块独立内存
- **原生网络**：容器端口直接暴露在 macOS 网卡上，不走虚拟机 NAT 桥接

官方 Benchmarks 数据（vs Docker Desktop）：

| 操作 | Docker Desktop | OrbStack | 提升 |
|------|---------------|----------|------|
| 冷启动 | ~45s | ~2s | 22x |
| `npm install` (bind mount) | ~120s | ~12s | 10x |
| CPU 空闲占用 | ~4% | ~0.1% | 40x |
| 内存占用（空跑） | ~2GB | ~200MB | 10x |
| 磁盘占用 | ~8GB | ~500MB | 16x |
| 电池续航影响 | 明显 | 几乎无 | — |

## 自动域名

OrbStack 最让人上瘾的功能——**每个容器自动分配一个 `*.orbstack.local` 域名**：

```bash
docker run -d --name myapp -p 3000:3000 node:20 node server.js

# 不需要记端口号
curl http://myapp.orbstack.local
# → 自动代理到容器的 3000 端口
```

容器名就是域名。多个端口的话加端口后缀：

```bash
# 容器暴露了 3000 和 8080
curl http://myapp.orbstack.local          # → 3000（默认第一个端口）
curl http://myapp-p3000.orbstack.local    # → 指定端口
curl http://myapp-p8080.orbstack.local    # → 指定端口
```

不需要配 `/etc/hosts`，不需要记端口映射。团队协作时发 `http://myapp.orbstack.local` 给同事就行——前提是对方也装了 OrbStack。

## 菜单栏操作

```
菜单栏图标 → 点开
├── Containers (5)
│   ├── myapp (running)      ← 点一下看日志
│   ├── postgres (running)
│   ├── redis (running)
│   └── nginx (stopped)
├── Linux Machines (1)
│   └── ubuntu-dev
├── Docker
│   ├── Open Dashboard
│   ├── Pause Docker         ← 临时冻结所有容器，释放 CPU
│   └── Restart Docker
└── Settings...
```

Docker Desktop 的 Dashboard 功能——查看容器状态、日志、终端——OrbStack 从菜单栏就能完成。不需要打开一个 Electron 窗口等它加载。

**Pause Docker** 是一个很实用的功能——临停所有容器，CPU 和内存释放，电池不再消耗。切回工作再 Resume，所有容器还原，状态不丢。比 `docker stop $(docker ps -q)` 优雅得多。

## Docker Compose 集成

```bash
# 和平时完全一样
docker compose up -d

# OrbStack 会自动检测 compose 项目
# 菜单栏里把它归到一个组里
```

OrbStack 不需要自己的 Compose 实现——它完全兼容标准的 Docker Compose。它只是多了个自动发现机制：检测到 `compose.yaml`/`docker-compose.yml`，在菜单栏里把同一个 compose 项目的容器折叠成一个组。

## Linux 机器

除了跑容器，OrbStack 还能跑完整的 Linux 虚拟机——不是容器，是真正的 VM：

```bash
# 创建一个 Ubuntu VM
orb create ubuntu ubuntu-dev

# 列出所有 VM
orb list

# SSH 进去
orb ssh ubuntu-dev
# 或者直接
ssh orbstack@ubuntu-dev.orbstack.local

# 删除
orb delete ubuntu-dev
```

预置的镜像包括 Ubuntu、Debian、Fedora、Arch、Alpine 等：

```bash
orb create ubuntu my-ubuntu
orb create debian my-debian
orb create fedora my-fedora
orb create arch my-arch
```

机器之间共用 OrbStack 的内核优化层——文件共享、网络、Rosetta 加速对 Linux 机器同样适用。可以在同一个网络里让容器和 VM 互相通信。

使用场景：

- 需要一个完整的 Linux 开发环境（不只是单容器）
- 测试多机网络拓扑
- 跑 systemd-nspawn / snap 等依赖完整 systemd 的服务
- 需要和 macOS 文件系统共享文件但又要完整 Linux 环境

## Kubernetes

```bash
# 菜单栏 → Kubernetes → Enable
kubectl get nodes
# NAME        STATUS   ROLES         AGE   VERSION
# orbstack    Ready    control-plane 10s   v1.30.2
```

OrbStack 内建 K3s，切换 Kubernetes 开关就行。和 Colima 的 K8s 支持类似，但 OrbStack 在菜单栏里提供了可视化状态和启停开关。

## Colima 篇 vs OrbStack

写这两篇不是要让它们对决——学完 Colima 后了解 OrbStack，选最适合自己的就行：

| | Colima | OrbStack |
|---|---|---|
| 许可证 | MIT 开源 | 个人免费，商业需授权 |
| 安装 | `brew install colima` | `brew install orbstack` |
| 冷启动 | ~15s | ~2s |
| GUI | 无 | 菜单栏 + 托盘 |
| 自动域名 | 无 | `*.orbstack.local` |
| 文件共享性能 | virtio-9p（一般） | 自研层（接近原生） |
| Linux VM | ❌（有 Incus） | ✅ `orb create` |
| Docker Desktop 迁移 | 手动 | ✅ 一键 |
| Kubernetes | K3s | K3s |
| GPU/AI | ✅ krunkit | ❌ |
| 社区支持 | GitHub Discussions | GitHub Issues + Email |

**选 Colima**：你是开源信仰者、需要 GPU 加速、喜欢纯命令行
**选 OrbStack**：你要丝滑体验、在意文件共享性能、需要 Linux VM、不想折腾配置

两者可以在同一台 Mac 上共存——通过 Docker Context 切换：

```bash
docker context use colima      # 用 Colima
docker context use orbstack    # 用 OrbStack
```

## 常用命令速查

```bash
# ---------- OrbStack 专用 ----------
orb list                          # 所有 Linux 机器
orb create ubuntu my-ubuntu       # 创建 Ubuntu VM
orb ssh my-ubuntu                 # SSH 进 VM
orb delete my-ubuntu              # 删除 VM
orb config                        # 查看当前配置
orb restart docker                # 重启 Docker 引擎

# ---------- Docker（和平时完全一样）---------
docker ps
docker compose up -d
docker build -t myapp .

# ---------- 服务发现 ----------
curl http://myapp.orbstack.local           # 容器自动域名
curl http://myapp-p8080.orbstack.local     # 指定端口
ssh orbstack@my-ubuntu.orbstack.local      # SSH 进 VM

# ---------- 菜单栏 ----------
# Pause Docker：    临时冻结所有容器
# Restart Docker：  重启 Docker 引擎（不重启容器）
# Open Dashboard：  打开 Web Dashboard
```

## 常见问题

**Docker Compose 的 depends_on 和 healthcheck 能正常工作吗？**

完全可以。OrbStack 不修改 Compose 的行为——它只是提供了一个更快的 Docker 运行时。

**和 Docker Desktop 的 docker-compose 版本有什么区别？**

OrbStack 用你系统里的 Docker CLI 和 Docker Compose——`brew install docker docker-compose` 装的就行。不捆绑自己的版本。

**免费吗？**

个人和开源项目免费。商业用途需要购买 license。具体见 [orbstack.dev](https://orbstack.dev)。

**支持 Intel Mac 吗？**

支持。但 Rosetta 加速和 AI 功能只在 Apple Silicon 上可用。

## 总结

OrbStack 做的事情就是让 macOS 上的容器开发**感觉快**。启动快、文件操作快、域名访问方便、菜单栏管理省事。它不是功能最多的（Colima 有 GPU），也不是最开放的（闭源），但日常开发体验是最好的——每天少等几十次启动时间，一年下来很可观。

和前两篇形成完整的 macOS 容器三篇曲：

- Colima：纯命令行，开源，适合极简主义
- OrbStack：菜单栏 GUI + 命令行，个人免费，适合效率优先
- systemd/launchd：理解两个 OS 的服务管理底色
