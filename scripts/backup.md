# 备份脚本说明

将 blog 知识库打包上传到坚果云 WebDAV，作为 Git + GitHub 之外的额外备份。

## 依赖

- `curl` — 系统自带
- `tar` — 系统自带
- 坚果云账号（需开启 WebDAV 功能）

## 首次配置

1. 登录坚果云 → 账户信息 → 安全选项 → 第三方应用管理 → 添加应用密码
2. 复制 `.env.example` 为 `.env`
3. 填入账号邮箱和应用密码

```bash
cp .env.example .env
# 编辑 .env，修改 WEBDAV_USER 和 WEBDAV_PASS
```

## 使用

```bash
./scripts/backup.sh
```

备份文件会以 `blog-backup-YYYY-MM-DD-HHMM.tar.gz` 格式保存到坚果云 `backups/blog/` 目录下。

## 排除规则

打包时排除以下内容：
- `.git/` — 版本历史（已有 GitHub 备份）
- `.claude/` — Claude Code 本地配置
- `.DS_Store` — macOS 系统文件
- `source-read/Sequoia-X` — 项目源码排除
