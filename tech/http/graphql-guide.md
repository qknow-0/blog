# GraphQL：让客户端决定要什么数据

> REST 里你调 `/users/42` 拿到整个 User 对象——包括你不想要的 20 个字段。调 `/users/42/orders` 再拿一次。前端说「我只要名字和最近 3 个订单」，后端说「不行，我返回什么你接什么」。GraphQL 的设计初衷就是解决这个矛盾。

## 是什么

[GraphQL](https://graphql.org) 是 Facebook 2015 年开源的查询语言。核心理念和 REST 刚好相反：**服务端定义数据图谱，客户端指定要什么字段**。

```text
REST：    服务端决定返回结构 → 客户端被动接受 → 多拿或少拿字段
GraphQL： 客户端写查询 → 服务端精确返回 → 一次请求，不多不少
```

## 一个例子胜过千言

你要做一个用户资料页，需要姓名、头像、最近 3 个订单的金额和状态。

**REST 方式**（至少 2 个请求）：

```text
GET /users/42    → { id, name, email, phone, avatar, created_at, updated_at, ... }
GET /users/42/orders?limit=3  → [{ id, amount, status, items: [...], ... }]
```

拿回来一大堆不需要的字段——`email`、`phone`、`created_at`、订单里的 `items` 数组。

**GraphQL 方式**（1 个请求，精确字段）：

```graphql
query {
  user(id: 42) {
    name
    avatar
    orders(last: 3) {
      amount
      status
    }
  }
}
```

返回——**不多一个字段**：

```json
{
  "data": {
    "user": {
      "name": "张三",
      "avatar": "https://cdn.example.com/avatars/42.jpg",
      "orders": [
        { "amount": 299.00, "status": "paid" },
        { "amount": 159.00, "status": "shipped" },
        { "amount": 89.00, "status": "pending" }
      ]
    }
  }
}
```

## 核心概念

### Schema——数据图定义

```graphql
type User {
  id: ID!
  name: String!
  email: String!
  avatar: String
  orders(last: Int): [Order!]!  # 关联到订单
}

type Order {
  id: ID!
  amount: Float!
  status: OrderStatus!
  user: User!
}

enum OrderStatus {
  pending
  paid
  shipped
  cancelled
}

type Query {
  user(id: ID!): User
  orders(status: OrderStatus): [Order!]!
}

type Mutation {
  createOrder(userId: ID!, amount: Float!): Order!
  cancelOrder(id: ID!): Order!
}
```

Schema 是 GraphQL 的灵魂——它是前端和后端之间的**类型契约**。不像 REST 靠文档，GraphQL 靠类型系统自动生成文档。

### Query——读

```graphql
query {
  user(id: 42) {
    name
    orders(status: paid) {
      amount
    }
  }
}
```

### Mutation——写

```graphql
mutation {
  createOrder(userId: 42, amount: 299.00) {
    id
    amount
    status
  }
}
```

`mutation` 和 `query` 语法上没区别，但**语义上 mutation 是串行执行的**（防止并发写冲突），query 可以并行。

### Subscription——实时推送

```graphql
subscription {
  orderStatusChanged(userId: 42) {
    orderId
    newStatus
  }
}
```

WebSocket 长连接，服务端有变化主动推给客户端。

## 和 REST 的对比——什么时候用哪个

| | REST | GraphQL |
|---|---|---|
| 数据获取 | 服务端控制 | **客户端控制** |
| 请求次数 | 可能需要多个 | **一次** |
| 冗余数据 | 常有 | **没有** |
| 缓存 | HTTP 原生支持 | **需要自己搞** |
| 学习成本 | 低 | 中 |
| 工具链 | 任何 HTTP 客户端 | Apollo/Relay 等 |
| 错误处理 | HTTP 状态码 | 都是 200，错误放 body |
| 文件上传 | 原生支持 | 需要插件 |
| 适合场景 | 简单 CRUD | 复杂关联查询 |

### 什么时候用 GraphQL

- 前端需要灵活的数据组合（移动端弱网场景尤其受益）
- 数据之间有复杂的关联关系（社交网络、电商）
- 多个客户端（Web、iOS、Android）需要不同字段

### 什么时候继续用 REST

- 简单 CRUD——GraphQL 的复杂度不值得
- 需要 HTTP 缓存——GraphQL 通常 POST，CDN 不好缓存
- 文件上传——REST 的 multipart 更成熟
- 团队没有前端深度参与 API 设计

## 常见陷阱

**1. N+1 查询**

```graphql
query {
  users {       # 1 次查询拿到 100 个用户
    name
    orders {    # 每个用户再查一次 → 100 次额外查询
      amount
    }
  }
}
```

解法：**DataLoader**——批量查询，把 100 个 `SELECT * FROM orders WHERE user_id = ?` 合并成一条 `WHERE user_id IN (...)`。

**2. 深度嵌套 DDOS**

```graphql
query {
  user {
    orders { user { orders { user { orders { ... } } } } }
  }
}
```

解法：**限制查询深度**（`max_depth: 5`）和**复杂度计算**（每个字段加权，超阈值拒绝）。

**3. 过度暴露**

给前端开了所有字段的查询权限，内部字段 `internal_notes` 也暴露了。解法：**字段级别的权限控制**。

## 小结

GraphQL 不是 REST 的替代品，是另一种思路——**当你的数据有复杂关联、客户端需要灵活组合时**，GraphQL 省下的请求和带宽值得它带来的复杂度。大多数内部管理后台用 REST 就够了。

---

**相关阅读：**
- [RESTful API 设计](restful-api-guide.md)
- [gRPC：微服务间通信的最优解](grpc-guide.md)
- [HTTP 协议系列](index.md)
