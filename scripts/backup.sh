#!/bin/bash
# 坚果云 WebDAV 配置（首次使用请修改为你的账号信息）
# 坚果云 → 账户信息 → 安全选项 → 第三方应用管理 → 添加应用密码
WEBDAV_URL="https://dav.jianguoyun.com/dav/backups/blog"
WEBDAV_USER="your-email@example.com"
WEBDAV_PASS="your-app-password"

TIMESTAMP=$(date +%Y-%m-%d-%H%M)
ARCHIVE_NAME="blog-backup-${TIMESTAMP}.tar.gz"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BLOG_DIR="$(dirname "$SCRIPT_DIR")"
BLOG_NAME="$(basename "$BLOG_DIR")"

# 打包
cd "$(dirname "$BLOG_DIR")"
tar -czf "/tmp/${ARCHIVE_NAME}" \
  --exclude='.git' \
  --exclude='.claude' \
  --exclude='.DS_Store' \
  "$BLOG_NAME/"

# 上传到坚果云
curl -T "/tmp/${ARCHIVE_NAME}" \
  -u "${WEBDAV_USER}:${WEBDAV_PASS}" \
  "${WEBDAV_URL}/${ARCHIVE_NAME}"

# 清理
rm -f "/tmp/${ARCHIVE_NAME}"
echo "备份完成"
