# RESTful API 设计：让接口像对话一样自然

> 好的 API 不需要文档——你看到 `/users/42/orders?status=paid` 就知道它在查什么。差的 API 看一眼 URL 就头疼：`/getUserOrders?uid=42&type=1`。区别在于是否遵循了 REST。

## 是什么

REST（Representational State Transfer）是 Roy Fielding 2000 年博士论文里提出的架构风格。它不是协议，不是标准，是一套**设计约束**。

```text
REST ≠ "用 HTTP 的接口"（那是 HTTP API）
REST = 满足六大约束的 HTTP API
```

现实是：90% 自称 RESTful 的 API 只是「用了 HTTP 方法 + JSON 格式的接口」，并不满足全部约束。够用就行。

## 核心约束

Fielding 定义了六个约束，其中前三个最关键：

| 约束 | 含义 | 怎么体现 |
|---|---|---|
| **客户端-服务器** | 前端不关心数据怎么存的，后端不关心界面长什么样 | `/api/orders` 返回 JSON，前端自己渲染 |
| **无状态** | 每个请求自包含全部信息，服务器不记客户端状态 | Token 放 Header，不带 Session Cookie |
| **统一接口** | 用一致的 URL + HTTP 方法 + 状态码交互 | 查就是 GET，建就是 POST，删就是 DELETE |
| 可缓存 | 响应声明自己能不能被缓存 | `Cache-Control: max-age=3600` |
| 分层系统 | 客户端不知道中间有没有代理/负载均衡 | Nginx 反代，客户端只看到同一个域名 |
| 按需代码（可选） | 服务器可以发可执行代码给客户端 | 基本没人用 |

## URL 设计：资源，不是动作

```text
❌ POST /getUserOrders      # 动词
❌ POST /api?method=getOrders&userId=42  # RPC 风格

✅ GET /users/42/orders     # 名词（资源），层级关系
✅ GET /orders?user_id=42   # 也可以，扁平风格
```

URL 设计的核心原则：

```text
/资源/标识符/子资源/标识符

/users         ← 用户集合
/users/42      ← 42 号用户
/users/42/orders     ← 42 号用户的订单
/users/42/orders/15   ← 42 号用户的 15 号订单
```

层级**不超过 3 层**。太深了说明资源划分有问题：

```text
❌ /users/42/orders/15/items/3/refunds/1
✅ /refunds?order_item_id=3  # 扁平化
```

## HTTP 方法：动词要对

| 方法 | 操作 | 幂等 | 安全 |
|---|---|---|---|
| `GET` | 获取 | ✅ | ✅ |
| `POST` | 创建 | ❌ | ❌ |
| `PUT` | 全量替换 | ✅ | ❌ |
| `PATCH` | 部分修改 | ❌ | ❌ |
| `DELETE` | 删除 | ✅ | ❌ |
| `HEAD` | 只拿头 | ✅ | ✅ |
| `OPTIONS` | 看支持哪些方法 | ✅ | ✅ |

**幂等** = 调 1 次和调 100 次结果一样。PUT 是幂等的（反复提交同一个 JSON 还是那个资源），POST 不是（每次调都创建一个新的）。

```bash
# GET——查
GET /users/42

# POST——建
POST /users
{"name": "张三", "email": "zhangsan@example.com"}

# PUT——全量替换（不传 email 就会被清空）
PUT /users/42
{"name": "张三改", "email": "zhangsan@example.com"}

# PATCH——部分修改（只改名，email 不动）
PATCH /users/42
{"name": "张三改"}

# DELETE——删
DELETE /users/42
```

## 状态码：少而精

不需要记 60 多个状态码。实际项目里用到这十几个就够了：

### 成功

| 状态码 | 含义 | 什么时候用 |
|---|---|---|
| `200 OK` | 成功 | GET、PUT、PATCH 成功 |
| `201 Created` | 已创建 | POST 创建新资源成功 |
| `204 No Content` | 成功但没 body | DELETE 成功 |

### 重定向

| 状态码 | 含义 | 什么时候用 |
|---|---|---|
| `301 Moved Permanently` | 永久搬家 | 域名换了 |
| `304 Not Modified` | 没变化 | 缓存命中 |

### 客户端错误

| 状态码 | 含义 | 什么时候用 |
|---|---|---|
| `400 Bad Request` | 请求有问题 | JSON 格式错、参数校验失败 |
| `401 Unauthorized` | 没登录 | Token 过期或缺失 |
| `403 Forbidden` | 没权限 | 登录了但不是管理员 |
| `404 Not Found` | 资源不存在 | 用户 42 不存在 |
| `409 Conflict` | 冲突 | 重复创建、版本号不匹配 |
| `422 Unprocessable Entity` | 参数对但语义错 | 邮箱格式对但已被注册 |
| `429 Too Many Requests` | 频率限制 | 刷太快了 |

### 服务端错误

| 状态码 | 含义 | 什么时候用 |
|---|---|---|
| `500 Internal Server Error` | 服务器挂了 | 未预期的异常 |
| `502 Bad Gateway` | 上游挂了 | 网关连不上后端 |
| `503 Service Unavailable` | 维护中 | 主动停机 |

## 响应格式：统一信封

```json
// ✅ 成功
{
  "success": true,
  "data": {
    "id": 42,
    "name": "张三",
    "email": "zhangsan@example.com"
  }
}

// ❌ 失败
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "用户 42 不存在"
  }
}

// 📄 列表——加分页元数据
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

关键设计：

- **统一信封**——客户端不需要判断「这次返回的是数组还是对象」
- **`success` 字段**——不用 `if (response.status === 200)`，直接判断 `if (data.success)`
- **`error.code`**——机器可读的错误码，前端可以做 i18n 映射
- **不要暴露内部错误**——`500` 时返回 `"服务器内部错误"`，不是返回 stack trace

## 分页、过滤、排序

```bash
# 分页
GET /users?page=2&per_page=20

# 过滤
GET /users?status=active&role=admin

# 排序
GET /users?sort=-created_at   # - 表示倒序
GET /users?sort=name,-created_at  # 先按名字正序，再按时间倒序

# 字段筛选（只返回需要的字段）
GET /users?fields=id,name,email

# 搜索
GET /users?q=张三
```

**响应里必须返回分页元数据**：

```json
{
  "meta": {
    "page": 2,
    "per_page": 20,
    "total": 156,
    "total_pages": 8,
    "links": {
      "first": "/users?page=1",
      "prev": "/users?page=1",
      "next": "/users?page=3",
      "last": "/users?page=8"
    }
  }
}
```

## 版本控制

三种常见策略。推荐哪种取决于你的场景：

```bash
# 方式 1：URL 路径（最直观）
GET /api/v1/users/42
GET /api/v2/users/42

# 方式 2：请求头（URL 干净，但调试麻烦）
GET /api/users/42
Accept: application/vnd.myapp.v2+json

# 方式 3：查询参数（灵活，但缓存不友好）
GET /api/users/42?version=2
```

**内部 API 用 URL 路径**——最简单，谁都能看懂。**对外公开 API 用请求头**——URL 永久不变。

## REST vs 其他

| | REST | GraphQL | gRPC |
|---|---|---|---|
| 协议 | HTTP | HTTP | HTTP/2 |
| 数据格式 | JSON | JSON | Protobuf |
| 查什么 | 服务端定 | 客户端定 | 按 schema |
| 强项 | 简单、可缓存、可预测 | 定制查询、弱冗余 | 性能、类型安全 |
| 弱项 | 过度获取/不足获取 | 复杂度、缓存难 | 浏览器不友好 |
| 适合 | Web API、对外接口 | 复杂数据、移动端 | 微服务间通信 |

**REST 不是最好的，但是最普适的。** 微服务内部调用考虑 gRPC，前端需要定制查询考虑 GraphQL，大多数场景直接用 REST。

## 常见陷阱

**1. POST 当 GET 用**

```text
❌ POST /api/getUsers    # 查数据用了 POST
✅ GET /users
```

**2. 返回和状态码不匹配**

```text
❌ HTTP 200 { "error": "用户不存在" }
✅ HTTP 404 { "success": false, "error": { ... } }
```

**3. 把业务操作当资源**

```text
❌ POST /orders/15/cancel    # cancel 是动作，不是资源
✅ PATCH /orders/15  { "status": "cancelled" }
```

**4. 嵌套过深**

```text
❌ /customers/1/orders/5/products/3/reviews/2
✅ /reviews/2    # 直接定位到资源
```

**5. JWT Token 验证失败返回 500**

认证中间件里 `try-catch` 了 token 校验但没区分「token 过期」和「服务器崩了」，前者应该是 401，后者才是 500。

## 小结

RESTful 不是为了遵守规范——**规范是一堆人踩过坑后总结出的最佳实践**。把资源名用名词、操作交给 HTTP 方法、错误交给状态码，三件事做对，你的 API 就比 90% 的项目好。

设计时想一想：**一个不认识你的人，只看到 URL 和方法，能不能猜出这个接口在干什么？** 能的话，你就做对了。

---

**相关阅读：**
- [HTTP 协议系列](index.md)
