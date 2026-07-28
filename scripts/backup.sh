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
  --exclude='.AppleDouble' \
  --exclude='.LSOverride' \
  --exclude='.vscode' \
  --exclude='.idea' \
  --exclude='*.swp' \
  --exclude='*.swo' \
  --exclude='.env' \
  --exclude='._*' \
  --exclude='source-read/Sequoia-X' \
  --exclude='source-read/FinnewsHunter' \
  --exclude='source-read/QuantDinger' \
  --exclude='source-read/daily-stock-analysis' \
  --exclude='source-read/TrendRadar' \
  --exclude='source-read/newsnow' \
  --exclude='source-read/nanobot' \
  --exclude='source-read/MetaGPT' \
  --exclude='source-read/dbx' \
  --exclude='source-read/horizon' \
  --exclude='source-read/ai-hedge-fund' \
  --exclude='source-read/worldmonitor' \
  --exclude='source-read/impeccable' \
  --exclude='code/mini-gpt/mini-gpt-cn.pt' \
  --exclude='code/mini-gpt/.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$BLOG_NAME/"

# 检查压缩包大小——超过 20MB 可能打包了不需要的文件
ARCHIVE_SIZE=$(stat -f%z "/tmp/${ARCHIVE_NAME}" 2>/dev/null || stat -c%s "/tmp/${ARCHIVE_NAME}" 2>/dev/null)
ARCHIVE_SIZE_MB=$((ARCHIVE_SIZE / 1024 / 1024))
if [ "$ARCHIVE_SIZE_MB" -gt 20 ]; then
  echo "❌ 错误：压缩包大小 ${ARCHIVE_SIZE_MB}MB（超过 20MB），可能打包了不需要的文件"
  echo "   已取消上传。请检查 .gitignore 和 backup.sh 的 --exclude 列表是否同步"
  echo "   当前排除：source-read/（11个）, code/mini-gpt/*.pt, __pycache__, .env 等"
  rm -f "/tmp/${ARCHIVE_NAME}"
  exit 1
fi

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

# 清理远程旧备份：只保留最近 5 份
REMOTE_LIST=$(curl -s -X PROPFIND -u "${WEBDAV_USER}:${WEBDAV_PASS}" \
  -H "Depth: 1" \
  "${WEBDAV_URL}/" 2>/dev/null | \
  grep -o 'blog-backup-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-[0-9]\{4\}\.tar\.gz' | \
  sort -u -r | tail -n +6)

if [ -n "$REMOTE_LIST" ]; then
  echo "清理旧备份..."
  echo "$REMOTE_LIST" | while read -r OLD_FILE; do
    echo "  删除远程: $OLD_FILE"
    curl -s -o /dev/null -X DELETE \
      -u "${WEBDAV_USER}:${WEBDAV_PASS}" \
      "${WEBDAV_URL}/${OLD_FILE}"
  done
  echo "旧备份清理完成"
fi

# 清理本地临时文件
rm -f "/tmp/${ARCHIVE_NAME}"
echo "备份完成"
