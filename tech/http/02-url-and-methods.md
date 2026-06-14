# HTTP（二）：URL 与请求方法——地址和动作

> 你知道要寄信给谁了（第一篇），但信封上具体怎么写地址？信里要办什么事？这篇拆解 URL 的每个部分和五种请求方法。

## URL 拆解：比你想象的多

一个完整的 URL 长这样：

```text
https://tom:pass@blog.example.com:443/articles?id=5#summary
└─┬─┘ └──┬──┘ └──────┬──────┘ └┬┘ └──┬───┘└─┬┘ └──┬──┘
协议   用户信息     主机名        端口  路径   查询   锚点
```

| 部分 | 示例值 | 必需？ | 说明 |
|------|--------|--------|------|
| 协议（scheme） | `https` | ✅ | http 或 https |
| 用户信息 | `tom:pass` | 极少 | 基本淘汰了——用 Cookie/JWT 替代 |
| 主机名（host） | `blog.example.com` | ✅ | 域名或 IP |
| 端口（port） | `443` | 隐藏了 | HTTP 默认 80，HTTPS 默认 443——不写就用默认 |
| 路径（path） | `/articles` | ✅ | 定位到服务器上的哪个资源 |
| 查询（query） | `?id=5` | 可选 | 给资源的额外过滤或参数 |
| 锚点（fragment） | `#summary` | 浏览器用 | 不发给服务器——只用来定位页面内位置 |

**核心比喻：寄信的地址栏**。

```text
协议   = 用什么语言写信（中文/英文）
主机名 = 收件人名字
端口   = 收件人的第几个信箱（公寓有多个信箱口）
路径   = 收件人的哪个抽屉
查询   = 信封上的「请只看关于 XX 的部分」
```

日常开发里，你 99% 只需要关注**路径**和**查询参数**。剩下的交给浏览器和框架。

## GET：看一眼

最常用的方法——只读，不改变任何东西。浏览器输入网址、点击链接、img 标签加载图片——全是 GET。

```http
GET /articles?id=5 HTTP/1.1
Host: blog.example.com
```

特点：
- 参数放在 URL 里（`?id=5`）
- 可以被缓存、收藏、分享
- **幂等**——请求 1 次和请求 100 次结果一样

注意：GET **不应该有请求体**（body）。虽然 HTTP 规范没禁止，但很多工具和代理不支持，别这么用。

## POST：提交数据

当你要创建新资源或提交表单时用 POST。

```http
POST /articles HTTP/1.1
Host: blog.example.com
Content-Type: application/json

{"title": "HTTP 入门", "content": "..."}
```

特点：
- 数据放在请求**体**里（不在 URL 里）
- **不幂等**——POST 两次会创建两条记录
- 不会被缓存

**比喻**：GET 是看菜单，POST 是下单。

## PUT：整个替换

```http
PUT /articles/5 HTTP/1.1
Host: blog.example.com
Content-Type: application/json

{"title": "HTTP 精通", "content": "..."}
```

PUT 的意思是：「把 `/articles/5` 这个资源**完整替换**成我给你的数据」。和 POST 的区别：

| | POST | PUT |
|---|---|---|
| 语义 | 创建新资源 | 替换已有资源 |
| 幂等 | ❌ | ✅（放 5 次都一样） |
| 路径 | `/articles`（集合） | `/articles/5`（具体哪个） |

**比喻**：POST 是在书架上放本新书，PUT 是把第 5 本书换成新版本。

## PATCH：局部修改

```http
PATCH /articles/5 HTTP/1.1
Host: blog.example.com
Content-Type: application/json

{"title": "HTTP 精通（修订版）"}
```

PUT 要你传整个资源（包括不改的字段），PATCH 只传要更新的字段。

**比喻**：PUT 是整本书重印，PATCH 是只换封面。

## DELETE：删除

```http
DELETE /articles/5 HTTP/1.1
Host: blog.example.com
```

就是删除。幂等——删一次和删五次一样。

## 五种方法速查

```mermaid
flowchart LR
    GET["GET 看<br/>读菜单"]
    POST["POST 创<br/>下单"]
    PUT["PUT 换<br/>整本替换"]
    PATCH["PATCH 改<br/>只改封面"]
    DELETE["DELETE 删<br/>扔掉"]

    GET -->|"有数据给服务器"| POST
    POST -->|"已有资源要更新"| PUT
    PUT -->|"只改部分字段"| PATCH
```

实际开发中，浏览器表单只支持 GET 和 POST。PUT/PATCH/DELETE 需要通过 JavaScript 发 Ajax 请求，或者用框架的 method spoofing（比如 Laravel 的 `_method` 隐藏字段）。

## 小结

- URL 就是完整地址——日常只需要关注**路径**和**查询参数**
- 五个方法：**GET 看、POST 创、PUT 全换、PATCH 部分改、DELETE 删**
- 幂等：GET/PUT/DELETE ✅，POST ❌
- 请求体：GET 没有，POST/PUT/PATCH 有

下一篇讲请求头和响应头——信封上的各种备注。

---

**上一篇：** [（一）HTTP 是什么——浏览器和服务器怎么对话](01-basics.md)
**下一篇：** [（三）请求头与响应头——信封上的备注](03-headers.md)
