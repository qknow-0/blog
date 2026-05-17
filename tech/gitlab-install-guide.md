# GitLab 自托管安装：一台 Ubuntu 服务器，十分钟上线

读完这篇文章你会得到：一个带 HTTPS 的私有 GitLab 实例，自动备份到远程服务器，能发邮件通知。

环境是 Ubuntu 22.04，4GB 内存。如果你手边是一台刚装好系统的 VPS，跟着走就行。

## 装上去

先装依赖，然后一行脚本加仓库，一行命令安装：

```bash
sudo apt update
sudo apt install -y curl openssh-server ca-certificates tzdata perl

curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo apt install -y gitlab-ce
```

告诉 GitLab 你的域名：

```bash
sudo sed -i "s|^external_url .*|external_url 'https://git.example.com'|" /etc/gitlab/gitlab.rb
```

启动。这一步初始化数据库、Nginx、Redis、PostgreSQL 全套内建服务，等 3-5 分钟：

```bash
sudo gitlab-ctl reconfigure
```

取 root 密码，拿它登录，然后第一时间改掉：

```bash
sudo cat /etc/gitlab/initial_root_password
```

到这里 GitLab 已经跑起来了。访问 `https://git.example.com`。

## 加上 HTTPS

GitLab 内建 Let's Encrypt，两行配置：

```bash
sudo tee -a /etc/gitlab/gitlab.rb << 'EOF'
letsencrypt['enable'] = true
letsencrypt['contact_emails'] = ['admin@example.com']
letsencrypt['auto_renew'] = true
EOF

sudo gitlab-ctl reconfigure
```

如果你在前面挂了一层 Nginx 反向代理，关掉内置 HTTPS：

```bash
sudo sed -i "s|^# nginx\['listen_https'\] .*|nginx['listen_https'] = false|" /etc/gitlab/gitlab.rb
sudo gitlab-ctl reconfigure
```

## Docker 尝鲜

不想折腾服务器环境的话：

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

## 接上邮件

GitLab 内置了 SMTP 支持。在 `/etc/gitlab/gitlab.rb` 末尾加上：

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

`reconfigure` 完就能收通知邮件了——注册确认、密码重置、CI 失败提醒。

## 备份这件事

一条命令出备份，一条 cron 搞定自动化：

```bash
# 手动备份
sudo gitlab-backup create

# 每天凌晨 2 点自动备份
echo '0 2 * * * /usr/bin/gitlab-backup create CRON=1' | sudo crontab -
```

备份文件在 `/var/opt/gitlab/backups/`。扔在本地没意义，rsync 推走：

```bash
rsync -avz /var/opt/gitlab/backups/ user@backup-server:/backups/gitlab/
```

恢复的时候指定备份时间戳：

```bash
sudo gitlab-backup restore BACKUP=1737062400_2026_01_17_17.5.0
```

## 日常会用到的操作

```bash
sudo gitlab-ctl status         # 看各服务状态
sudo gitlab-ctl restart        # 重启
sudo gitlab-ctl tail            # 实时日志
sudo gitlab-ctl reconfigure     # 改完配置后生效
```

升级就两条命令，但有一条铁律——**大版本不能跳**。16.x → 17.x 必须中间过一遍 16 最后一个版本：

```bash
sudo apt update && sudo apt install -y gitlab-ce
sudo gitlab-ctl reconfigure
```

## 三个关键点

1. 所有配置都通过 `/etc/gitlab/gitlab.rb` + `reconfigure`，不要直接改 Nginx 或 PostgreSQL 的配置文件——会被覆盖
2. 升级前先跑一次 `gitlab-backup create`，反正就一条命令
3. 大版本升级按官方升级路径走：`16.x → 16.latest → 17.0 → 17.latest`

> 官方安装文档：[https://about.gitlab.com/install/](https://about.gitlab.com/install/)
> 升级路径：[https://docs.gitlab.com/ee/update/index.html#upgrade-paths](https://docs.gitlab.com/ee/update/index.html#upgrade-paths)
