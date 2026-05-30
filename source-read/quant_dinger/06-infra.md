# QuantDinger 源码阅读（六）：基础设施——Docker 部署、认证计费与安全设计

> 最后一篇看基础设施层——Docker Compose 怎么编排五个服务、多用户认证和角色体系怎么设计、三种计费模式（credits/membership/USDT）怎么切换、以及贯穿整个项目的安全底线在哪里。

## Docker Compose 服务编排

`docker-compose.yml` 定义了完整的部署拓扑：

```yaml
services:
  postgres:    # ① 数据库——系统状态唯一来源
  redis:       # ② 缓存——worker 协调 + 会话管理
  backend:     # ③ 后端 API——从本地源码构建
  frontend:    # ④ 前端——预构建镜像，Nginx 静态服务
  mcp_server:  # ⑤ MCP Server——可选，通过 profiles 启用
```

### 后端：从源码构建 vs 预构建镜像

```yaml
backend:
  build:
    context: ./backend_api_python
    dockerfile: Dockerfile
  # 不声明 image:——意味着从本地源码构建
```

与 `frontend` 服务形成对比：

```yaml
frontend:
  image: ghcr.io/brokermr810/quantdinger-frontend:${IMAGE_TAG:-latest}
  # 没有 build:——直接拉预构建镜像
```

**为什么后端本地构建而前端预构建？**

后端是 QuantDinger 的核心价值所在——策略引擎、执行层、AI 集成都在这里。用户可能需要修改后端代码（加自定义数据源、改策略逻辑），所以提供源码构建路径。

前端 Vue 源码在独立的私有仓库，打 tag 时自动 CI/CD 推送到 GHCR。普通用户不需要碰前端源码——如果你的需求只是在已有 UI 上操作，拉镜像即可。如果你想改 UI（加自定义页面、改主题），clone `QuantDinger-Vue` 仓库，用 `docker-compose.build.yml` 覆盖即可本地构建。

### PostgreSQL：不仅仅是存储

```yaml
postgres:
  image: postgres:16-alpine
  command:
    - "postgres"
    - "-c" "max_connections=150"    # 默认 100，给连接池留余量
    - "-c" "shared_buffers=256MB"   # 默认 128MB，适度调大
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./backend_api_python/migrations/init.sql:/docker-entrypoint-initdb.d/01-init.sql
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U quantdinger -d quantdinger"]
    interval: 10s
    timeout: 5s
    retries: 5
```

两个值得注意的细节：

1. **`migrations/init.sql` 挂载到 `/docker-entrypoint-initdb.d/`**——PostgreSQL 容器首次启动时自动执行这个目录下的 SQL 文件。QuantDinger 利用这个机制做幂等 schema 引导——`CREATE TABLE IF NOT EXISTS` 确保重复执行不会破坏数据。不需要单独的 migration 工具（如 Alembic），在 Docker 部署场景下更简单可靠。

2. **`max_connections=150`**——默认 PostgreSQL 只允许 100 个连接。QuantDinger 的数据库连接池默认 50 个连接，加上 psql 管理连接和一些余量，150 是合理的。没有过度调大（连接数过大消耗内存），也没有卡着默认值（防止高峰期连接耗尽）。

### Redis：不只是缓存

```yaml
redis:
  image: redis:7-alpine
  # 没有端口映射——只在内部网络可达
```

Redis 在 QuantDinger 中的角色：
- **后台 worker 协调**——`PendingOrderWorker`、`PortfolioMonitor` 等后台服务通过 Redis 做状态共享
- **会话缓存**——用户登录 session、Agent Token 的临时白名单
- **任务队列**——回测和实验优化的异步任务状态

Redis 端口没有对外暴露（只有 `127.0.0.1` 可以访问），减少攻击面。

### HEALTHCHECK 依赖链

```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy    # 等 PG 的 pg_isready 通过
    redis:
      condition: service_started    # Redis 起来就行，没有 healthcheck
```

这和我们在容器化系列讨论的 `depends_on + healthcheck` 完全一致。PostgreSQL 需要 `service_healthy`——数据没初始化好之前，后端连上去会报错。Redis 只需要 `service_started`——它的启动几乎是即时的。

## 认证体系

### 多用户 + RBAC

```python
# services/user_service.py
class UserService:
    def ensure_admin_exists(self):
        """启动时确保至少有一个 admin 用户"""
        if not self._has_admin():
            self._create_default_admin()

    def create_user(self, username, password, role='user'):
        """role: admin / user / viewer"""
```

三种角色：
- **admin**：完整权限——管理用户、配置系统、查看所有策略
- **user**：标准权限——创建/管理自己的策略、回测、交易
- **viewer**：只读——查看仪表盘和策略结果，不能修改

默认管理员账号 `quantdinger / 123456` 的意图很明确——**让你能快速看到产品长什么样，但首次登录后必须改密码**。不改密码的默认账号只能在本地 `127.0.0.1` 访问（通过后端环境变量控制）。

### 密码安全

密码通过 `werkzeug.security`（Flask 内置）的 `generate_password_hash` 和 `check_password_hash` 处理——bcrypt 哈希，加盐，不可逆。即使数据库泄露，攻击者也无法还原明文密码。

### OAuth 集成

```python
# services/oauth_service.py
# 支持 GitHub / Google OAuth 登录
# 首次 OAuth 登录自动创建关联用户
```

可选启用——开箱即用的本地账号密码就够了，OAuth 是为团队使用场景准备的。

### Agent Token 体系

```python
# 人类用户通过 Web UI 创建 Agent Token
# Token 格式：qd_agent_{random_hex}
# 数据库存储 SHA-256 哈希，不存明文
# 每个 Token 有独立的作用域、速率限制、过期时间
```

Token 和用户账号是独立的——一个用户可以创建多个 Token（给不同的 AI 客户端用），每个 Token 有不同的作用域和限制。Token 可以随时吊销。

## 计费系统

QuantDinger 是开源项目，但也支持商业化运营。计费系统设计为**模块化可切换**：

```python
# config/settings.py
BILLING_MODE = os.getenv("BILLING_MODE", "credits")
# 可选：credits / membership / disabled
```

### 三种模式

| 模式 | 机制 | 适用场景 |
|------|------|---------|
| `credits` | 按 API 调用次数扣减积分 | SaaS 多租户，用量计费 |
| `membership` | 固定周期订阅（月/年） | 会员制，功能分级 |
| `disabled` | 不启用计费 | 个人自用，完全免费 |

三种模式共享同一套 `billing_service.py` 的抽象接口，通过环境变量切换实现。不是硬编码的 `if-else`，而是策略模式——`BillingService` 的 `charge()` 方法根据当前模式委派到不同子实现。

### USDT 支付

```python
# services/usdt_payment/
# 支持 TRC-20 / ERC-20 / BEP-20 三条链
# TronGrid / EVM / Solana 三个 watcher
```

USDT 支付是计费系统的特殊通道——支持加密货币支付订阅费。实现方式是：

1. 为每个订单生成唯一的链上地址
2. `USDTOrderWorker` 后台轮询 TronGrid/EVM/Solana 链上交易
3. 检测到支付到账后，自动激活用户会员

每个 watcher 独立运行，互不影响——TRC-20 没到账不影响 ERC-20 的检测。

## 安全底线

QuantDinger 的安全设计不是"加了一层防护"，而是从多个层面设置了硬止损：

### 启动级：SECRET_KEY 强制

```python
# app/__init__.py
SECRET_KEY = os.getenv("SECRET_KEY", "")
if SECRET_KEY == "changeme_please_replace_with_a_secure_random_string" or len(SECRET_KEY) < 32:
    logger.error("SECRET_KEY is insecure. Refusing to start.")
    sys.exit(1)
```

应用直接崩溃，不给任何绕过机会。这是对"运维人员图省事"的硬防御。

### 网络级：最小暴露面

```
外部可访问：8888（前端 Nginx）
仅本地可访问：5000（后端 API）、5432（PG）、6379（Redis）
```

后端 API 只监听 `127.0.0.1`——外部请求走 Nginx 反向代理。直接访问后端 API 的唯一方式是从宿主机 SSH 进去 curl。减少了一层攻击面。

### 交易级：Paper Only 默认

```python
# 所有 Agent 交易路径需要双重开关
if token['paper_only'] or not env_live_trading_enabled():
    raise AgentAuthError
```

AI Agent 绝对不能在无人知晓的情况下动用真实资金。这是设计原则，不是可选项。

### 数据级：密钥哈希存储

```python
# 用户密码：bcrypt 哈希
# Agent Token：SHA-256 哈希
# 交易所 API Key：AES 加密（credential_crypto.py）
```

用户密码和 Agent Token 不可逆（哈希），交易所 API Key 可逆但加密存储（需要 SECRET_KEY 才能解密）。即使数据库文件泄露，攻击者需要同时拿到 `SECRET_KEY` 才能解密交易所密钥。

### 审计级：Append-Only 日志

所有 Agent 操作、所有交易操作、所有用户管理操作的审计日志是 append-only 的。这既是为安全事件溯源，也是合规要求——如果你基于 QuantDinger 运营商业化服务，审计日志是监管的最低要求。

## 为什么读这个项目

六篇文章走完 QuantDinger 的完整架构。最后说一句：这个项目值得读，不是因为它技术多么新颖——Flask + PostgreSQL + Redis 是十年前的成熟技术栈。它值得读的地方在于：

1. **完整产品思维**——从数据到策略到执行到计费，没有死角。不是"技术 demo"而是"可运营的产品"
2. **安全设计不打折**——SECRET_KEY 硬停止、Agent 双重开关、密钥加密存储。每一个可能出安全事故的地方都有对应的防御
3. **不做过度抽象**——DataSourceFactory 就是一个 if-elif 链，不搞插件系统。Agent Gateway 的 MCP Server 就是一个薄 HTTP 封装，不做逻辑复制
4. **设计决策可追溯**——代码注释解释了为什么这么设计（为什么不用 CCXT 直连交易所？为什么空 market 向后兼容但不静默？为什么启动时恢复运行中的策略？）

这些不是某个天才的灵光一闪，而是一个成熟工程师面对真实问题时的自然选择。理解这些选择，比背熟 API 参数重要得多。

## 系列回顾

```
① 项目概览      → 理解五层闭环架构和 Docker 服务拓扑
② 数据层        → 七个市场的统一抽象 + 缓存/限流/熔断
③ 策略引擎      → 双运行时 + 指标IDE + 回测 + LLM驱动优化
④ 执行层        → 多交易所工厂模式 + 订单生命周期
⑤ AI集成        → Agent Gateway + MCP Server + 安全模型
⑥ 基础设施      → Docker编排 + 认证计费 + 安全底线
```

从一篇 README 到一个完整产品的源码级理解。这是源码阅读的价值——不是看懂每个文件，而是理解设计者面对问题和做出选择的全过程。
