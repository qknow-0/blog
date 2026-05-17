# GitLab 自托管安装指南：从零搭建私有代码仓库

GitLab 是目前最流行的自托管 Git 平台，支持代码管理、CI/CD、容器镜像仓库、Wiki 等全套 DevOps 功能。本文记录在 Linux 服务器上从零安装 GitLab CE（社区版）的完整流程。

## 选择安装方式

GitLab 提供三种主流安装方式：

| 方式 | 适用场景 | 复杂度 |
|------|---------|:---:|
| Linux 包（Omnibus） | 单机部署，推荐方式 | 低 |
| Docker 容器 | 快速尝鲜、开发环境 | 低 |
| Helm（Kubernetes） | 生产集群 | 高 |

本文使用 **Omnibus 包安装**，适合大多数场景。

## 环境要求

- **操作系统**：Ubuntu 22.04 / Debian 12 / RHEL 9
- **内存**：最低 4GB，推荐 8GB+
- **CPU**：2 核以上
- **存储**：20GB+（代码量和 CI 产物决定）
- **域名**：一个指向服务器的域名（如 `git.example.com`）

以下以 **Ubuntu 22.04** 为例。

## 安装步骤

### 1. 安装依赖

```bash
sudo apt update
sudo apt install -y curl openssh-server ca-certificates tzdata perl
```

### 2. 添加 GitLab 仓库并安装

```bash
curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo apt install -y gitlab-ce
```

### 3. 配置外部访问地址

```bash
sudo sed -i "s|^external_url .*|external_url 'https://git.example.com'|" /etc/gitlab/gitlab.rb
```

### 4. 启动并初始化

```bash
sudo gitlab-ctl reconfigure
```

首次启动需要 3-5 分钟。完成后访问 `https://git.example.com`。

### 5. 获取初始 root 密码

```bash
sudo cat /etc/gitlab/initial_root_password
```

用 `root` 和这个密码登录，进入后第一时间修改密码。

## HTTPS 配置

GitLab 会自动申请 Let's Encrypt 证书：

```bash
# 在 /etc/gitlab/gitlab.rb 中添加
sudo tee -a /etc/gitlab/gitlab.rb << 'EOF'
letsencrypt['enable'] = true
letsencrypt['contact_emails'] = ['admin@example.com']
letsencrypt['auto_renew'] = true
EOF

sudo gitlab-ctl reconfigure
```

如果已经手动配置了 Nginx 反向代理，需要关闭内置 HTTPS：

```bash
sudo sed -i "s|^# nginx\['listen_https'\] .*|nginx['listen_https'] = false|" /etc/gitlab/gitlab.rb
sudo gitlab-ctl reconfigure
```

## Docker 快速安装（备选）

如果只是快速体验：

```bash
sudo docker run --detach \
  --hostname git.example.com \
  --publish 443:443 --publish 80:80 --publish 2222:22 \
  --name gitlab \
  --restart always \
  --volume $GITLAB_HOME/config:/etc/gitlab \
  --volume $GITLAB_HOME/logs:/var/log/gitlab \
  --volume $GITLAB_HOME/data:/var/opt/gitlab \
  gitlab/gitlab-ce:latest
```

## 日常运维命令

```bash
# 查看服务状态
sudo gitlab-ctl status

# 重启
sudo gitlab-ctl restart

# 查看日志
sudo gitlab-ctl tail

# 备份（包含数据库和仓库）
sudo gitlab-backup create

# 恢复
sudo gitlab-backup restore BACKUP=1737062400_2026_01_17_17.5.0

# 升级到最新版
sudo apt update && sudo apt install -y gitlab-ce
sudo gitlab-ctl reconfigure
```

## 备份策略

```bash
# 定时任务：每天凌晨 2 点备份
echo '0 2 * * * /usr/bin/gitlab-backup create CRON=1' | sudo crontab -
```

备份文件默认位于 `/var/opt/gitlab/backups/`，建议同步到远程存储：

```bash
# 在备份脚本中追加
rsync -avz /var/opt/gitlab/backups/ user@backup-server:/backups/gitlab/
```

## 配置 SMTP 邮件

让 GitLab 能发通知邮件：

```bash
sudo tee -a /etc/gitlab/gitlab.rb << 'EOF'
gitlab_rails['smtp_enable'] = true
gitlab_rails['smtp_address'] = "smtp.example.com"
gitlab_rails['smtp_port'] = 587
gitlab_rails['smtp_user_name'] = "noreply@example.com"
gitlab_rails['smtp_password'] = "your-smtp-password"
gitlab_rails['smtp_domain'] = "example.com"
gitlab_rails['smtp_authentication'] = "login"
gitlab_rails['smtp_enable_starttls_auto'] = true
EOF

sudo gitlab-ctl reconfigure
```

## 升级注意事项

1. 升级前**先备份**
2. 大版本跨越时（如 16.x → 17.x），必须**逐个大版本升级**，不能跳
3. 参考官方 [升级路径](https://docs.gitlab.com/ee/update/index.html#upgrade-paths)

## 总结

用 Omnibus 安装 GitLab，十分钟就能有一个功能完整的私有 Git 平台。关键点：

1. 用 `gitlab-ctl reconfigure` 而不是手动改配置文件
2. 配置好 HTTPS 和自动备份
3. 升级前一定备份，大版本逐级升

> 官方安装文档：[https://about.gitlab.com/install/](https://about.gitlab.com/install/)
