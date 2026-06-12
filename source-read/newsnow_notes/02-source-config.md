# （二）源配置系统：从 human-friendly 到 machine-friendly

> 基于 newsnow v0.0.40。

## 为什么需要两层配置

42 个新闻源，每个都有自己的抓取频率、展示方式、所属栏目。如果让开发者手写 `sources.json`（50+ 个条目、每个 10+ 个字段），维护起来就是一坨重复的 JSON。

NewsNow 的解法：**人写一份简洁的 `pre-sources.ts`，构建脚本展开成机器读的 `sources.json`**。

## pre-sources.ts：给人看的源定义

```typescript
// shared/pre-sources.ts（简化）
const Time = {
  Fast: 120000,     // 2 分钟——热搜变化快
  Common: 600000,   // 10 分钟
  Slow: 3600000,    // 1 小时——内容站变化慢
}

export const originSources = {
  // 简单源——一个平台一个榜单
  "weibo": {
    name: "微博", color: "red", column: "china",
    type: "hottest", interval: Time.Fast,
    home: "https://weibo.com",
  },

  // 带子源的——一个平台多个榜单
  "wallstreetcn": {
    name: "华尔街见闻", color: "blue", column: "finance",
    sub: {
      quick: { type: "realtime", interval: Time.Fast, title: "快讯" },
      news: { title: "最新", interval: Time.Common },
      hot:  { type: "hottest", interval: Time.Common, title: "最热" },
    },
  },

  // 重定向——另一个名字指向同一个数据
  "v2ex": {
    name: "V2EX", color: "orange", column: "tech",
    redirect: "v2ex-share",
  },

  // 被 Cloudflare 盾挡住的——自动跳过
  "ithome": {
    name: "IT之家", color: "red", column: "tech",
    interval: Time.Common, home: "https://www.ithome.com",
    disable: "cf",  // 仅在 Cloudflare Pages 环境禁用
  },
}
```

### Time 常量——用语义代替数字

```typescript
const Time = {
  Fast: 2 * 60 * 1000,      // 2 min
  Common: 10 * 60 * 1000,    // 10 min
  Slow: 60 * 60 * 1000,      // 60 min
}
```

比写 `120000` 直观得多，而且改全局频率只改一处。

### sub：平台内多榜单的表达

`sub` 是这个配置系统最精巧的设计。来看一个具体的展开过程：

```typescript
// 输入：人写的
"bilibili": {
  name: "哔哩哔哩", column: "china",
  sub: {
    "hot-search": { type: "hottest", title: "热搜" },
    "hot-video":  { title: "热门视频" },
    "ranking":    { title: "排行榜" },
  },
}

// 输出：genSources() 展开为 4 个独立源
"bilibili":            { redirect: "bilibili-hot-search" },
"bilibili-hot-search": { name: "哔哩哔哩", type: "hottest", title: "热搜", ... },
"bilibili-hot-video":  { name: "哔哩哔哩", title: "热门视频", ... },
"bilibili-ranking":    { name: "哔哩哔哩", title: "排行榜", ... },
```

规则：

1. 父 ID 变成 redirect，指向第一个子源
2. 每个 `sub` 的 key 拼接为 `{parentId}-{subId}`
3. 子源继承父源的 `name`、`color`、`column`、`home`，可覆盖 `type`、`interval`、`title`

这意味着用户看到的 URL 是 `/sources/bilibili`（语义清晰），底层实际路由到 `bilibili-hot-search`。

### disable 的三种状态

| 值 | 含义 | 场景 |
|----|------|------|
| `false`（默认） | 正常启用 | 大部分源 |
| `true` | 全局禁用 | 源已失效、不再维护 |
| `"cf"` | Cloudflare Pages 环境禁用 | 中国网站拒绝海外 IP |

`disable: "cf"` 是一个务实的妥协——承认某些中国网站（IT之家、凤凰网）会拒绝 Cloudflare 的海外 IP。本地开发正常，部署到 Cloudflare 时自动跳过。

## genSources()：展开逻辑

```typescript
// shared/pre-sources.ts 底部
export function genSources() {
  const sources: Record<string, Source> = {}

  for (const [id, origin] of Object.entries(originSources)) {
    // 1. 跳过全局禁用的源
    if (origin.disable === true) continue

    const base = { ...origin, sub: undefined, redirect: undefined }

    if (origin.redirect) {
      // 2. 重定向源——直接指向目标
      sources[id] = { name: origin.name, redirect: origin.redirect, ...base }
    } else if (origin.sub) {
      // 3. 有子源——展开为 N+1 个条目
      const subIds = Object.keys(origin.sub)
      
      // 3a. 父 ID → redirect 到第一个子源
      sources[id] = { ...base, redirect: `${id}-${subIds[0]}` }

      // 3b. 每个子源独立一条
      for (const [subId, subConfig] of Object.entries(origin.sub)) {
        if (subConfig.disable) continue  // 子源也可以单独禁用
        const sourceId = `${id}-${subId}`
        sources[sourceId] = {
          ...base,
          ...subConfig,             // 子源覆盖父源
          name: base.name!,         // 保持父源的显示名
        }
      }
    } else {
      // 4. 简单源——原样保留
      sources[id] = { ...base } as Source
    }
  }

  return sources
}
```

构建时 `scripts/source.ts` 调用 `genSources()`，产出 `shared/sources.json`：

```bash
npx tsx scripts/source.ts
# → 写入 shared/sources.json（50+ 条目）
# → 写入 shared/pinyin.json（中文名 → 拼音）
```

## 类型系统：从运行时到编译时

```typescript
// shared/types.ts
// 从 originSources 推导出所有合法 source ID 的联合类型
export type SourceID = {
  [K in keyof typeof originSources]:
    // 如果源有 disable → never（排除）
    typeof originSources[K] extends { disable: true } ? never :
    // 如果源有 sub → 展开为 "parent" | "parent-sub1" | "parent-sub2"
    typeof originSources[K] extends { sub: infer S } ?
      K | { [Sub in keyof S]: S[Sub] extends { disable: true } ? never : `${K & string}-${Sub & string}` }[keyof S] :
    // 否则 → 只有 parent
    K
}[keyof typeof originSources]
```

这个类型展开的结果是：

```typescript
// SourceID = "weibo" | "zhihu" | "bilibili" | "bilibili-hot-search"
//          | "bilibili-hot-video" | "bilibili-ranking"
//          | "wallstreetcn" | "wallstreetcn-quick" | ...
```

如果开发者在 `getter` 里引用了一个不存在的 ID（比如把源文件名写错了），TypeScript 编译期直接报错——不需要等到运行时才发现。

## 拼音索引：让 cmdk 支持中文搜索

```typescript
// scripts/source.ts
function genPinyin() {
  const pinyinMap: Record<string, string> = {}
  for (const [id, source] of Object.entries(sources)) {
    if (source.name && !pinyinMap[source.name]) {
      pinyinMap[source.name] = toPinyin(source.name)
    }
  }
  return pinyinMap
}
```

产出 `shared/pinyin.json`：

```json
{
  "华尔街见闻": "huaerjiejianwen",
  "哔哩哔哩": "bilibili",
  "微博": "weibo"
}
```

前端搜索时，输入拼音首字母 `hws` → 反查 `huaerjiejianwen` → 匹配"华尔街见闻"。42 个源的中文名全支持拼音搜索。

## 源配置的文件组织

```
server/sources/
├── zhihu.ts            # 简单源 —— 单文件、单 export
├── weibo.ts
├── hackernews.ts
├── bilibili.ts          # 多子源 —— 单文件、多 export
├── wallstreetcn.ts      # 同文件内处理 quick/news/hot 三个 API
├── cls/                 # 目录级源 —— 有自定义 auth 逻辑
│   ├── index.ts         #   三个子源的抓取
│   └── utils.ts         #   SHA-1 签名生成
├── coolapk/             #   同上——App Token 生成
│   ├── index.ts
│   └── utils.ts
└── _36kr.ts             # 下划线前缀——只影响 glob 导入的顺序
```

`_36kr.ts` 的前缀 `_` 是一个 hack——JavaScript 变量名不能以数字开头，但文件夹导入时不会冲突。只是为了让 36kr 在字母排序中排在前面。

## 小结

源配置系统的核心设计理念是**人和机器各看各的**：

| 层 | 受众 | 特点 |
|----|------|------|
| `pre-sources.ts` | 人 | `sub` 嵌套、`Time` 常量、`disable: "cf"` 标记 |
| `sources.json` | 机器 | 扁平展开、所有字段填充完整 |
| `SourceID` 类型 | TypeScript 编译器 | 从配置推导，写错直接报编译错误 |
| `pinyin.json` | 前端搜索框 | 中文名 → 拼音，支持首字母搜索 |

下一篇深入抓取引擎——`myFetch` 怎么处理超时重试、`defineRSSSource` 怎么封装 RSS 解析、`coolapk` 的 App Token 怎么逆向的。
