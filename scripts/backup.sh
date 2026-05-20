#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BLOG_DIR="$(dirname "$SCRIPT_DIR")"

# 从 .env 读取配置
if [ -f "$BLOG_DIR/.env" ]; then
  set -a
  source "$BLOG_DIR/.env"
  set +a
else
  echo "错误: 未找到 $BLOG_DIR/.env 文件"
  echo "请复制 .env.example 为 .env 并填入你的坚果云凭据"
  exit 1
fi

WEBDAV_URL="${WEBDAV_URL:-https://dav.jianguoyun.com/dav/backups/blog}"

TIMESTAMP=$(date +%Y-%m-%d-%H%M)
ARCHIVE_NAME="blog-backup-${TIMESTAMP}.tar.gz"
BLOG_NAME="$(basename "$BLOG_DIR")"

# 打包
cd "$(dirname "$BLOG_DIR")"
tar -czf "/tmp/${ARCHIVE_NAME}" \
  --exclude='.git' \
  --exclude='.claude' \
  --exclude='.DS_Store' \
  --exclude='source-read/Sequoia-X' \
  "$BLOG_NAME/"

# 上传到坚果云
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -T "/tmp/${ARCHIVE_NAME}" \
  -u "${WEBDAV_USER}:${WEBDAV_PASS}" \
  "${WEBDAV_URL}/${ARCHIVE_NAME}")

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "204" ]; then
  echo "上传成功 (HTTP ${HTTP_CODE})"
else
  echo "上传失败 (HTTP ${HTTP_CODE})"
  exit 1
fi

# 清理
rm -f "/tmp/${ARCHIVE_NAME}"
echo "备份完成"
