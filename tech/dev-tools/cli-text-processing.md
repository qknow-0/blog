# awk、sed、grep 和其他六个：终端文本处理的九把刀

> 基于 POSIX 标准，示例在 macOS 和 Linux 下通用。

## 你会在这篇文章里学到什么

不是"每个命令的完整手册"——man 已经够好了。是从真实场景出发，讲清楚**什么场景用什么刀、怎么组合**。

每把刀一个"只用一次就回不去"的例子。

## 工具箱全景

| 工具 | 一句话 | 核心用途 |
|---|---|---|
| `grep` | 行过滤器 | 找包含某个模式的行 |
| `sed` | 流编辑器 | 查找替换、删除行 |
| `awk` | 列处理器 | 按列提取/计算/格式化 |
| `cut` | 切分器 | 按分隔符取列（比 awk 更轻） |
| `sort` | 排序器 | 排序、去重（-u） |
| `uniq` | 去重器 | 统计重复、去重 |
| `tr` | 字符翻译器 | 大小写转换、删除字符 |
| `xargs` | 参数构造器 | 把 stdin 变成命令参数 |
| `wc` | 计数器 | 行数、字数、字符数 |

## 1. grep — 找到了才能开始下一步

```bash
# 基本：找包含 "error" 的行
grep error app.log

# -i 忽略大小写
grep -i error app.log

# -v 反向匹配：排除匹配的行
grep -v DEBUG app.log

# -c 计数
grep -c ERROR app.log
# → 42

# -r 递归搜索目录
grep -r "panic" src/

# 组合技：日志里找 ERROR，只显示文件名
grep -rl ERROR /var/log/ | head
```

**只用一次就回不去：**

```bash
# 在 10 万行日志中找所有非 debug 行里的 ERROR，统计出现次数最多的 5 个
grep -v DEBUG app.log | grep ERROR | awk '{print $6}' | sort | uniq -c | sort -rn | head -5
```

## 2. sed — 替换、删除、提取，一行解决

```bash
# 替换（最常用）
sed 's/error/ERROR/g' app.log         # 所有 error → ERROR

# 删除匹配的行
sed '/DEBUG/d' app.log                 # 删掉所有 debug 行

# 只打印第 10-20 行
sed -n '10,20p' app.log

# 原地修改（-i）
sed -i '' 's/old-api/new-api/g' src/**/*.rs
```

**只用一次就回不去：**

```bash
# 批量删除所有 Python 文件中的 `debugger;` 注释行
sed -i '' '/debugger;/d' **/*.py
```

## 3. awk — 当数据有"列"的时候

awk 是 grep 做不到的那些事的答案：按列计算、按条件过滤、按格式输出。

```bash
# 打印第 2 列
awk '{print $2}' data.txt

# 第 3 列 > 100 的行
awk '$3 > 100' data.txt

# 带条件的格式化输出
awk '$3 > 100 {printf "%-20s %8d\n", $1, $3}' data.txt
```

**只用一次就回不去：**

```bash
# 分析 Nginx 日志：统计每个 IP 的请求数，取 top 10
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10

# 日志里按小时统计请求数（$4 是时间戳）
awk '{split($4, a, ":"); print a[2]}' access.log | sort | uniq -c
```

### awk 的 BEGIN/END 块 — 表格报告生成器

```bash
# 统计目录下所有 .log 文件的大小
ls -l *.log | awk '{sum += $5} END {printf "total: %.1f MB\n", sum/1024/1024}'

# 带表头的表格输出
ps aux | awk '
BEGIN { printf "%-8s %-20s %s\n", "PID", "COMMAND", "CPU%" }
$3 > 5 { printf "%-8s %-20s %.1f%%\n", $2, $11, $3 }
'
```

## 4. cut — 比 awk 更轻的列切分

```bash
# 取第 1 列和第 3 列（默认 tab 分隔）
cut -f1,3 data.tsv

# 逗号分隔
cut -d',' -f2,3 data.csv

# 取每行的第 5-15 个字符
cut -c5-15 data.txt
```

**只用一次就回不去：**

```bash
# 从 CSV 提取所有邮箱（第 3 列）
cut -d',' -f3 users.csv | grep '@'
```

## 5. sort — 不只是排序

```bash
# 排序
sort file.txt

# 逆序
sort -rn file.txt

# 按第 2 列数值排序
sort -k2 -n file.txt

# 去重（-u）
sort -u file.txt

# 以逗号分隔，按第 3 列排序
sort -t',' -k3 -n data.csv
```

**只用一次就回不去：**

```bash
# 找占用磁盘最大的 5 个文件
du -sh * | sort -rh | head -5
```

## 6. uniq — 统计重复

```bash
# 去重（需先排序）
sort file.txt | uniq

# 统计出现次数
sort file.txt | uniq -c

# 只显示重复的行
sort file.txt | uniq -d

# 只显示不重复的行
sort file.txt | uniq -u
```

## 7. tr — 字符级翻译

```bash
# 大写转小写
echo "HELLO" | tr 'A-Z' 'a-z'

# Windows 换行转 Unix
tr -d '\r' < dos.txt > unix.txt

# 多个空格合并为一个
tr -s ' ' < messy.txt
```

## 8. xargs — stdin 变命令行参数

```bash
# 删除所有 .tmp 文件
find . -name "*.tmp" | xargs rm

# 并行执行（-P）
find . -name "*.log" | xargs -P 4 gzip

# 配合 grep 找到的文件批量操作
grep -rl "TODO" src/**/*.rs | xargs sed -i '' 's/TODO/FIXME/g'
```

**只用一次就回不去：**

```bash
# 杀掉所有包含 "python server" 的进程
ps aux | grep "python server" | awk '{print $2}' | xargs kill
```

## 9. wc — 最简单的统计

```bash
wc -l file.txt     # 行数
wc -c file.txt     # 字节数
wc -w file.txt     # 单词数

# 目录下所有 Python 文件的总行数
wc -l **/*.py | tail -1
```

## 组合才是精髓：常见场景速查

| 场景 | 命令 |
|---|---|
| 日志中某 IP 的请求数 top 10 | `awk '{print $1}' access.log \| sort \| uniq -c \| sort -rn \| head -10` |
| CSV 第 3 列求和 | `awk -F',' '{sum+=$3} END {print sum}' data.csv` |
| 批量替换多文件中的字符串 | `grep -rl old api/ \| xargs sed -i 's/old/new/g'` |
| 统计代码库文件类型分布 | `find src -type f \| sed 's/.*\.//' \| sort \| uniq -c \| sort -rn` |
| 去空白行 + 去重复 | `grep -v '^$' file \| sort \| uniq` |
| 删除所有注释行 | `grep -v '^#' file` |
| 按进程占用内存排序 top 5 | `ps aux \| sort -k4 -rn \| head -5` |
| 实时 tail 日志，只显示 ERROR | `tail -f app.log \| grep ERROR` |

## 三个核心思维

**1. 一个命令只做一件事，管道是胶水。**

```
grep → 过滤行
sort → 排序
uniq → 去重统计
awk → 列处理
```

你不需要学 10 个工具的全部参数——每个工具你只需要它最擅长的那一个操作。

**2. 先用 grep 缩小范围，再做复杂处理。**

```bash
# ❌ awk 处理 100 万行
awk '/ERROR/ { ... }' huge.log

# ✅ 先 grep 缩小到 100 行，再 awk
grep ERROR huge.log | awk '{ ... }'
```

**3. awk 的默认行为就是"按空白列分隔 + print"——这覆盖了 80% 的场景。**

```bash
# 大部分时候你只需要
awk '{print $2, $1}' file    # 交换列
awk '$3 > 100' file          # 按条件过滤
awk '{sum += $1} END {print sum}' file  # 统计
```

## 小结

九把刀，按使用频率排序：

```
grep > awk > sed > sort > uniq > cut > xargs > tr > wc
```

不用记全部参数——记一个让你"回不去"的场景就够了。pipe（`|`）是 Unix 最好的发明——它让你可以像搭积木一样组合简单工具来解决复杂问题。
