# nanobot 源码阅读（四）：Session 与 Memory——Dream 记忆巩固

> 基于 nanobot v0.2.1。

## 问题：AI Agent 的记忆应该怎么存

nanobot 的"记忆"分三层：

1. **Session（会话历史）**：一次对话的完整记录，存为 JSONL 文件
2. **Memory（长期记忆）**：跨会话的知识提取，存为 `MEMORY.md` 等 Markdown 文件
3. **Dream（记忆巩固）**：异步后台任务，从历史中提炼知识写入长期记忆

这三层构成了从"对话缓存"到"知识沉淀"的递进。

## Session：JSONL 持久化

```python
# nanobot/session/manager.py
@dataclass
class Session:
    key: str                      # channel:chat_id
    messages: list[dict]          # 消息列表
    metadata: dict                # 元数据（goal_state, checkpoint, ...）
    last_consolidated: int        # 已 consolidate 的消息数
    created_at: datetime
    updated_at: datetime
```

每个 session 存为一个 JSONL 文件——第一行是 metadata，后续每行一条消息：

```jsonl
{"_type": "metadata", "key": "telegram:12345", "created_at": "...", ...}
{"role": "user", "content": "帮我写个 HTTP server", "timestamp": "..."}
{"role": "assistant", "content": "好的，这是一个简单的 HTTP server...", "timestamp": "..."}
```

### 原子写入：先写 tmp，再 rename

```python
# nanobot/session/manager.py
def save(self, session: Session, *, fsync: bool = False) -> None:
    path = self._get_session_path(session.key)
    tmp_path = path.with_suffix(".jsonl.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        # 写 metadata + 所有消息
        # ...
    os.replace(tmp_path, path)  # 原子替换
```

`os.replace()` 在 POSIX 上是原子操作——要么完全成功，要么保留旧文件。不存在"写了一半崩溃"的状态。

`fsync=True` 模式在 shutdown 时使用——flush 文件 + fsync 目录，确保 rclone/NFS 等有写缓存的文件系统也不丢数据。

### 历史回放：token budget 截断

```python
def get_history(self, max_messages=120, *, max_tokens=0, ...) -> list[dict]:
    unconsolidated = self.messages[self.last_consolidated:]  # 跳过已 consolidate 的
    # 1. 消息数量截断
    sliced = unconsolidated[-max_messages:]
    # 2. 从 user turn 开始（不截断在半路）
    for i, msg in enumerate(sliced):
        if msg["role"] == "user":
            sliced = sliced[i:]
            break
    # 3. Token 预算截断（从尾部反向累加）
    if max_tokens > 0:
        kept = []
        used = 0
        for msg in reversed(sliced):
            tokens = estimate_message_tokens(msg)
            if kept and used + tokens > max_tokens:
                break
            kept.append(msg)
            used += tokens
        kept.reverse()
        sliced = kept
    return sliced
```

三个截断策略保证发给 LLM 的历史不会超出 context window——先按数量、再对齐 user turn 边界、最后按 token 预算。

### Runtime Checkpoint：/stop 后恢复

用户执行 `/stop` 中断一个正在运行的 turn 时，nanobot 不会丢失已执行的 tool 结果：

```python
# nanobot/agent/loop.py
async def _state_save(self, ctx):
    # checkpoint 保存在 session metadata 里
    self._set_runtime_checkpoint(session, {
        "assistant_message": ...,       # LLM 返回的 assistant 消息
        "completed_tool_results": [...], # 已完成的 tool 结果
        "pending_tool_calls": [...],     # 还在执行中的 tool_call
    })
```

下次对话时，`_state_restore()` 把 checkpoint 从 metadata 还原到 session 消息列表——用户看到的连续对话里，被中断的 tool 结果也在。

## Memory：长期知识存储

```python
# nanobot/agent/memory.py
class MemoryStore:
    """纯文件 I/O：MEMORY.md, history.jsonl, SOUL.md, USER.md"""
    def __init__(self, workspace):
        self.memory_file = workspace / "memory" / "MEMORY.md"
        self.history_file = workspace / "memory" / "history.jsonl"
        self.soul_file = workspace / "SOUL.md"
        self.user_file = workspace / "USER.md"
```

`MEMORY.md` 存储长期记忆（每个事实一个文件，带 frontmatter）。`history.jsonl` 是 append-only 日志——每条记录带自增 cursor，方便增量读取。

`GitStore` 自动把 `MEMORY.md`、`SOUL.md`、`USER.md` 的变更 commit 到 git——所以记忆修改有版本控制。

## Dream：异步记忆巩固

Dream 是 nanobot 最独特的设计——它把记忆巩固做成一个独立的 agent turn：

```python
# nanobot/agent/memory.py
def build_dream_prompt(self, *, max_entries=20) -> tuple[str, int] | None:
    last_cursor = self.get_last_dream_cursor()
    entries = self.read_unprocessed_history(since_cursor=last_cursor)
    if not entries:
        return None  # 没有新数据，跳过
    batch = entries[:max_entries]
    history_text = "\n".join(
        f"[{e['timestamp']}] {truncate_text(e['content'], 500)}"
        for e in batch
    )
    prompt = render_template("agent/dream.md") + "\n\n" + history_text
    return (prompt, batch[-1]["cursor"])
```

Dream 给 LLM 一个受限的工具集——只能读/写/编辑 `MEMORY.md`、`SOUL.md`、`USER.md` 和 `skills/` 目录。它不能执行 shell、不能搜索网页、不能操作 workspace 文件。这确保了记忆巩固是安全的、可控的。

```python
def build_dream_tools(self):
    tools = ToolRegistry()
    # 只有 filesystem 工具，且限定在 memory 文件 + skills 目录
    tools.register(ReadFileTool(
        workspace=workspace, allowed_dir=workspace,
        extra_read_allowed_dirs=[BUILTIN_SKILLS_DIR],
    ))
    tools.register(EditFileTool(
        workspace=workspace,
        allowed_dir=skills_dir,
        extra_write_allowed_files=[self.memory_file, self.soul_file, self.user_file],
    ))
    tools.register(WriteFileTool(
        workspace=workspace, allowed_dir=skills_dir,
    ))
    return tools
```

## Consolidator：Token 预算触发的记忆归档

当 session 历史太长、接近 context window 上限时，`Consolidator` 会把最早的对话轮次发送给 LLM 做摘要，然后把摘要存入 `history.jsonl`：

```python
# nanobot/agent/memory.py
async def maybe_consolidate_by_tokens(self, session, *, replay_max_messages=None):
    if estimated_tokens < budget:
        return  # 还没超，不需要 consolidate

    for round_num in range(_MAX_CONSOLIDATION_ROUNDS):
        # 1. 找到安全的 archive 边界（user turn 边界）
        boundary = self.pick_consolidation_boundary(session, tokens_to_remove)
        # 2. 把边界前的消息发给 LLM 摘要
        summary = await self.archive(chunk, session_key=session.key)
        # 3. 推进 last_consolidated 指针
        session.last_consolidated = end_idx
        # 4. 重新估算 token 用量
        estimated, _ = self.estimate_session_prompt_tokens(session)
        if estimated <= target:
            break
```

关键设计：`last_consolidated` 指针使得 consolidation 是增量的——已经归档的消息不会被重复处理，`get_history()` 只返回"未 consolidate 的部分"。

如果 LLM 摘要调用失败，降级方案是 `raw_archive()`——直接把消息文本写入 `history.jsonl`，保证不丢数据。

## AutoCompact：TTL 淘汰

```python
# nanobot/agent/autocompact.py
class AutoCompact:
    def check_expired(self, schedule_background, *, active_session_keys):
        for key in self.sessions.list_keys():
            if key in active_session_keys:
                continue  # 活跃 session 不压缩
            session = self.sessions.get_or_create(key)
            if is_expired(session, self.session_ttl_minutes):
                # 后台执行 compact：保留最近 8 条消息，其余送 consolidator
                schedule_background(
                    self.consolidator.compact_idle_session(key, max_suffix=8)
                )
```

## 小结

三层记忆的递进关系：

```
Session (JSONL) ──token 超限──→ Consolidator ──→ history.jsonl
                                        │
                                        ▼
                                    LLM 摘要
                                        │
Session (JSONL) ──TTL 过期──→ AutoCompact ──→ history.jsonl
                                        │
                                        ▼
                                    LLM 摘要
                                        │
history.jsonl ──有新数据──→ Dream (另一个 agent turn)
                                        │
                                        ▼
                              MEMORY.md + SOUL.md + USER.md
                                        │
                                        ▼
                                  git commit
```

每一步都有降级方案——LLM 调用失败时 `raw_archive` 保底——确保不会因为一个 model error 丢掉整段对话历史。

下一篇讲 Channel 系统——nanobot 如何用一套接口接入 15+ 个聊天平台。
