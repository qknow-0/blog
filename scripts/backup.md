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

> ⚠️ **`WEBDAV_PASS` 必须填应用密码，不能填账号登录密码。**
> 应用密码是 **16 位**字符串；填成登录密码（10~12 位）会返回 **HTTP 401**，且不给出任何错误说明。

## 使用

```bash
./scripts/backup.sh
```

备份文件会以 `blog-backup-YYYY-MM-DD-HHMM.tar.gz` 格式保存到坚果云 `backups/blog/` 目录下。

脚本行为：

- 打包 → 大小检查 → 上传 → 清理远程旧备份
- 远程**只保留最近 5 份**，第 6 份起自动删除
- 临时包在脚本退出时清理（`trap ... EXIT`，成功/失败/Ctrl-C 都覆盖）

## 排查 401

401 只表示「凭据没被接受」，不含更多信息。用这组对比快速定位——**看带凭据和不带凭据的状态码是否相同**：

```bash
bash -c 'set -a; source ./.env; set +a
echo -n "不带凭据: "; curl -s -o /dev/null -w "%{http_code}\n" -X PROPFIND -H "Depth: 0" "$WEBDAV_URL/"
echo -n "带凭据:   "; curl -s -o /dev/null -w "%{http_code}\n" -X PROPFIND -H "Depth: 0" -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL/"
echo "密码长度: ${#WEBDAV_PASS}"'
```

| 结果 | 含义 |
|------|------|
| 两个都是 401 | 凭据被拒 → 检查密码是否是 16 位应用密码 |
| 带凭据返回 **207** | 凭据正常，问题在别处 |
| 带凭据返回 409 | 凭据正常，但目标目录不存在 |

## 排除规则

打包时排除以下内容。分类与 `.gitignore` 对应——**`.gitignore` 新增条目时要同步到这里**（`tar --exclude` 不读 `.gitignore`）。

### 版本控制与本地配置

| 排除项 | 原因 |
|--------|------|
| `.git` | 版本历史，已有 GitHub 备份 |
| `.claude` | Claude Code 本地配置 |
| `.codegraph` | 索引数据库（192MB，是体积大头） |
| `.obsidian/themes` | 第三方主题（`.obsidian/` 本身纳入备份） |

### 凭据与系统文件

| 排除项 | 原因 |
|--------|------|
| `.env` | WebDAV 凭据 |
| `.DS_Store` `.AppleDouble` `.LSOverride` `._*` | macOS 系统文件与缩略图 |
| `.vscode` `.idea` `*.swp` `*.swo` | 编辑器配置与临时文件 |

### 源码与依赖（体积控制）

| 排除项 | 原因 |
|--------|------|
| `source-read/` 下 16 个项目目录 | 开源项目源码，可重新 clone；笔记另行保留 |
| `code/mini-gpt/mini-gpt-cn.pt` | 模型权重 |
| `code/mini-gpt/.venv` | 虚拟环境 |
| `__pycache__` `*.pyc` | Python 缓存 |

源码阅读的**笔记文件夹不在排除之列**（如 `Kun` 对应的 `kun_notes`），它们跟着备份走。

## 大小门限

压缩包超过 **20MB** 会中止上传并报错。这个门限是防「误打包大文件」的——历史上就是 `.codegraph/codegraph.db` 把包从 1.3MB 撑到 46MB，导致连续多日备份失败。

报错时的排查顺序：

```bash
# 列出包里最大的 20 个文件（-k5 是 size 列，tar -v 的第 5 个字段）
tar -tzvf /tmp/blog-backup-YYYY-MM-DD-HHMM.tar.gz | sort -k5 -n -r | head -20
```

（失败时临时包会被 `trap` 清掉，想事后分析可以先注释掉 `trap` 那行，或手动 `tar` 一遍。）

正常体积约 **1.3MB**。
