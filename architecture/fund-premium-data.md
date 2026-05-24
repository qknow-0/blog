# LOF 基金实时数据查询系统 — 数据处理文档

## 1. 系统概述

### 1.1 系统定位

LOF 基金溢价监控面板，实时追踪 LOF（Listed Open-Ended Fund，上市型开放式基金）的场内交易价格与基金净值之间的偏离程度，发现套利机会。

### 1.2 数据出口

| 出口 | 路径 | 触发方式 | 说明 |
|------|------|----------|------|
| 实时表格 API | `GET /api/lof` | 前端轮询 | 全量 LOF 实时行情 + 溢价率 + 申购限额 |
| 历史明细 API | `GET /api/lof/history?fundCode=` | 前端按需 | 单只基金历史价格、净值、溢价率、场内份额 |
| 飞书告警 | `POST /api/v1/notify` | 定时 + 启动执行 | 筛选高溢价基金推送到飞书群 |

### 1.3 数据流全景

```
东方财富 push2delay ─┐
东方财富 Fund_JJZJ ───┼─→ ThreadPoolExecutor ─→ merge ─→ 计算溢价率 ─→ 格式化 ─→ JSON 响应
东方财富 FundGuZhi ───┘        │
                               └→ 缓存 (降级 fallback)

同花顺/东方财富 K线 ─→ 实时校准 ─→ 份额修正 ─→ 净值合并 ─→ 溢价率 ─→ JSON 响应
东方财富 lsjz ────────┘         │
东方财富 f84 ──────────────────┘
```

---

## 2. 外部数据源

### 2.1 实时行情（Spot）

**用途：** 获取 LOF 基金实时交易数据

**接口：** `https://push2delay.eastmoney.com/api/qt/clist/get`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `pn` | `1`, `2`, ... | 页码，按页数循环拉取全量 |
| `pz` | `500` | 每页条数 |
| `po` | `1` | 排序方向 |
| `fid` | `f3` | 按涨跌幅排序 |
| `fs` | `b:MK0404,b:MK0405,b:MK0406,b:MK0407` | LOF 市场的四个板块代码 |
| `fields` | `f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152` | 请求 35 个字段 |
| `ut` | `bd1d9ddb04089700cf9c27f6f7426281` | 固定 token |

**分页逻辑：**
```
1. 请求第一页 (pn=1) 获取 total 和 per_page_num
2. 计算 total_page = ceil(total / per_page_num)
3. 循环请求第 2 到 total_page 页
4. concat 所有页的 DataFrame
```

**返回结构（真实示例）：**
```json
{
  "data": {
    "total": 350,
    "diff": [
      {
        "f12": "161226",
        "f14": "白银基金",
        "f2": 0.992,
        "f3": -0.50,
        "f4": -0.005,
        "f5": 125000,
        "f6": 12400000,
        "f17": 0.995,
        "f15": 0.998,
        "f16": 0.985,
        "f18": 0.997,
        "f20": 2150000000
      }
    ]
  }
}
```

**源字段 → 内部字段映射：**

| 源字段 | 内部字段 | 含义 | 单位 |
|--------|----------|------|------|
| `f12` | `代码` | 基金代码 | — |
| `f14` | `名称` | 基金名称 | — |
| `f2` | `最新价` | 最新成交价 | 元 |
| `f3` | `涨跌幅` | 涨跌幅 | % |
| `f4` | `涨跌额` | 涨跌额 | 元 |
| `f5` | `成交量` | 成交量 | 手（1手=100份） |
| `f6` | `成交额` | 成交额 | 元 |
| `f17` | `开盘价` | 开盘价 | 元 |
| `f15` | `最高价` | 最高价 | 元 |
| `f16` | `最低价` | 最低价 | 元 |
| `f18` | `昨收` | 昨日收盘价 | 元 |
| `f20` | `总市值` | 基金总市值 | 元 |

**调用频率：** 每次 API 请求实时拉取，无缓存（spot 数据变化快速，缓存无意义）。

**代码位置：** `back/app/services/fetcher.py:20-78`

---

### 2.2 净值与限额（Purchase）

**用途：** 获取基金最新净值和日申购限额

**接口：** `https://fund.eastmoney.com/Data/Fund_JJZJ_Data.aspx`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `t` | `8` | 数据类型 |
| `page` | `1,50000` | 页码,每页条数（一次拉全量） |
| `js` | `reData` | JS 变量包装名 |
| `sort` | `fcode,asc` | 按基金代码升序 |

**返回结构（原始）：**
```javascript
var reData={datas:[[
  "161226",          // [0] 基金代码
  "国投瑞银白银期货(LOF)A",  // [1] 基金简称
  "商品型基金",        // [2] 基金类型
  1.005,              // [3] 最新净值/万份收益
  "2024-12-20",       // [4] 净值日期
  "开放",              // [5] 申购状态
  "",                  // [6] 赎回状态
  "",                  // [7] 下一开放日
  "",                  // [8] 购买起点
  10000                // [9] 日累计限定金额
  ...
], [...], ...]}
```

**JSON 解析优化：** 原始返回是 JS 变量赋值格式，不是合法 JSON。传统 `demjson` 库（纯 Python）解析需 ~1.5s。系统使用正则 `re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', text)` 给 key 加双引号后，用 C 实现的 `json.loads()` 解析，速度提升约 **150 倍**（~10ms）。

**选定列：**

| 列索引 | 字段名 | 含义 |
|--------|--------|------|
| `[0]` | `基金代码` | 基金代码 |
| `[3]` | `最新净值/万份收益` | 最新公布净值 |
| `[9]` | `日累计限定金额` | 单日申购上限（元） |
| `[5]` | `申购状态` | 开放 / 暂停 / 限大额 |

**缓存策略：** 5 分钟 TTL。净值一天只更新一次，申购限额变化更慢，缓存避免每次 API 请求都拉全量（~15k 基金 × 2 列 = 大量数据）。

**Fallback：** 直接解析失败时，回退到 `akshare.fund_purchase_em()`。

**代码位置：** `back/app/services/fetcher.py:81-131`，缓存逻辑见 `back/app/cache.py:7-34`

---

### 2.3 估算净值（Estimate）

**用途：** 获取实时估算净值（盘中实时计算，比收盘净值更及时）

**接口：** `https://api.fund.eastmoney.com/FundGuZhi/GetFundGZList`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `type` | `1` | 全部类型（不限定 LOF，避免跨分类遗漏） |
| `sort` | `3` | 排序方式 |
| `orderType` | `desc` | 降序 |
| `canbuy` | `0` | 不限制购买状态 |
| `pageIndex` | `1` | 页码 |
| `pageSize` | `50000` | 一次拉取全量 |
| `_` | 当前毫秒时间戳 | 防缓存 |

**返回结构（真实示例）：**
```json
{
  "Data": {
    "list": [
      [
        "161226",           // [0] 基金代码
        "...",              // [1]-[19] 其他字段
        1.008               // [20] 估算净值
      ]
    ]
  }
}
```

**选定列：**

| 列索引 | 字段名 | 含义 |
|--------|--------|------|
| `[0]` | `基金代码` | 基金代码 |
| `[20]` | `估算净值` | 实时估算净值 |

**Fallback：** 请求失败时回退到 `akshare.fund_value_estimation_em()`，从返回列中搜索名称包含 `估算数据-估算值` 的列。

**调用频率：** 每次 API 请求实时拉取（估算值盘中变化快速）。

**代码位置：** `back/app/services/fetcher.py:140-184`

---

### 2.4 历史 K 线数据

LOF 的历史价格数据有两个数据源，互为备份。

#### 2.4.1 主数据源：同花顺（10jqka）

**接口：** `http://d.10jqka.com.cn/v6/line/hs_{fund_code}/01/{year}.js`

**请求参数：** 无，URL 路径中直接拼入基金代码和年份。

**数据格式：** 返回 JS 文件，内容为 `var data = { "data": "..." }` 形式。`data` 字段是分号分隔的日线记录。

**每行记录的结构（逗号分隔）：**
```
20241220,0.995,0.998,0.985,0.992,12500000,12400000,1.25
   │       │     │     │     │      │       │       │
  日期   开盘   最高  最低  收盘  成交量(股) 成交额  换手率(%)
```

**份额计算公式（关键）：**
```
同花顺换手率基于场内份额（流通股本）
换手率(%) = 成交量(股) / 场内份额(股) × 100
=> 场内份额(万份) = 成交量(股) / (换手率(%) / 100) / 10000
```

**返回 DataFrame 列：**

| 列名 | 含义 | 单位 |
|------|------|------|
| `date` | 交易日期 | datetime |
| `price` | 收盘价 | 元 |
| `volume` | 成交量 | 手 |
| `turnover` | 成交额 | 万元 |
| `share_volume` | 场内份额（推算） | 万份 |

**注意：** 同花顺换手率仅保留 3 位小数。对低换手率基金（如 161226 白银基金，换手率 ~1%），份额计算误差可达 ~40 万份。这个误差通过后续 f84 校准修正。

**拉取策略：** 拉取当年和上一年两个 JS 文件，合并后取最近 `max_days=120` 天。

**代码位置：** `back/app/services/fetcher.py:187-239`

#### 2.4.2 备用数据源：东方财富 K 线

**接口：** `https://push2his.eastmoney.com/api/qt/stock/kline/get`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `secid` | `0.{fund_code}` 或 `1.{fund_code}` | 深市/沪市 ID |
| `fields1` | `f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13` | 基本信息字段 |
| `fields2` | `f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61` | K 线数据字段 |
| `klt` | `101` | K 线类型（101=日线） |
| `fqt` | `0` | 复权方式（0=不复权） |
| `lmt` | `120` | 最大条数 |

**K 线字段结构（f51-f61，逗号分隔）：**
```
2024-12-20,0.995,0.992,0.998,0.985,125000,12400000,1.25,1.50,-0.50,-0.005,0.85
    │         │     │     │     │     │       │       │    │    │    │     │
   日期     开盘   收盘   最高   最低  成交量  成交额  振幅 涨跌幅 涨跌额 换手率
```

**重要差异：** 东方财富换手率基于**总份额**（总股本），而非常内份额（流通股本）。因此推算出的 `share_volume` 是**总份额**，与同花顺的场内份额口径不同。这也是同花顺作为主数据源的原因。

**重试机制：** 带 5 次重试，递增延迟（1s, 1.5s, 2s, 4s, 8s），每次重试用新的 Session。

**代码位置：** `back/app/services/fetcher.py:242-308`

---

### 2.5 历史净值（NAV History）

**用途：** 获取基金历史单位净值（用于计算历史溢价率）

**接口：** `https://api.fund.eastmoney.com/f10/lsjz`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `fundCode` | 基金代码 | |
| `pageIndex` | `1`, `2`, ... | 分页循环 |
| `pageSize` | `120` | 每页条数 |
| `startDate` | K 线数据的最早日期 | 只拉需要的时间范围 |
| `endDate` | K 线数据的最晚日期 | |

**分页拉取逻辑：**
```
1. 第 1 页获取 TotalCount
2. 循环 pageIndex++ 直到 len(nav_rows) >= TotalCount
3. 每页取 Data.LSJZList
```

**返回结构（真实示例）：**
```json
{
  "TotalCount": 300,
  "Data": {
    "LSJZList": [
      {
        "FSRQ": "2024-12-20",     // 净值日期
        "DWJZ": "0.9920",          // 单位净值
        "LJJZ": "1.2560",          // 累计净值（未使用）
        "JZZZL": "-0.15"           // 净值增长率（未使用）
      }
    ]
  }
}
```

**选定字段：**

| 源字段 | 内部字段 | 含义 |
|--------|----------|------|
| `FSRQ` | `nav_date` | 净值日期 |
| `DWJZ` | `nav` | 单位净值（解析为 float，空值则为 None） |

**代码位置：** `back/app/routers/lof.py:171-209`

---

### 2.6 单个基金实时报价（Realtime Quote）

**用途：** 获取单只基金的实时数据，用于校准历史数据最新一天

**接口：** `https://push2.eastmoney.com/api/qt/stock/get`

**请求参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `secid` | `0.{code}` 或 `1.{code}` | `0`=深市（代码以0/2/3开头），`1`=沪市（代码以5/6/9开头） |
| `fields` | `f43,f47,f48,f84` | 仅请求 4 个必要字段 |

**返回结构（真实示例）：**
```json
{
  "data": {
    "f43": 992,        // 最新价（×1000，需除以1000）
    "f47": 1250,       // 成交量（手）
    "f48": 12400000,   // 成交额（元）
    "f84": 215000000   // 实时总份额（股）
  }
}
```

**字段处理：**

| 源字段 | 内部字段 | 转换 | 单位 |
|--------|----------|------|------|
| `f43` | `price` | `/1000` | 元 |
| `f47` | `volume` | 直接使用 | 手 |
| `f48` | `turnover` | 直接使用 | 元 |
| `f84` | `f84` | 直接使用 | 股 |

**调用频率：** 单次历史查询时调用 1 次。

**代码位置：** `back/app/routers/lof.py:47-69`

---

### 2.7 基金类型（Fund Type）

**用途：** 判断基金是否为 QDII，决定净值匹配策略

**接口：** `https://fundf10.eastmoney.com/jbgk_{fund_code}.html`

**解析方式：** 正则匹配 HTML 页面中的 `基金类型</th><td>XXX</td>`

**返回示例：**
- 商品型基金（如 161226 白银基金）：非 QDII
- QDII 基金（如 160213 纳斯达克 100）：QDII
- 混合型基金（如 161005）：非 QDII

**QDII 判定规则：** `"QDII" in fund_type` → 净值延迟 1 天匹配

**缓存策略：** 模块级 `_fund_type_cache: dict[str, str]`，无 TTL，程序生命周期内缓存。

**代码位置：** `back/app/routers/lof.py:25-44`

---

## 3. GET /api/lof — 实时数据接口

### 3.1 数据流步骤

```
Step 1: 并行拉取
  ├─ fetch_spot_data()     → 实时行情（~350 条 LOF）
  ├─ fetch_purchase_data() → 净值与限额（~15000 条，有 5min 缓存）
  └─ fetch_estimate_data() → 估算净值（~8000 条全量基金）
  总耗时：~3-4s（串行约 9s）
```

```
Step 2: LOF 代码过滤
  取 spot["代码"] 去重集合 → lof_codes
  purchase = purchase[purchase["基金代码"] ∈ lof_codes]
  estimate = estimate[estimate["基金代码"] ∈ lof_codes]
  目的：减少后续 merge 的无效行
```

```
Step 3: 三表合并
  spot ──(left join on 代码=基金代码)──→ purchase ──(left join on 代码=基金代码)──→ estimate
```

```
Step 4: 溢价率计算

  静态溢价率 = (最新价 - 最新净值/万份收益) / 最新净值/万份收益 × 100
    - 基于最新公布的收盘净值（通常是昨日净值）
    - 交易日内一直不变（净值收盘后才更新）

  估算溢价率 = (最新价 - 估算净值) / 估算净值 × 100
    - 基于实时估算净值（盘中实时推算）
    - 交易时间内动态变化，更真实反映当前溢价
    - 收盘后估算净值消失，值变为 NaN
```

```
Step 5: 格式化
  format_limit(日累计限定金额):
    0 或 NaN → "-"
    ≥ 1亿    → "不限"
    < 1万    → "{n}元/日"
    其他     → "{n/10000}万/日"

  format_amount(总市值/成交额):
    NaN      → "-"
    ≥ 1亿    → "{n/1e8:.2f}亿"
    ≥ 1万    → "{n/1e4:.2f}万"
    其他     → "{n:.0f}"
```

```
Step 6: 列选择与重命名
  见附录 A：字段映射表
```

```
Step 7: NaN 替换
  pd.NA, pd.NaN → "-"
```

```
Step 8: 缓存后返回
  update_cache_data(data)  // 存入 fallback 缓存
  return {"code": 200, "data": [...]}
```

### 3.2 异常降级

```
任一 future 超时（>30s）或异常
  → 检查 cached = get_cached_lof_data()
  → 有缓存：返回 {"code": 200, "data": [...], "cached": True}
  → 无缓存：返回 {"code": 500, "msg": "数据获取超时/失败..."}
```

### 3.3 返回 JSON 示例

```json
{
  "code": 200,
  "data": [
    {
      "fundCode": "161226",
      "fundName": "白银基金",
      "tradePrice": 0.992,
      "increaseRate": -0.50,
      "netValue": 1.005,
      "estimateValue": 1.008,
      "premiumRate": -1.29,
      "estimatePremiumRate": -1.59,
      "purchaseLimit": "1万/日",
      "purchaseStatus": "开放",
      "fundSize": "21.50亿",
      "volume": 125000,
      "turnover": "1.24亿"
    }
  ]
}
```

### 3.4 代码位置

`back/app/routers/lof.py:277-388`

---

## 4. GET /api/lof/history — 历史明细接口

### 4.1 数据流步骤

```
Step 1: K 线数据获取
  fetch_ths_kline(fund_code)
    ├─ 成功 → source="ths"，继续
    └─ 失败 → fetch_em_kline(fund_code, secid)
               ├─ 成功 → source="em"
               └─ 失败 → 返回 404
```

```
Step 2: 实时校准（仅同花顺数据源）

  调用 fetch_em_realtime(fund_code) 获取当前实时数据

  校准触发条件（同时满足）：
    1. 同花顺最新一天的日期 == 今天
    2. 价格偏差 > 0.1% 或 成交额偏差 > 50%

  原因：同花顺 year.js 文件有缓存延迟，当天最后一根 K 线可能未更新。
  东方财富 push2 接口是实时推送，数据更准确。

  校准时覆盖：price, volume, turnover
```

```
Step 3: 份额延后

  price_df["share_volume"] = price_df["share_volume"].shift(1)

  原因：T 日场内份额在收盘后结算，T+1 日才公布。
  所以 T 日的价格对应的是 T-1 日公布的份额。
```

```
Step 4: f84 份额校准（仅同花顺数据源）

  条件：
    1. 同花顺数据源
    2. f84（东方财富实时总份额）已获取
    3. 最新一天 share_volume 满足：
       - NaN → 直接用 f84 填充
       - 正常值且偏差 < 5% → 用 f84 替换

  原因：同花顺换手率仅 3 位小数。
  对低换手率基金（如 161226 白银基金，日换手率约 1%-2%），
  份额计算误差可达约 40 万份。
  f84 是东方财富实时总份额，对 LOF 基金 ≈ 场内份额，误差 < 1%。
```

```
Step 5: 份额变动计算

  change_amount = share_volume[t] - share_volume[t-1]
  change_pct    = change_amount / share_volume[t-1] × 100

  注意：share_volume 已经 shift(1) 过了，
  所以这里的变动反映的是公布日比前一公布日的变化。
```

```
Step 6: 净值拉取

  API: https://api.fund.eastmoney.com/f10/lsjz
  时间范围: price_date_min ~ price_date_max
  分页: 每页 120 条，循环拉取直到页数 × 120 ≥ TotalCount

  返回: nav_df["nav_date", "nav"]
```

```
Step 7: 净值匹配（按基金类型分策略）

  get_fund_type(fund_code) → fund_type

  如果是 QDII（fund_type 含 "QDII"）：
    price_df["prev_date"] = price_df["date"].shift(1)
    用 prev_date 匹配 nav_date
    → T 日价格对应 T-1 日净值

    原因：QDII 基金投资海外市场，净值公布有延迟。
    当日公布的净值实际是前一交易日的净值。

  如果是非 QDII（商品、混合型等）：
    用 date 直接匹配 nav_date
    → T 日价格对应 T 日净值
```

```
Step 8: 溢价率计算

  溢价率 = (price - nav) / nav × 100
  结果四舍五入到 2 位小数
```

```
Step 9: 数据清洗与输出

  1. 列选择：date, price, nav_date, nav, premium_rate,
             turnover, share_volume, change_amount, change_pct
  2. 列重命名：→ date, price, navDate, nav, premiumRate,
               turnover, shareVolume, changeAmount, changePct
  3. NaN 替换：
     - pd.notnull 替换为 None
     - pd.NA 和 float('nan') 替换为 None
     - 逐行逐列 NaN 检查（float NaN 的 Python 判定：v != v）
  4. 逆序排列（最新数据在前）
```

### 4.2 返回 JSON 示例

```json
{
  "code": 200,
  "data": [
    {
      "date": "2024-12-20",
      "price": 0.992,
      "navDate": "2024-12-20",
      "nav": 1.005,
      "premiumRate": -1.29,
      "turnover": 1240.00,
      "shareVolume": 21500.00,
      "changeAmount": -120.50,
      "changePct": -0.557
    }
  ],
  "fundCode": "161226",
  "fundName": "白银基金"
}
```

### 4.3 代码位置

`back/app/routers/lof.py:72-274`

---

## 5. 告警系统 — 数据处理

### 5.1 触发机制

**APScheduler (AsyncIOScheduler)**，时区 `Asia/Shanghai`：

| 配置项 | 默认值 | 环境变量 |
|--------|--------|----------|
| 触发小时 | `11,14` | `LOF_ALERT_CRON_HOURS` |
| 触发星期 | `mon-fri` | `LOF_ALERT_CRON_DAYS` |
| 每次推送上限 | `5` 只 | `LOF_ALERT_MAX_COUNT` |

**额外触发：** 应用启动时立即执行一次（`scheduler.add_job(run_alert_cycle, id="lof_alert_startup")`）。

### 5.2 筛选条件

```
1. 申购状态不含 "暂停"        — 可申购的基金才有套利价值
2. 估算溢价率 > 0%            — 正溢价（场内价高于净值）才有溢价套利机会
3. 成交额 > 1,000,000 元      — 排除流动性极差的基金
4. 估算溢价率不為 NaN         — 排除估算净值缺失
5. 成交额不為 NaN             — 排除无成交
```

### 5.3 排序与截断

按估算溢价率**降序**排列，取前 `settings.max_count`（默认 5）条。

### 5.4 推送 Payload

```json
{
  "channel": "feishu",
  "title": "基金套利提醒",
  "template": "fund_arbitrage",
  "body": "{\"title\":\"基金套利监控\",\"funds\":[{
    \"fund_code\": \"161226\",
    \"fund_name\": \"白银基金\",
    \"on_exchange_price\": \"0.992\",
    \"off_exchange_nav\": \"1.005\",
    \"estimated_nav\": \"1.008\",
    \"price_change\": \"-0.50%\",
    \"premium_rate_yesterday\": \"-1.29%\",
    \"premium_rate_realtime\": \"-1.59%\",
    \"daily_limit\": \"1万/日\",
    \"subscription_suspended\": \"否\",
    \"fund_size\": \"21.50亿\",
    \"trading_volume\": \"1.24亿\"
  }]}"
}
```

**目标地址：** `{LOF_ALERT_API_BASE_URL}/api/v1/notify`，未配置时静默跳过。

### 5.5 代码位置

`back/app/services/alerter.py:18-132`

---

## 6. 缓存系统

### 6.1 缓存层次概览

| 缓存 | 数据类型 | TTL | 用途 |
|------|----------|-----|------|
| LOF 实时数据 | `list[dict]` | 无 TTL | 异常降级 fallback |
| 净值/限额 | `pd.DataFrame` | 5 分钟 | 减少重复拉取 |
| 基金类型 | `dict[str, str]` | 程序生命周期 | 避免重复爬页面 |

### 6.2 LOF 实时数据缓存

```
结构: {"data": [...], "time": Timestamp}
位置: back/app/cache.py:5

写入: 每次 GET /api/lof 成功后调用 update_cache_data()
读取: GET /api/lof 超时或异常时调用 get_cached_lof_data()

非 TTL 缓存，只作为 fallback 使用。
正常请求不读缓存，始终拉取最新数据。
```

### 6.3 净值/限额缓存

```
结构: {"data": DataFrame, "time": Timestamp}
TTL: PURCHASE_CACHE_TTL_SECONDS = 300 秒（5 分钟）
位置: back/app/cache.py:8-9

写入: fetch_purchase_data() 成功拉取后
读取: fetch_purchase_data() 检查 is_purchase_cache_valid()
      有效 → 返回缓存副本（.copy()）
      无效 → 重新拉取

重要性：净值/限额涉及 ~15000 只基金，全量拉取需 ~1-2s。
        每天变化一次，5 分钟缓存大幅降低外部 API 调用。
```

### 6.4 基金类型缓存

```
结构: {"161226": "商品型基金", "160213": "QDII", ...}
TTL: 无 TTL，程序生命周期
位置: back/app/routers/lof.py:25

写入: get_fund_type() 首次查某个基金类型时爬页面
读取: get_fund_type() 检查 fund_code in _fund_type_cache

基金类型几乎不会变化，程序运行期间缓存即可。
```

### 6.5 代码位置

`back/app/cache.py:1-47`

---

## 7. 关键设计决策与边界情况

### 7.1 绕过 akshare，直接调东方财富接口

**背景：** akshare 封装了东方财富 API，但部分 akshare 内部域名已失效，且速度慢。

**决策：**
- `fetch_spot_data()` — 直接调 `push2delay.eastmoney.com`
- `fetch_purchase_data()` — 直接调 `fund.eastmoney.com`（auth 解析优化）
- `fetch_estimate_data()` — 直接调 `api.fund.eastmoney.com`

**保留 akshare 作为 fallback**：仅在直接请求失败时降级使用（`ak.fund_purchase_em()`, `ak.fund_value_estimation_em()`）。

### 7.2 JSON 解析优化

**问题：** 东方财富净值接口返回 `var reData={...};` 格式（JS 变量赋值），不是合法 JSON。

**传统方案：** `demjson` 库（纯 Python 实现）解析，约 1.5s。

**优化方案：**
```python
# 1. 去掉 JS 包装
clean_text = text[len("var reData="):].rstrip(";")
# 2. 正则给无引号 key 加双引号
valid_json = re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', clean_text)
# 3. CPython 实现的 json.loads() 解析
data_json = json.loads(valid_json)
```

**效果：** 从 ~1.5s 降至 ~10ms，约 **150 倍**加速。

### 7.3 同花顺换手率精度问题

**问题：** 同花顺 K 线数据换手率只保留 **3 位小数**（如 `1.252%`）。

**影响：** 对于低换手率基金（如 161226 白银基金，日换手率约 1%-2%）：
```
份额 = 成交量(股) / (换手率/100) / 10000
      = 12,500,000 / (0.0125/100) / 10000  ← 实际 1.252%，截断为 1.25%
      ≈ 10,000 万份  vs  实际 9,840 万份  ← 误差 ~160 万份

更极端时误差可达 ~40 万份
```

**缓解方案：** 用东方财富 `f84` 字段（实时总份额）校准最新一天的数据。f84 是大整数（股），精度远高于基于百分比的推算，对 LOF 基金误差 < 1%。偏差 < 5% 时直接替换。

**代码位置：** `back/app/routers/lof.py:128-143`

### 7.4 QDII 净值延迟匹配

**背景：** QDII 基金投资海外市场，净值计算和公布有 1 个交易日的延迟。当日市场看到的"最新净值"实际是前一交易日的净值。

**处理：**
```
非 QDII: T 日价格 ←→ T 日净值
QDII:    T 日价格 ←→ T-1 日净值（prev_date = date.shift(1)）
```

**判定依据：** 爬取东方财富基金基本概况页面的"基金类型"，如果包含 "QDII" 字样则为 QDII。

### 7.5 同花顺 year.js 缓存延迟

**问题：** 同花顺 `year.js` 文件有 CDN 缓存，当天最新的 K 线数据可能延迟几分钟才更新。

**检测方法：** 当天 K 线的价格、成交额与东方财富实时报价对比。

**校准触发条件（同时满足）：**
1. 最新一天日期 == 今天
2. 价格偏差 > 0.1% **或** 成交额偏差 > 50%

**代码位置：** `back/app/routers/lof.py:100-123`

### 7.6 份额 shift(1) 逻辑

**背景：** LOF 基金的场内份额由中登公司（中国结算）在 T 日收盘后结算，T+1 日公布。T 日盘后公布的份额对应 T 日终的状态。

**处理：** `share_volume = share_volume.shift(1)` — 将份额数据向下偏移一天，使 T 日的行显示 T-1 日的份额，因为 T 日盘中的份额要到 T+1 日才能看到。

### 7.7 并行拉取

**API 端点和告警系统都使用 `ThreadPoolExecutor(max_workers=3)`** 并行拉取三个数据源：

```
串行: spot(3s) → purchase(2s) → estimate(3s) = 8-9s
并行: max(spot(3s), purchase(2s), estimate(3s)) ≈ 3-4s
```

节省约 50-60% 的等待时间。使用 `future.result(timeout=30)` 限制单次超时。

### 7.8 超时与异常降级

| 场景 | 处理 |
|------|------|
| 3 个 future 任一超时 | 检查 LOF 实时缓存，有则返回缓存数据（标记 cached=true），无则 500 |
| 同花顺 K 线失败 | 降级到东方财富 K 线 |
| 东方财富 K 线失败 | 5 次重试（递增延迟），全失败返回 None → 接口返回 404 |
| 净值直接解析失败 | 降级到 akshare |
| 估算净值失败 | 降级到 akshare |
| 基金类型获取失败 | 返回空字符串，按非 QDII 处理 |
| 实时校准失败 | 跳过校准，使用原始 K 线数据 |
| API 地址未配置 | 告警静默跳过（日志记录） |

---

## 8. 附录

### 附录 A：/api/lof 字段映射表

| 源字段（中文） | 输出字段（英文） | 类型 | 说明 |
|----------------|------------------|------|------|
| 代码 | `fundCode` | string | 6 位基金代码 |
| 名称 | `fundName` | string | 基金名称 |
| 最新价 | `tradePrice` | float | 最新成交价（元） |
| 涨跌幅 | `increaseRate` | float | 涨跌幅（%） |
| 最新净值/万份收益 | `netValue` | float | 最新收盘净值 |
| 估算净值 | `estimateValue` | float | 实时估算净值 |
| 溢价率 | `premiumRate` | float | 静态溢价率（%），vs 收盘净值 |
| 估算溢价率 | `estimatePremiumRate` | float | 估算溢价率（%），vs 估算净值 |
| 限额 | `purchaseLimit` | string | 格式化后的申购限额 |
| 申购状态 | `purchaseStatus` | string | 开放/暂停/限大额 |
| 总市值_格式化 | `fundSize` | string | 格式化后的总市值 |
| 成交量 | `volume` | float | 成交量（手） |
| 成交额_格式化 | `turnover` | string | 格式化后的成交额 |

### 附录 B：/api/lof/history 字段映射表

| 源字段（内部） | 输出字段（英文） | 类型 | 说明 |
|----------------|------------------|------|------|
| date | `date` | string | 交易日期（YYYY-MM-DD） |
| price | `price` | float | 收盘价（元） |
| nav_date | `navDate` | string 或 null | 匹配的净值日期 |
| nav | `nav` | float 或 null | 单位净值 |
| premium_rate | `premiumRate` | float 或 null | 溢价率（%） |
| turnover | `turnover` | float | 成交额（万元） |
| share_volume | `shareVolume` | float 或 null | 场内份额（万份） |
| change_amount | `changeAmount` | float 或 null | 份额日变动量（万份） |
| change_pct | `changePct` | float 或 null | 份额日变动率（%） |

### 附录 C：告警字段映射表

| 输出字段 | 来源 | 格式 |
|----------|------|------|
| `fund_code` | 代码 | 字符串 |
| `fund_name` | 名称 | 字符串 |
| `on_exchange_price` | 最新价 | `_fmt_num`，如 "0.992" |
| `off_exchange_nav` | 最新净值/万份收益 | `_fmt_num` |
| `estimated_nav` | 估算净值 | `_fmt_num` |
| `price_change` | 涨跌幅 | `_fmt_pct`，如 "+0.50%" |
| `premium_rate_yesterday` | 溢价率（静态） | `_fmt_pct` |
| `premium_rate_realtime` | 估算溢价率 | `_fmt_pct` |
| `daily_limit` | 日累计限定金额 | `format_limit` |
| `subscription_suspended` | 申购状态 | "是"/"否" |
| `fund_size` | 总市值 | `format_amount` |
| `trading_volume` | 成交额 | `format_amount` |

### 附录 D：环境变量配置参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOF_BACKEND_PORT` | `8000` | FastAPI 服务端口 |
| `LOF_ALERT_CRON_HOURS` | `11,14` | 告警触发小时（北京时间） |
| `LOF_ALERT_CRON_DAYS` | `mon-fri` | 告警触发星期 |
| `LOF_ALERT_MAX_COUNT` | `5` | 每次推送最大基金数 |
| `LOF_ALERT_SEND_DELAY_SECONDS` | `0.5` | 推送间隔（秒） |
| `LOF_ALERT_API_BASE_URL` | `""` | 飞书通知服务地址，为空则跳过 |

### 附录 E：外部 API 速查表

| 用途 | URL | 调用时机 | 缓存 |
|------|-----|----------|------|
| 实时行情 | `push2delay.eastmoney.com/api/qt/clist/get` | 每次 /api/lof 请求 | 无 |
| 净值/限额 | `fund.eastmoney.com/Data/Fund_JJZJ_Data.aspx` | 每次请求，读缓存跳过 | 5min |
| 估算净值 | `api.fund.eastmoney.com/FundGuZhi/GetFundGZList` | 每次 /api/lof 请求 | 无 |
| 历史 K 线（主） | `d.10jqka.com.cn/v6/line/hs_{code}/01/{year}.js` | 每次 /history 请求 | 无 |
| 历史 K 线（备） | `push2his.eastmoney.com/api/qt/stock/kline/get` | 同花顺失败时 | 无 |
| 历史净值 | `api.fund.eastmoney.com/f10/lsjz` | 每次 /history 请求 | 无 |
| 实时报价 | `push2.eastmoney.com/api/qt/stock/get` | 校准/填充份额时 | 无 |
| 基金类型 | `fundf10.eastmoney.com/jbgk_{code}.html` | 首次查某基金 | 程序生命周期 |
