# 防腐层与上下文映射：模块之间怎么划界

> 系列：企业应用架构（17/19）。代码用 Python 3.12 演示。

## 生活比喻：电源转换插头

你带电器出国，发现插座形状不一样。**你不会去改造电器**——你买一个转换插头。

转换插头的作用就三条：

- **你的电器不用为别人的插座改造自己**
- **插座标准变了，你换转接头，不改电器**
- **转接头上有明确的规格**（国标转美标），插错了当场就知道

**防腐层就是软件里的转换插头。** 上游系统的模型是「别人的插座」，你的领域模型是「你的电器」，中间那层翻译就是防腐层。

## 什么是防腐层

> **防腐层（Anti-Corruption Layer，ACL）位于两个上下文之间，负责双向翻译，让下游的领域模型不被上游的模型污染。**

「防腐」这个名字很准——它防的是**概念污染**：如果下游直接用上游的模型，上游的术语、假设、甚至它的设计缺陷都会渗进你的领域层。

## 反例：没有防腐层会怎样

上游 CRM 系统返回这样的数据：

```python
CRM_V1 = {"cust_nm": "张三", "tier_cd": "GOLD", "reg_dt": "2024-03-01"}
```

**没有防腐层时，领域对象直接吃这个字典：**

```python
# ❌ 领域对象依赖上游原始结构
class BadCustomer:
    def __init__(self, raw: dict):
        self.name = raw["cust_nm"]           # ← 上游字段名泄漏进领域层
        self.tier = raw["tier_cd"]
        self.registered = raw["reg_dt"]

    def is_vip(self) -> bool:
        return self.tier in ("GOLD", "PLATINUM")     # ← 上游的枚举值也进来了
```

**三个月后，上游做了一次「命名规范重构」**——它觉得这是纯技术改动，发了个 changelog 就上线了：

```python
CRM_V2 = {"customer_name": "张三", "tier_code": "GOLD", "registered_at": "2024-03-01"}
```

```console
  【无防腐层】
    ❌ KeyError: 'cust_nm'
    ↑ 异常发生在领域对象内部 —— 上游的技术重构震碎了领域层
```

**注意异常发生在哪**：在 `BadCustomer.__init__` 里。**上游一个字段改名，直接震到了你的领域对象。**

**而且问题不只是「炸了一次」**——真正的问题是：

- 领域层里现在到处是 `cust_nm` 这种缩写**（上游的历史包袱变成了你的）**
- 上游的枚举值 `STANDARD` / `GOLD` 变成了你业务规则的一部分
- 上游每次改动，你都要改领域层——**领域层的稳定性取决于一个你不控制的系统**

## 加上防腐层

```python
class CustomerTier:
    """领域自己的枚举 —— 完全不知道上游怎么编码"""
    NORMAL, GOLD, PLATINUM = "normal", "gold", "platinum"


class Customer:
    """纯领域对象 —— 没有一个字段名来自上游"""
    def __init__(self, name: str, tier: str, registered_at: str):
        self.name = name
        self.tier = tier
        self.registered_at = registered_at

    def is_vip(self) -> bool:
        return self.tier in (CustomerTier.GOLD, CustomerTier.PLATINUM)


class CrmAcl:
    """防腐层：唯一知道上游长什么样的地方"""

    # ★ 上游编码 → 领域枚举：这张表也属于边界，不属于领域
    _TIER_MAP = {"STANDARD": CustomerTier.NORMAL,
                 "GOLD": CustomerTier.GOLD,
                 "PLATINUM": CustomerTier.PLATINUM}

    def __init__(self, field_map: dict):
        self._FIELD_MAP = field_map          # ← 全部的变化面就是这一张表

    def to_domain(self, raw: dict) -> Customer:
        missing = set(self._FIELD_MAP.values()) - set(raw)
        if missing:
            raise ValueError(f"上游结构变了，缺少: {sorted(missing)}")
        return Customer(
            name=raw[self._FIELD_MAP["name"]],
            tier=self._to_tier(raw[self._FIELD_MAP["tier"]]),
            registered_at=raw[self._FIELD_MAP["registered"]],
        )
```

**注意 `_TIER_MAP` 放在了 ACL 而不是 `CustomerTier` 里。** 领域枚举不该知道「上游用 STANDARD 表示普通」——**那是边界的事**。

上游改名之后：

```console
  【有防腐层，但还没更新映射】
    ⚠️  上游结构变了，缺少: ['cust_nm', 'reg_dt', 'tier_cd']
    ↑ 在边界上失败 —— 脏数据根本没进来，领域层毫发无伤

  【修防腐层：只改三个映射值】
    ACL_V1 = CrmAcl({"name": "cust_nm", "tier": "tier_cd", ...})
    ACL_V2 = CrmAcl({"name": "customer_name", "tier": "tier_code", ...})
    → 尊敬的贵宾客户 张三

  【领域层改动量】Customer + CustomerTier 源码：未改变 ✅
```

**两条输出值得对比：**

- **无防腐层**：`KeyError` 抛在领域对象内部
- **有防腐层**：错误抛在边界上，**而且信息是「上游结构变了」**——直接指出了问题在哪

**这就是防腐层最实际的价值**：不是「代码更优雅」，是**上游改动时你能一眼定位，而且改动被限制在一个文件里**。

### 验收标准

```console
领域模型里还有上游的影子吗？
  上游专有字段/编码出现次数: 0  （无）
```

**这是个可以机械检查的硬指标**：`grep` 一下上游的字段名，领域层里应该一个都找不到。

## 上下文映射：不止防腐层一种关系

两个上下文之间的关系不止「加防腐层」一种。DDD 里总结了几种，**按耦合度从高到低**：

| 关系 | 含义 | 什么时候用 |
|------|------|-----------|
| **共享内核**<br/>Shared Kernel | 两个团队**共享一块模型代码** | 团队在同一屋檐下、模型确实一致 |
| **客户-供应商**<br/>Customer/Supplier | 上游**有义务**考虑下游的需求 | 同一个公司的两个团队 |
| **遵奉者**<br/>Conformist | 下游**完全照抄**上游模型，不做翻译 | 上游强势且模型够用；你不想维护翻译层 |
| **防腐层**<br/>ACL | 下游**加一层翻译** | 上游模型不适合你的领域 |
| **开放主机服务 + 发布语言**<br/>OHS + PL | 上游提供**稳定的公开接口 + 文档化格式** | 上游要服务很多下游 |
| **各行其道**<br/>Separate Ways | **不集成** | 集成的成本超过收益 |

```mermaid
flowchart LR
    A["共享内核<br/>共用一块代码"] --> B["客户-供应商<br/>上游听下游的"]
    B --> C["遵奉者<br/>下游照抄上游"]
    C --> D["防腐层<br/>下游加翻译"]
    D --> E["OHS+PL<br/>上游提供稳定契约"]
    E --> F["各行其道<br/>不集成"]

    style A fill:#3e1a1a,stroke:#e94560,color:#fff
    style B fill:#3e1a1a,stroke:#e94560,color:#fff
    style C fill:#533483,stroke:#e94560,color:#fff
    style D fill:#0f3460,stroke:#e94560,color:#fff
    style E fill:#16213e,stroke:#e94560,color:#fff
    style F fill:#1a2e1b,stroke:#53d769,color:#fff
```

**从左到右：耦合降低，但要自己付出的成本上升。**

**遵奉者和防腐层的取舍最值得注意**：

- **遵奉者**：直接用上游模型。省了翻译层，但**你的领域模型从此由上游定义**
- **防腐层**：加翻译层。多写代码，但**领域模型你自己说了算**

**什么时候选遵奉者？** 当上游的模型**恰好就是你要的**——比如你只是展示它的数据，没有任何自己的业务规则要加。这时候防腐层是纯粹的浪费。

## 什么时候需要防腐层

| 场景 | 建议 |
|------|------|
| 你的领域有**自己的业务规则**，要加在上游数据之上 | **需要** |
| 上游模型**不符合你的术语**（`cust_nm` vs `name`） | **需要** |
| 上游是**第三方、你不控制它的演进** | **需要** |
| 上游模型**经常变** | **需要** |
| 你只是**原样展示**上游数据 | **不需要**——遵奉者就够 |
| 上游模型和你的领域**基本一致** | **不需要** |
| 集成成本 > 收益 | **不集成** |

**判断标准**：

> **上游的模型如果变坏（改字段名、加奇怪的枚举、设计倒退），会不会污染我的领域？**

- 会 → 防腐层
- 不会（我只是透传）→ 遵奉者

**注意「加一层翻译」不该是默认动作**——它会带来一个必须维护的映射表。**只有在「防止污染」这个收益真实存在时才值得。**

## 三种粒度的防腐层

实践中防腐层有三种实现粒度：

| 粒度 | 做法 | 适合 |
|------|------|------|
| **函数级** | 一个 `to_domain(raw) -> Domain` 函数 | 单一接口、模型简单 |
| **类级** | 一个 `XxxAcl` 类，管一个上游系统的全部翻译 | 一个上游系统 |
| **网关级** | 独立的服务/模块，上游调用都经过它 | 多个上游、要统一治理 |

**大多数场景函数级或类级就够。** 网关级通常出现在「上游特别多」或「要有统一的熔断/限流/审计」时——那已经超出了「防腐」的范围，更接近 API 网关。

## 总结

| 维度 | 无防腐层 | 有防腐层 |
|------|---------|---------|
| 领域模型里的字段名 | 上游的（`cust_nm`） | **自己的**（`name`） |
| 上游改字段名 | **领域层炸** | 改映射表 |
| 错误发生位置 | 领域对象内部 | **边界上，信息明确** |
| 领域层的稳定性 | 取决于上游 | **自己控制** |
| 代价 | — | 一层翻译 + 一张要维护的映射表 |

**三条结论：**

1. **防腐层防的是「概念污染」，不是「接口变化」。** 接口变了改代码就行；概念污染是**你的领域模型从此由别人定义**。

2. **领域枚举的上游编码映射应该放在 ACL，不该放在领域枚举里。** 领域对象不该知道「上游用 STANDARD 表示普通」。

3. **不是所有关系都该加防腐层。** 如果只是透传展示，遵奉者更省事；如果集成成本超过收益，各行其道才是对的。

DDD 部分到此结束。最后两篇换两个角度收尾——[第 18 篇](18-cqrs-event-sourcing.md)讲两个现代的进阶模式，[第 19 篇](19-when-overkill.md)讲**什么时候这些全是过度设计**。

---

**相关文章：** [限界上下文](16-bounded-context.md) · [聚合根](15-aggregate-root.md) · [六边形 / 洋葱 / Clean](10-hexagonal-onion-clean.md) · [总纲](00-overview.md)
