# 源码阅读规范

每个源码阅读项目包含两类内容：**整体架构学习** + **具体优秀代码学习**。

## 一、整体架构学习

回答三个问题：

1. **怎么分模块**——画 Mermaid 流程图，标注模块之间的调用关系和数据流
2. **为什么这么分**——每个模块的职责边界在哪，解耦点在哪
3. **优缺点分析**——这个架构在什么场景下有效，什么场景下会崩

## 二、优秀代码学习

每篇至少拆解 **1-2 个可复用的具体代码片段**，每个片段包含：

- **源码摘录**——标注文件路径和行号，只保留核心逻辑
- **好在哪里**——命名？抽象？错误处理？边界条件？
- **用到了什么模式**——具体说出模式名（策略、状态机、观察者、管道等）
- **骨架代码**——去掉业务逻辑，留下可复用的代码结构

### Prompt 提取

如果源码中有 LLM 的 system prompt、task contract、tool description 等 prompt 模板，**单独写一篇 prompt 全集文章**。要求：

- 中英双语对照（原文 + 中文翻译）
- 标注每个 prompt 的用途、触发条件、所在文件路径
- 按功能分组（SQL 生成、错误修复、查询优化、对话总结等）

### 好的优秀代码学习长这样

```markdown
## 优秀代码：MessageBus 的两个 Queue 解耦

### 源码
```python
# nanobot/bus/queue.py:46-50
class MessageBus:
    def __init__(self):
        self.inbound = asyncio.Queue()
        self.outbound = asyncio.Queue()
```

### 好在哪
用两个 asyncio.Queue 替代了回调地狱。Channel 只管往里推消息，
AgentLoop 只管往外拿消息——互不知道对方存在。

### 模式
**Mediator 模式**：MessageBus 是中介者，Channel 和 AgentLoop 不直接通信。

### 骨架代码（你敢直接用）
```python
import asyncio

class MessageBus:
    def __init__(self):
        self._in = asyncio.Queue()
        self._out = asyncio.Queue()
    
    async def send(self, msg): await self._in.put(msg)
    async def receive(self): return await self._in.get()
    async def reply(self, msg): await self._out.put(msg)

# 你的项目中：用两个 Queue 解耦 WebSocket 推送和业务逻辑
```
```

## 项目规范

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
| TrendRadar | trend_radar/ | ✅ | ✅ |
| newsnow | newsnow_notes/ | ✅ | ✅ |
| nanobot | nanobot_notes/ | ✅ | ✅ |
| MetaGPT | meta_gpt/ | ✅ | ✅ |
| ai-hedge-fund | ai_hedge_fund/ | ✅ | ✅ |
| worldmonitor | world_monitor/ | ✅ | ✅ |
| impeccable | impeccable_notes/ | ✅ | ✅ |
| Kun | kun_notes/ | ✅ | ✅ |
| deepseek-harness | deepseek_harness_notes/ | ✅ | ✅ |
| ib_async | ib_async_notes/ | ✅ | ✅ |
