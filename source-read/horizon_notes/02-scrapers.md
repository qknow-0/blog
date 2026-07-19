# Horizon 源码阅读（二）：多源采集系统——10 个 Scraper，一个接口

> 基于 Horizon v0.x，源码地址 `source-read/horizon/`。

## 整体架构

Horizon 的采集层由 10 个 Scraper 组成，覆盖了信息聚合最常见的 10 类数据源：

| Scraper | 源 | 认证方式 | 特色 |
|---------|---|---------|------|
| `GitHubScraper` | GitHub Events / Releases | `GITHUB_TOKEN`（可选） | 用户事件 + 仓库 Release |
| `HackerNewsScraper` | Hacker News | 无需认证 | 自动抓取 Top Comments |
| `RSSScraper` | RSS / Atom Feeds | 请求头或 URL 中可嵌 Token | 支持内容全文提取 |
| `RedditScraper` | Reddit | 无需认证 | 三层降级策略（JSON → HTML → RSS） |
| `TelegramScraper` | Telegram Channels | Telegram API | 频道消息获取 |
| `TwitterScraper` | Twitter (Apify) | `APIFY_TOKEN` | 基于 Apify Actor |
| `TwitterPlaywrightScraper` | Twitter (Playwright) | Cookie 文件 | 免费方案，浏览器自动化 |
| `OpenBBScraper` | 金融新闻 | 可选（OpenBB SDK） | 股票/公司新闻 |
| `OSSInsightScraper` | OSS Insight Trending | 无需认证 | GitHub 增长最快仓库 |
| `GDELTScraper` | GDELT 2.0 | 无需认证 | 全球新闻 API |
| `GoogleNewsScraper` | Google News RSS | 无需认证 | 关键词新闻搜索 |

## 核心设计：一个统一的抽象接口

### 源码

```python
# src/scrapers/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
import httpx

from ..models import ContentItem

class BaseScraper(ABC):
    """抽象基类，所有 Scraper 继承自它。"""

    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @abstractmethod
    async def fetch(self, since: datetime) -> List[ContentItem]:
        """获取 since 之后发布的所有内容。"""
        pass

    def _generate_id(self, source_type: str, subtype: str, native_id: str) -> str:
        """生成全局唯一 ID: {source}:{subtype}:{native_id}"""
        return f"{source_type}:{subtype}:{native_id}"
```

### 好在哪

1. **一个 `fetch` 方法统一所有**——不管是从 REST API 拉取、从 RSS 解析、还是从浏览器自动化抓取，对外接口只有 `fetch(since) → List[ContentItem]`。Orchestrator 不需要知道某个 Scraper 是怎么实现的。

2. **依赖注入 `http_client`**——所有 Scraper 共享一个 `httpx.AsyncClient`，由外部传入。好处有两个：（1）连接池复用，减少 TCP 握手开销；（2）测试时可以注入 mock client。

3. **标准化 ID 生成**——`_generate_id` 方法生成 `{source}:{subtype}:{native_id}` 格式的 ID，天然包含来源信息，方便去重和溯源。

4. **返回值永远是 `List[ContentItem]`**——所有原始数据在 Scraper 内部就转换好了。下游的 AI 分析层、存储层、分发层都只跟 `ContentItem` 打交道。

## 优秀代码：并行采集 + 三层降级策略

### RedditScraper 的三层降级

Reddit 的 API 访问限制很多——需要认证、有速率限制、且 JSON API 对未认证请求越来越严格。Horizon 的 RedditScraper 实现了「三层降级」策略：

```python
# src/scrapers/reddit.py（核心逻辑简化）
class RedditScraper(BaseScraper):

    async def _fetch_subreddit(self, cfg, since):
        # 第 1 层：old.reddit.com HTML 解析（无需 API Key，最宽松）
        html_items = await self._fetch_subreddit_html(cfg, since)
        if html_items:
            return html_items

        # 第 2 层：JSON API（需要认证，但有速率限制）
        try:
            data = await self._reddit_get(url, params)
        except RedditBlockedError:
            # 第 3 层：RSS 兜底（最可靠，但信息最简）
            return await self._fetch_subreddit_rss(cfg, since)
```

这个设计思路很实用：**优先选择对目标服务负担最小的方式**。HTML 解析不需要 API Key，RSS 是标准协议最稳定，JSON API 作为中间选择。三层依次 fallback，总有能用的方案。

### HackerNewsScraper 的并行评论抓取

```python
# src/scrapers/hackernews.py（核心逻辑简化）
class HackerNewsScraper(BaseScraper):

    async def fetch(self, since: datetime) -> List[ContentItem]:
        # 批量获取 Top Stories ID
        story_ids = await self.client.get(f"{self.base_url}/topstories.json")
        story_ids = story_ids.json()[:fetch_count]

        # 第 1 轮并发：同时拉取所有 Story 详情
        stories = await asyncio.gather(
            *[self._fetch_story(sid) for sid in story_ids],
            return_exceptions=True,
        )

        # 筛选有效 Story，同时构造评论请求
        valid_stories = []
        comment_tasks = []
        for story in stories:
            if isinstance(story, Exception) or story is None:
                continue
            if story.get("score", 0) < min_score:
                continue
            valid_stories.append(story)
            comment_tasks.append(self._fetch_comments(
                story.get("kids", [])[:TOP_COMMENTS_LIMIT]
            ))

        # 第 2 轮并发：同时拉取所有 Story 的 Top Comments
        all_comments = await asyncio.gather(*comment_tasks, return_exceptions=True)

        # 组装 ContentItem
        for story, comments in zip(valid_stories, all_comments):
            items.append(self._parse_story(story, comments or []))
```

### 好在哪

1. **两阶段并发**——先把所有 Story 详情并发拉回来，再根据 `kids`（评论 ID 列表）并发拉评论。不是等每条 Story 拉完了再拉它的评论，而是批次 + 批次的模式。

2. **`return_exceptions=True`**——某个 Story 或评论请求失败不会影响其他请求。Hacker News 的 `/item/{id}.json` 接口偶尔会超时，这种模式保证了稳定性。

3. **只拉 Top 5 评论**——`TOP_COMMENTS_LIMIT = 5` 控制了每条 Story 的评论数量，既提供了有价值讨论内容，又控制了 API 请求量和 token 消耗。

### 骨架代码：多阶段并发采集

```python
import asyncio

async def multi_stage_fetch(
    item_ids: list,
    fetch_item_fn,
    fetch_children_fn,
    max_children: int = 5,
):
    """两阶段并发拉取模式：先拉主条目，再拉子内容。"""
    # Stage 1：并发拉主条目
    items = await asyncio.gather(
        *[fetch_item_fn(i) for i in item_ids],
        return_exceptions=True,
    )
    valid = [i for i in items if not isinstance(i, Exception) and i]

    # Stage 2：并发拉子内容
    child_tasks = []
    for item in valid:
        child_ids = item.get("child_ids", [])[:max_children]
        child_tasks.append(fetch_children_fn(child_ids))

    children = await asyncio.gather(*child_tasks, return_exceptions=True)

    # 组装
    result = []
    for item, child_list in zip(valid, children):
        if isinstance(child_list, Exception):
            child_list = []
        result.append(_merge(item, child_list))
    return result
```

## 优秀代码：RSSScraper 的 Token 注入与内容提取

RSS Feed 有些需要认证（如 LWN 会员 feed），有些摘要很短需要全文提取。RSSScraper 解决这两个问题的方式很优雅。

```python
# src/scrapers/rss.py（精简）
class RSSScraper(BaseScraper):

    async def _fetch_feed(self, source, since):
        # 1. 环境变量注入 —— ${LWN_TOKEN} 在运行时替换
        feed_url = re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            str(source.url),
        )

        response = await self.client.get(feed_url, follow_redirects=True)
        feed = feedparser.parse(response.text)

        for entry in feed.entries:
            # 2. 可选：全文提取
            if source.content_extractor and self._extractors:
                extractor = self._extractors.get(source.content_extractor)
                if extractor:
                    full = await extractor.extract(entry.link, self.client)
                    if full:
                        content = full
```

两种能力合在一起的价值：

- **环境变量注入**——`${VAR}` 语法允许在配置文件中使用占位符，实际运行时才替换。这样可以直接把需要认证的 feed URL 写在配置里，而敏感的 token 留在 `.env` 文件。
- **可插拔的提取器**——`content_extractor` 字段指向一个 `ExtractorRegistry` 中的提取器，目前使用 trafilatura 做正文提取。这是策略模式：RSS feed 的摘要可能很短，需要提取器去原文页抓取正文。

## 数据模型：SourceType 枚举

10 个 Scraper 对应 10 个 `SourceType` 枚举值：

```python
# src/models.py
class SourceType(str, Enum):
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    REDDIT = "reddit"
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    OPENBB = "openbb"
    OSSINSIGHT = "ossinsight"
    GDELT = "gdelt"
    GOOGLE_NEWS = "google_news"
```

每个 Scraper 在创建 `ContentItem` 时传入对应的 `SourceType`，下游的过滤、分析、展示都通过这个枚举区分来源。

## 为什么这么设计

**策略模式（Strategy Pattern）**：每个 Scraper 是一个策略，实现同一个接口 `fetch(since)`。Orchestrator 根据配置决定启用哪些策略，然后统一调用。

这个选择对比「一个巨型 Scraper 类 + if-else 分支」：

| 维度 | 策略模式 | if-else 大统一 |
|------|---------|---------------|
| 新增源 | 建新文件，写新类 | 改大文件，加分支，可能影响已有代码 |
| 测试 | 每个 Scraper 独立测试 | 必须 mock 所有依赖 |
| 职责边界 | 清晰：一个 Scraper 只懂一种源 | 模糊：一个类什么都做 |
| 可读性 | 每源 100-200 行，集中处理细节 | 上千行，阅读困难 |

Horizon 选了策略模式，10 个 Scraper 文件都在 100-200 行，每个文件聚焦一种数据源的细节。

## 反模式警示

每个 Scraper 都可能在 `fetch` 中抛出异常，但如果你的 Scraper 抛了异常就直接炸掉整个流程，那就是错误的做法。Orchestrator 中正确的处理方式是：

```python
# 正确：单个 Scraper 失败不影响其他源
outcomes = await asyncio.gather(*tasks, return_exceptions=True)
# 失败信息记录在 FetchReport 中，流程继续
```

如果你的采集系统只有一个统一的 `fetch_from_all_sources()` 方法，其中任何一个源失败就返回空列表，那你的用户会错过所有其他源的内容。

## 小结

1. **10 个 Scraper 一个接口**——`BaseScraper` 定义了 `fetch(since)` 抽象方法，所有采集器遵循同一契约
2. **并行采集 + 降级策略**——`asyncio.gather` 多并发，单个失败不影响全局；Reddit 的三层降级确保总有数据
3. **边界标准化**——所有源在 Scraper 内部转为 `ContentItem`，下游不关心原始数据格式

---

**上一篇：** [架构总览](01-architecture.md)
**下一篇：** [AI 分析层](03-ai-layer.md)
