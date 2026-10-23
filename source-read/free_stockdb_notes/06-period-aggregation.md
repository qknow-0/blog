# free-stockdb 源码阅读（六）：周 K、月 K 与分钟 K 的时间轴

> 基于 commit `f352641`，2026-10-05。
> 系列：free-stockdb 源码阅读（6/10）。

## 一句话概括

free-stockdb 的底层只存日 K 和 1 分钟 K；周 K、月 K、5/15/30/60 分钟 K 都是**查询时在内存里合成**的。

这条路线的好处是存储小、口径可调；代价是每次查询都要重新聚合，而且聚合逻辑要在 Python、WPS JS、HTML 等多套客户端里各写一遍。

## 日 K → 周 K / 月 K

`_merge_to_period`（`stock_sdk.py:128-244`）先分组，再聚合：

```python
if frequency == '1w':
    iso = dt.isocalendar()
    key = (iso[0], iso[1])       # (ISO 年, ISO 周)
elif frequency == '1M':
    key = (dt.year, dt.month)    # (年, 月)
```

聚合规则是标准的 OHLCV 合成：

| 字段 | 规则 |
|------|------|
| `open` | 周期内第一根日 K 的 open |
| `high` | 周期内最高 high |
| `low` | 周期内最低 low |
| `close` | 周期内最后一根日 K 的 close |
| `volume` | 求和 |
| `amount` | 求和 |
| `turnover` | 求和 |
| `vol_ratio` | 求均值 |
| `date` | 周期内最后一个交易日的日期 |
| `pe_ttm` / `pb` / `total_mv` / `float_mv` | 取最后一根日 K 的截面值 |

派生字段：

- `pre_close`：优先用上一个合成周期的 `close`；第一个周期退回到第一根日 K 的 `pre_close`，再退回 `open`；
- `pct_chg = (close - pre_close) / pre_close * 100`；
- `amplitude = (high - low) / pre_close * 100`。

这里有一个容易被忽略的正确性细节：**如果某一组缺少任意一个 OHLC 字段，就跳过整组**。

```python
# stock_sdk.py:185-187
if not (open_values and high_values and low_values and close_values):
    continue
```

为什么不能拿 0 代替缺失值？因为 0 会把 `low` 拉成 0，把 `amplitude` 拉到 100%，产生一根看起来很正常、其实完全错误的 K 线。**缺失不是 0，缺失是不能构成一根 K 线。**

## 1 分钟 K → 5/15/30/60 分钟 K

分钟 K 的难点不是聚合，而是**交易时段不是连续的**：9:30–11:30，午休，13:00–15:00。如果直接按自然时间每 5 分钟切，午休会被算进某一根 K 线，下午的第一根也会错位。

代码用了一个"交易分钟"映射（`stock_sdk.py:258-265`）：

```python
def trading_elapsed(minute_of_day: int) -> Optional[int]:
    if 570 <= minute_of_day <= 690:          # 9:30 - 11:30
        return minute_of_day - 570           # 0 .. 120
    if 780 <= minute_of_day <= 900:          # 13:00 - 15:00
        if minute_of_day == 780:
            return 121                       # 13:00 特殊处理
        return 120 + (minute_of_day - 780)   # 13:01 -> 121, 15:00 -> 240
    return None                              # 非交易时间
```

```mermaid
flowchart LR
    A["09:30"] -->|"elapsed 0"| B["上午 0..120"]
    B --> C["11:30 elapsed 120"]
    C --> D["午休：不参与分组"]
    D --> E["13:00 elapsed 121"]
    E --> F["下午 121..240"]
    F --> G["15:00 elapsed 240"]
```

`13:00` 为什么要单独返回 `121`？因为如果直接算 `120 + (780-780) = 120`，13:00 会和 11:30 落在同一个交易日历位置，跨午休合并。特殊处理把 13:00 推到 121，保证它属于下午的第一组。

分组键是**对齐后的结束时刻**：

```python
# stock_sdk.py:299-307
if elapsed <= 0:
    group_end_elapsed = interval
else:
    group_idx = (elapsed - 1) // interval
    group_end_elapsed = (group_idx + 1) * interval

key = (ymd, group_end_elapsed)
```

例如 5 分钟周期（仅 Python/HTML 的实现）：9:30 和 9:31–9:35 归到 `9:35` 这一组；11:30 归到 `11:30`；13:00 和 13:01–13:05 归到 `13:05`。最后再映射回 `YYYYMMDDHHMMSS`：

```python
aligned_date_int = ymd * 1000000 + end_hour * 10000 + end_minute * 100
```

聚合字段和日 K 类似：first open、max high、min low、last close、sum volume/amount，然后算出 `pre_close`、`pct_chg`、`amplitude`，并把 `vol_ratio`、`pe_ttm`、`pb` 等截面字段从最后一根分钟 K 复制过来。

但分钟路径和日 K 路径并不完全一样：

```python
# stock_sdk.py:319-322
high = max(x['high'] for x in items if 'high' in x)
low = min(x['low'] for x in items if 'low' in x)
volume = sum(x['volume'] for x in items if 'volume' in x)
amount = sum(x['amount'] for x in items if 'amount' in x)
```

它只检查字段是否存在，不检查值是否为 `None`。如果某根分钟 K 的 `high` 或 `volume` 是 `None`，这里会直接 `TypeError`；它也没有像日 K 路径那样计算 `turnover` 求和、`vol_ratio` 均值，而是从最后一根原样复制。**"缺失不是 0" 这个原则只落实到日 K 路径，没有落实到分钟路径。**

> 首根 bar 的归属（9:30 是代表 9:30 这一分钟，还是 9:29–9:30）取决于数据源的时间戳约定。代码把 9:30 和 13:00 当作特殊起点，读的时候要结合上游数据确认，不要只看函数名。

## 为什么在内存里合成，而不是预计算

| 方案 | 优点 | 缺点 |
|------|------|------|
| 查询时合成（当前） | 存储只保留日 K/1m；口径可改；新增周期不改库 | 每次查询重复计算；大结果集慢 |
| 预计算所有周期 | 查询快 | 存储膨胀；口径变更要回刷；复权后要重算 |
| 物化视图/增量表 | 兼顾 | 工程复杂度高；需要调度和一致性保证 |

free-stockdb 选择了第一种。它符合"本地研究"场景：查询频率不高，数据量在单机可接受范围内，口径灵活性比极致延迟更重要。

## 代价：多端副本，而且分钟实现已经分叉

这是读这个仓库最明显的工程问题，但问题不只是"重复"，而是**重复的实现已经不等价**。

| 位置 | 日→周/月 | 分钟→多分钟 | 交易时段对齐 |
|------|----------|-------------|--------------|
| Python SDK | `stock_sdk.py:128` | `stock_sdk.py:246` | ✅ 9:30–11:30 / 13:00–15:00 |
| HTML 页面 | `数据网页版.html:1015` | `数据网页版.html:1102` | ✅ 有交易分钟映射 |
| WPS JS 宏 | `wps_js_macro.js:239` | `wps_js_macro.js:337` | ❌ 直接按自然分钟分组 |
| `http_js.js` | `http_js.js:237` | `http_js.js:335` | ❌ 直接按自然分钟分组 |

WPS 和 `http_js.js` 的分钟合成用的是自然时间：

```javascript
// wps_js_macro.js:356-360（http_js.js 同）
const totalMinutes = hour * 60 + minute;
const groupIdx = Math.floor((totalMinutes - 1) / interval);
```

于是同一个 `frequency="5m"`，不同客户端会得到不同的 bar：

- Python/HTML 把 9:30 和 9:31–9:35 合成 `9:35`；WPS/`http_js.js` 把 9:30 单独作为一根 `9:30`。
- 午休后，Python/HTML 从 13:05 开始对齐；WPS/`http_js.js` 会生成一根 `13:00`。
- 60 分钟周期下，WPS 甚至会把 11:01–11:30 这一组标成 `12:00`。

**同名周期在不同客户端返回不同时间轴，比代码重复危险得多。** 这已经不是"以后重构"的问题，而是需要黄金样例测试立刻锁住的行为差异。

为什么会有多份实现？因为这些客户端要"零依赖、双击即用"：WPS 宏不能 import Python，HTML 不能假定用户装了 pandas，MCP 之外也不想再装一个服务。于是它们各自带一份复权和聚合逻辑。

合理的改进方向：

1. 把聚合/复权下沉到服务端，客户端只传 `frequency`/`fq`，但这会改变 HTTP 协议，增加服务端计算压力；
2. 提供一个可选的 JS 共享库，WPS/HTML 共用一份；
3. 至少用同一组测试向量（黄金样例）锁住**所有**实现的行为，并明确以哪一端为准。

**这里真正值得学的是：当你要为多个运行环境提供同一套计算时，先决定"计算放在哪一层"，再决定要不要复制；一旦复制，必须用测试证明副本等价。**

## 优秀代码：用 `None` 表示缺失，而不是 0

```python
# stock_sdk.py:175-194
def valid_values(field):
    return [x[field] for x in items if x.get(field) is not None]

volume_values = valid_values('volume')
volume = sum(volume_values) if volume_values else None
```

这段代码把"没有观测值"与"观测值为 0"区分开了。停牌日通常没有记录；如果某天有不完整的记录，缺失字段也不能参与求和。用 `None` 传递"不知道"，比用 0 传递"确定是 0"更接近事实。

**模式**：Nullable / Missing Value Semantics。金融数据里，"0"和"没有数据"必须分开。

> 注意：这只是日 K→周/月 K 路径的实现。分钟 K 路径没有复用这套 `valid_values`，`None` 仍可能在 `max`/`sum` 里炸掉，见上一节。

## 骨架代码：按交易分钟分组

```python
def trading_elapsed(hhmm: int) -> int | None:
    if 930 <= hhmm <= 1130:
        return (hhmm // 100 - 9) * 60 + hhmm % 100 - 30
    if 1300 <= hhmm <= 1500:
        if hhmm == 1300:
            return 121          # 下午第一根，避免和 11:30 的 120 冲突
        return 120 + (hhmm // 100 - 13) * 60 + hhmm % 100
    return None

def group_key(dt: datetime, interval: int):
    elapsed = trading_elapsed(dt.hour * 100 + dt.minute)
    if elapsed is None:
        return None
    end = ((elapsed - 1) // interval + 1) * interval if elapsed > 0 else interval
    return dt.date(), end
```

**模式**：把"自然时间"映射成"交易时间轴"，再在交易时间轴上做等距切分。不要直接对自然时间做除法。

## 下一章

周期合成解决了"时间怎么对齐"。下一章看另一个影响正确性的维度：**复权**——全市场因子、二分查找和内存折算。

---

> 系列导航：[（五）Python SDK](05-python-sdk.md) · [（七）复权](07-adjustment.md)
