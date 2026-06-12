# 源码阅读规范

每个源码阅读项目遵循以下步骤：

1. **Clone 源码** — 将项目源码 clone 到本目录下
   ```bash
   cd source-read && git clone <repo-url> <项目名>
   ```
2. **新建笔记文件夹** — 创建同名文件夹存放阅读笔记
   ```bash
   mkdir source-read/<项目名>/
   ```
3. **排除源码提交** — 在 `.gitignore` 中添加 clone 的源码目录
   ```
   source-read/<项目名>
   ```
4. **排除源码备份** — 在 `scripts/backup.sh` 的 `--exclude` 列表中同步添加
   ```
   --exclude='source-read/<项目名>'
   ```

## 当前已排除的源码目录

| 项目 | .gitignore | backup.sh |
|------|-----------|-----------|
| Sequoia-X | ✅ | ✅ |
| FinnewsHunter | ✅ | ✅ |
| QuantDinger | ✅ | ✅ |
| daily-stock-analysis | ✅ | ✅ |
