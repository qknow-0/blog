# HTTP（三）：请求头与响应头——信封上的备注

> 请求行说了「GET /page」，请求头告诉服务器「我是浏览器」「我能看懂 HTML」「上次这个资源是昨天拿的」。响应头告诉浏览器「内容是 JSON」「允许哪个域名访问」「把这段缓存 10 秒钟」。

## 核心比喻：信封上的标注

你寄一封信，信封上除了地址，还可以写：

```text
寄件人：张三
内容类型：合同文件
是否要回执：是
```

HTTP 头部（Headers）就是这些信封上的标注——**一行一个键值对**，告诉对方额外信息：

```http
GET /page HTTP/1.1
Host: example.com              ← 这是哪个网站
User-Agent: Chrome/126         ← 我是什么浏览器
Accept: text/html              ← 我能看懂 HTML
Accept-Language: zh-CN         ← 给我中文版本
Cookie: session_id=abc123      ← 这是我的身份凭证
```

## 最常见的请求头

### Host（必填）

HTTP/1.1 规定必须带——因为一台服务器上可能跑了多个网站（虚拟主机），不告诉服务器你要访问哪个域名，它不知道返回哪个站的内容。

```http
Host: api.example.com
```

### User-Agent

浏览器自报家门。可以从中解析出操作系统和浏览器版本。

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
```

历史趣闻：所有浏览器的 User-Agent 都以 `Mozilla/5.0` 开头——包括 Chrome 和 Safari。这是 90 年代浏览器之战的遗产——当年 Netscape 叫 Mozilla，服务器看到 `Mozilla` 才给完整功能，后来所有浏览器都冒充 Mozilla。

### Accept 系列

告诉服务器我能接收什么格式：

```http
Accept: text/html, application/json       ← 我能看懂 HTML 和 JSON
Accept-Language: zh-CN, en;q=0.8          ← 优先中文，英文也行（q 是权重）
Accept-Encoding: gzip, br                  ← 可以压缩——省带宽
```

### Content-Type

请求体里装了什么格式的数据：

```http
# POST JSON 数据
Content-Type: application/json

# 提交表单
Content-Type: application/x-www-form-urlencoded

# 上传文件
Content-Type: multipart/form-data

# 纯文本
Content-Type: text/plain
```

服务器看 Content-Type 决定用什么解析器读请求体。写错了，服务器可能把 JSON 当表单字段解析——报 400 或数据丢失。

### Authorization

身份凭证——最常见的两种：

```http
# Basic Auth：用户名密码 Base64 编码（不安全，仅配合 HTTPS 使用）
Authorization: Basic dG9tOnBhc3M=

# Bearer Token：JWT 或 API Key（现代主流）
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## 最常见的响应头

### Content-Type

和请求的 Content-Type 对应——告诉浏览器响应体是什么格式：

```http
Content-Type: text/html; charset=utf-8    ← 网页
Content-Type: application/json            ← JSON 数据
Content-Type: application/octet-stream    ← 二进制（下载文件）
```

### Content-Length

响应体多少字节——浏览器用这个判断下载进度。

```http
Content-Length: 2417
```

### Cache-Control

告诉浏览器和中间代理这个资源可以缓存多久：

```http
Cache-Control: max-age=3600        ← 缓存 1 小时
Cache-Control: no-store            ← 绝对不要缓存（网银页面）
Cache-Control: no-cache            ← 可以缓存但每次都要重新验证
Cache-Control: public, max-age=86400  ← 所有人（包括 CDN）都可以缓存 1 天
```

### Set-Cookie

服务器让浏览器存一段数据，下次请求自动带上——下一篇的主题。

```http
Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Lax
```

### CORS 相关

跨域（Cross-Origin）请求是否被允许——Web 开发最常见的安全机制之一：

```http
Access-Control-Allow-Origin: https://example.com   ← 只有这个网站能调我的 API
Access-Control-Allow-Methods: GET, POST             ← 只允许这两种方法
Access-Control-Allow-Headers: Content-Type          ← 只允许这个请求头
```

如果服务器没返回这些头——前端 Ajax 请求会被浏览器直接拦截，请求根本没发出去。**CORS 是浏览器做的事**（curl/postman 不受限）。

## 用 curl 看真实头部

```bash
$ curl -I https://www.baidu.com
HTTP/1.1 200 OK
Server: bfe/1.0.8.18
Date: Fri, 14 Jun 2026 08:00:00 GMT
Content-Type: text/html
Cache-Control: private, no-cache, no-store
```

`-I` 参数只发 HEAD 请求——服务器只返回头，不返回体。用于快速检查资源是否存在或缓存是否过期。

## 小结

- 请求头 = 信封上的备注——告诉服务器「我是谁、我想干什么、我能接收什么」
- 响应头 = 回信上的额外说明——「内容是什么、缓存多久、是否允许跨域」
- 开发中最常见的：**Content-Type、Authorization、Cache-Control、CORS 系列**
- `curl -I` 快速看头

下一篇讲状态码——服务器用三位数字告诉你「成功了」「找不到了」「服务器炸了」。

---

**上一篇：** [（二）URL 与请求方法——地址和动作](02-url-and-methods.md)
**下一篇：** [（四）状态码——服务器的一句话回复](04-status-codes.md)
