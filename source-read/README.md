# 源码阅读规范

每个源码阅读项目遵循以下步骤：

1. **Clone 源码** — 将项目源码 clone 到本目录下（保持原始仓库名）
   ```bash
   cd source-read && git clone <repo-url>
   ```
   例如 clone 后得到 `source-read/QuantDinger/`

2. **新建笔记文件夹** — 使用 **snake_case** 命名，避免与 clone 的源码目录冲突
   ```bash
   mkdir source-read/quant_dinger/
   ```
   > ⚠️ macOS 文件系统默认不区分大小写。如果源码目录是 `QuantDinger`，笔记文件夹用 `quant_dinger`，.gitignore 只排除源码目录名 `QuantDinger`——笔记不会被误排除。

3. **排除源码提交** — 在 `.gitignore` 中添加 clone 的源码目录（原始仓库名）
   ```
   source-read/QuantDinger
   ```

4. **排除源码备份** — 在 `scripts/backup.sh` 的 `--exclude` 列表中同步添加
   ```
   --exclude='source-read/QuantDinger'
   ```

## 示例：新增一个源码阅读项目

```bash
# 1. clone 源码
cd source-read && git clone https://github.com/user/MyProject.git

# 2. 新建笔记文件夹（snake_case）
mkdir source-read/my_project/

# 3. 在 .gitignore 中添加
echo "source-read/MyProject" >> ../.gitignore

# 4. 在 scripts/backup.sh 的 --exclude 列表中添加
# --exclude='source-read/MyProject'
```

## 当前已排除的源码目录

| 源码目录（被排除） | 笔记文件夹 | .gitignore | backup.sh |
|-------------------|-----------|-----------|-----------|
| Sequoia-X | sequoia_x/ | ✅ | ✅ |
| FinnewsHunter | finnews_hunter/ | ✅ | ✅ |
| QuantDinger | quant_dinger/ | ✅ | ✅ |
| daily-stock-analysis | daily_stock_analysis/ | ✅ | ✅ |
