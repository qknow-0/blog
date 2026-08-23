# autossh + PostgreSQL SSH 隧道：内网安全访问远程数据库

> 基于 Ubuntu 22.04/24.04 + PostgreSQL + autossh。适用于任何需要安全访问远程数据库的场景。

## 问题：直接暴露数据库端口是作死

远程 PostgreSQL 最常见的"方便做法"：

```
阿里云安全组 → 开放 5432/tcp → 直接连接
```

这等于把数据库裸奔在公网。扫描器几秒就能找到你的 5432 端口，暴力破解只是时间问题。

SSH 隧道的思路：**不开放 5432，只开放 22（SSH）**。通过 SSH 加密通道转发数据库连接——数据库对公网完全不可见。

```mermaid
flowchart LR
    subgraph 内网
        APP["应用服务"]
    end
    subgraph 隧道
        SSH["autossh<br/>SSH 加密通道"]
    end
    subgraph 香港ECS
        PG["PostgreSQL<br/>127.0.0.1:5432"]
    end

    APP -->|"127.0.0.1:15432"| SSH
    SSH -->|"SSH 加密"| PG
```

## 完整步骤

### Step 1：确认远程 PostgreSQL 绑定

在香港 ECS 上：

```bash
sudo ss -lntp | grep 5432
```

最好看到：

```
LISTEN 0 244 127.0.0.1:5432
```

确认 PG 只监听 localhost，不对公网开放。再测试连接：

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d your_database
```

### Step 2：阿里云安全组只开 SSH

| 协议 | 端口 | 来源 |
|---|---|---|
| TCP | 22 | 你的公网 IP/32（如果 IP 固定） |

**不要开放 5432。**

### Step 3：创建专用 SSH 用户

不要用 root 做隧道。在香港 ECS 上：

```bash
sudo adduser tunnel          # 一路回车
sudo vim /etc/ssh/sshd_config
```

确保：

```
AllowTcpForwarding yes
```

重启 SSH：

```bash
sudo systemctl restart ssh
```

### Step 4：生成 SSH Key

在内网机器上：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/pg_tunnel_ed25519
```

生成两个文件：

```
~/.ssh/pg_tunnel_ed25519       # 私钥
~/.ssh/pg_tunnel_ed25519.pub   # 公钥
```

### Step 5：部署公钥到香港 ECS

```bash
ssh-copy-id -i ~/.ssh/pg_tunnel_ed25519.pub tunnel@你的ECS公网IP
```

测试免密登录：

```bash
ssh -i ~/.ssh/pg_tunnel_ed25519 tunnel@你的ECS公网IP
```

能直接登录就说明 Key 没问题。`exit` 退出。

### Step 6：手动测试 SSH 隧道

```bash
ssh \
  -i ~/.ssh/pg_tunnel_ed25519 \
  -N \
  -L 15432:127.0.0.1:5432 \
  tunnel@你的ECS公网IP
```

`-N` 表示不开 shell，只做端口转发。终端会一直卡着——这是正常的。

它建立了：

```
内网机器 127.0.0.1:15432  →  SSH 加密  →  香港 ECS 127.0.0.1:5432 → PostgreSQL
```

**另开一个终端**测试：

```bash
psql -h 127.0.0.1 -p 15432 -U postgres -d your_database
```

能进入 `your_database=#` 说明隧道成功。`Ctrl+C` 关掉隧道终端。

### Step 7：配置 SSH Config

```bash
vim ~/.ssh/config
```

加入：

```
Host hk-pg
    HostName 你的ECS公网IP
    User tunnel
    IdentityFile ~/.ssh/pg_tunnel_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ExitOnForwardFailure yes
    StrictHostKeyChecking yes
    LocalForward 15432 127.0.0.1:5432
```

之后只需要 `ssh hk-pg` 就能建隧道。

### Step 8：安装 autossh

```bash
sudo apt update && sudo apt install -y autossh
autossh -V
```

`autossh` = SSH + 自动重连。SSH 断了自动重连，不需要你手动干预。

### Step 9：创建 systemd 服务（关键）

```bash
sudo vim /etc/systemd/system/pg-tunnel.service
```

内容：

```ini
[Unit]
Description=SSH Tunnel to Remote PostgreSQL
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=你的用户名

ExecStart=/usr/bin/autossh -M 0 -N hk-pg

Restart=always
RestartSec=5

Environment="AUTOSSH_GATETIME=0"

[Install]
WantedBy=multi-user.target
```

**参数解释：**

| 参数 | 含义 |
|---|---|
| `-M 0` | 禁用 autossh 的内置监控端口（用 systemd 的 Restart 代替） |
| `-N` | 不开 shell，只做端口转发 |
| `hk-pg` | SSH Config 里的 Host 别名 |
| `Restart=always` | 进程退出后自动重启 |
| `RestartSec=5` | 重启间隔 5 秒 |
| `AUTOSSH_GATETIME=0` | 首次连接失败也立即重试（默认要等 30 秒） |

### Step 10：启动

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pg-tunnel
systemctl status pg-tunnel
```

确认看到 `Active: active (running)`。

验证本地端口：

```bash
ss -lntp | grep 15432
# → 127.0.0.1:15432

psql -h 127.0.0.1 -p 15432 -U postgres -d your_database
# → your_database=#
```

### Step 11：测试自动重连

```bash
# 模拟网络断开
sudo systemctl restart NetworkManager

# 观察 autossh 自动重连
journalctl -u pg-tunnel -f
# 你会看到 SSH 断开，然后自动重新连接

# 恢复后验证
nc -zv 127.0.0.1 15432
# → Connection to 127.0.0.1 15432 port [tcp/*] succeeded!
```

### Step 12：应用连接

原来：

```
DATABASE_URL=postgresql://user:pass@香港ECS公网IP:5432/trading
```

现在：

```
DATABASE_URL=postgresql://user:pass@127.0.0.1:15432/trading
```

你的应用完全不知道中间存在 SSH 隧道。

## Docker 容器里怎么用

如果应用跑在 Docker 容器里，**容器里的 `127.0.0.1` 是容器自己，不是宿主机**。

```yaml
# docker-compose.yml
services:
  api:
    image: your-app
    extra_hosts:
      - "host.docker.internal:host-gateway"  # 关键：让容器能访问宿主机
    environment:
      DATABASE_URL: postgresql://user:pass@host.docker.internal:15432/trading
```

连接链路：

```
Docker 容器 → host.docker.internal:15432 → 宿主机 SSH 隧道 → 香港 ECS → PostgreSQL
```

## 常见问题

### 隧道建不起来

```bash
# 检查 SSH 连接
ssh -v hk-pg

# 检查 autossh 日志
journalctl -u pg-tunnel -n 50

# 检查远程 PG 是否在监听
ssh hk-pg "ss -lntp | grep 5432"
```

### 连接超时

通常是 `ServerAliveInterval` 没设置。SSH Config 里确认有：

```
ServerAliveInterval 30
ServerAliveCountMax 3
```

每 30 秒发一次心跳，3 次没响应就断开重连。

### 多个数据库隧道

SSH Config 里加多个 Host：

```
Host hk-pg-main
    LocalForward 15432 127.0.0.1:5432

Host hk-pg-replica
    LocalForward 15433 127.0.0.1:5433
```

对应两个 systemd 服务，分别监听 15432 和 15433。

## 小结

```bash
# 一条命令记住整个方案
autossh -M 0 -N hk-pg  # SSH + 自动重连 + 端口转发

# 关键原则
# 1. 数据库端口不对外暴露
# 2. 只开 SSH 端口（22）
# 3. autossh + systemd 保证隧道永远在线
# 4. 应用只连 127.0.0.1:15432，不知道中间有隧道
```

SSH 隧道不是"高级技巧"——是远程数据库访问的标准做法。比开放端口安全得多，比 VPN 轻量得多，比跳板机简单得多。
