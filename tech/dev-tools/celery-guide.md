# Celery：Python 分布式任务队列实战指南

> 用户注册后发邮件、定时生成报表、批量处理图片——这些不应该堵在 HTTP 请求里。Celery 是 Python 生态里最成熟的异步任务队列，把重活从 Web 进程里拆出来，交给后台 Worker 慢慢跑。

## 什么问题

```python
@app.post("/register")
def register(user_data):
    user = create_user(user_data)
    send_welcome_email(user.email)     # 3 秒——SMTP 握手 + 渲染模板
    generate_thumbnail(user.avatar)     # 2 秒——图片处理
    notify_admin(f"New user: {user.id}") # 1 秒——Slack Webhook
    return {"ok": True}
# 用户点了注册，等了 6 秒才看到"注册成功"
```

每个操作本身都不慢，但串在一起就把 HTTP 请求拖死了。理想的模型：

```mermaid
flowchart LR
    Web["Web 进程"] -->|"task.delay()"| Broker["Broker<br/>RabbitMQ / Redis"]
    Broker -->|"分发"| Worker1["Worker 1"]
    Broker -->|"分发"| Worker2["Worker 2"]
    Broker -->|"分发"| Worker3["Worker 3"]
    Worker1 --> Backend["Result Backend<br/>Redis / DB"]
    Worker2 --> Backend
    Worker3 --> Backend
```

Web 进程只做一件事：**创建任务，立即返回**。Worker 进程从消息队列里取任务、执行、存结果。Web 和 Worker 之间唯一的耦合是 Broker——一个消息队列。

这就是 Celery 解决的问题。

## 快速开始

```bash
pip install celery

# Broker——二选一
# Redis（简单场景首选）
brew install redis && redis-server

# RabbitMQ（生产环境推荐）
brew install rabbitmq && rabbitmq-server
```

### 第一个任务

```python
# tasks.py
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def send_welcome_email(user_email):
    """模拟发送欢迎邮件"""
    import time
    time.sleep(3)  # 模拟 SMTP 延迟
    return f"Welcome email sent to {user_email}"

@app.task
def generate_thumbnail(image_path):
    """模拟生成缩略图"""
    import time
    time.sleep(2)
    return f"Thumbnail generated for {image_path}"

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def call_external_api(self, endpoint, payload):
    """调用外部 API，失败自动重试"""
    import requests
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise self.retry(exc=exc)
```

### 启动 Worker

```bash
# 终端 1：启动 Worker
celery -A tasks worker --loglevel=info

# 输出：
# -------------- celery@macbook.local v5.6.2
# -- ******* ---- macOS-14.5-arm64-64bit 2026-06-04
# - *** --- * ---
# - ** ---------- [config]
# - ** ---------- .> app:         tasks:0x...
# - ** ---------- .> transport:   redis://localhost:6379/0
# - ** ---------- .> results:     disabled://
# - *** --- * --- .> concurrency: 8 (prefork)
# -- ******* ---- .> task events: OFF
# -------------- [queues]
#                 .> celery       exchange=celery(direct) key=celery
#
# [2026-06-04 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
# [2026-06-04 10:00:00,010: INFO/MainProcess] celery@macbook.local ready.
```

### 调用任务

```python
# 终端 2：Python REPL
from tasks import send_welcome_email, generate_thumbnail

# .delay() —— 最简调用
result = send_welcome_email.delay("user@example.com")
print(result.id)      # "a1b2c3d4-e5f6-..."
print(result.status)  # "PENDING"

# .apply_async() —— 带参数调用
result = generate_thumbnail.apply_async(
    args=("/uploads/avatar.jpg",),
    countdown=10,        # 10 秒后执行
    expires=120,         # 2 分钟后过期
)

# 等结果
print(result.get(timeout=30))  # 阻塞等待 30 秒
# "Thumbnail generated for /uploads/avatar.jpg"
```

调用后 Web 进程立即返回，Worker 在后台执行。用户看到的注册响应从 6 秒变成 50 毫秒。

## 核心概念

### Broker —— 消息的「邮局」

| Broker | 适用场景 | 优点 | 缺点 |
|--------|---------|------|------|
| **Redis** | 开发、中小规模 | 简单、已有 Redis 的团队不需要新依赖 | 断电丢消息（少量）、内存成本 |
| **RabbitMQ** | 生产、大规模 | 消息不丢、ACK 确认、管理界面好 | 运维复杂度高、额外组件 |

```python
# Redis
app = Celery('tasks', broker='redis://localhost:6379/0')

# RabbitMQ
app = Celery('tasks', broker='amqp://guest:guest@localhost:5672//')

# Redis + 密码
app = Celery('tasks', broker='redis://:password@localhost:6379/0')
```

Redis 足够应付大多数场景。当你开始担心 Redis 宕机丢消息时，考虑 RabbitMQ。

### Result Backend —— 任务结果存在哪

```python
# 不存结果（最快，推荐对不需要结果的场景）
app = Celery('tasks', broker='redis://...', backend=None)

# Redis（最常用）
app = Celery('tasks', broker='redis://...', backend='redis://localhost:6379/1')

# Django ORM
app = Celery('tasks', backend='django-db')

# 啥也不存
app.conf.result_backend = 'rpc://'  # RPC 风格，结果存在 Worker 内存里
```

不需要结果的任务——发邮件、写日志、清理缓存——`backend=None` 省了 Redis 内存和网络开销。

### Worker —— 干活的进程

```bash
# 基础启动
celery -A tasks worker --loglevel=info

# 指定并发数
celery -A tasks worker --concurrency=4    # 4 个 Worker 子进程

# 指定队列
celery -A tasks worker -Q email,thumbnail  # 只消费这两个队列

# 自动扩容（需要 celery[solo_pool]）
celery -A tasks worker --autoscale=10,3    # 最多 10 个进程，最少 3 个

# 使用 gevent（I/O 密集型任务）
celery -A tasks worker --pool=gevent --concurrency=500
```

`--pool` 的选择：

| Pool 类型 | 适用场景 | 说明 |
|-----------|---------|------|
| `prefork`（默认） | CPU 密集型 | 多进程，最稳定，每个 Worker 一个独立进程 |
| `gevent` / `eventlet` | I/O 密集型 | 协程，一个进程可以跑数千并发，但不能用 CPU 密集型代码 |
| `threads` | I/O 中等 | 多线程，受 GIL 限制但比协程兼容性好 |
| `solo` | 调试 | 单进程，不 fork，方便 pdb 断点 |

## 任务——不只是 `@app.task`

### 基本形式

```python
@app.task
def add(x, y):
    return x + y

# 调用
add.delay(2, 3)              # 最常用
add.apply_async((2, 3))       # delay 的等价写法
add.apply_async(
    (2, 3),
    countdown=60,              # 延迟 60 秒
    eta=datetime(2026, 6, 5, 9, 0),  # 指定时间执行
    expires=300,               # 5 分钟未执行就丢弃
    retry=True,                # 失败重试
    retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },
    queue='high_priority',     # 指定队列
    routing_key='urgent',      # 路由键
    serializer='json',         # 序列化方式
    compression='zlib',        # 压缩
)
```

### `bind=True` —— 任务感知自己

```python
@app.task(bind=True)
def process_file(self, file_path):
    """self 指向当前任务实例"""
    total = get_file_size(file_path)
    for i, chunk in enumerate(read_chunks(file_path)):
        do_work(chunk)
        # 更新进度（需要在 result backend 中查询）
        self.update_state(
            state='PROGRESS',
            meta={'current': i, 'total': total}
        )
    return {'processed': total}
```

`update_state` 让 Web 端可以轮询 Celery 任务的实时进度——不是只有 PENDING 和 SUCCESS 两种状态。

### 错误处理与重试

```python
@app.task(bind=True, autoretry_for=(RequestException,), max_retries=3)
def fetch_api_data(self, url):
    """网络故障自动重试，指数退避"""
    response = requests.get(url, timeout=5)
    return response.json()

@app.task(bind=True, max_retries=5)
def charge_credit_card(self, order_id, amount):
    """手动控制重试逻辑"""
    try:
        payment_gateway.charge(order_id, amount)
    except TemporaryFailure as exc:
        # 第一次等 10 秒，第二次等 30 秒，第三次等 90 秒
        countdown = 10 * (3 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    except PermanentFailure:
        # 卡被拒——不重试，直接标记失败
        mark_order_failed(order_id)
        return {'status': 'card_declined'}
```

两种重试策略：
- **`autoretry_for`**：声明式，指定异常类型，Celery 自动重试
- **`self.retry()`**：命令式，在任务体内手动控制重试逻辑和延迟

### 任务链——一个任务的输出是下一个的输入

```python
from celery import chain, group, chord

# 链式：按顺序执行
result = chain(
    fetch_data.s(url),
    parse_data.s(),
    save_to_db.s(),
)()

# 组：并行执行
job = group(
    process_file.s(f) for f in file_list
)

# chord：并行执行完再汇总
result = chord(
    [fetch_price.s(symbol) for symbol in ['AAPL', 'GOOGL', 'TSLA']],
    calculate_portfolio.s()
)()

# 签名 .s() 是 partial 的快捷方式
# add.s(1, 2) 等价于 lambda: add(1, 2)
```

Canvas（画布）是 Celery 最强大的特性之一——用函数组合的方式编排复杂工作流，不需要写状态机。

## 定时任务——Celery Beat

```python
# tasks.py
from celery import Celery
from celery.schedules import crontab

app = Celery('tasks', broker='redis://localhost:6379/0')

app.conf.beat_schedule = {
    'cleanup-every-hour': {
        'task': 'tasks.clean_old_sessions',
        'schedule': crontab(minute=0),   # 每小时整点
    },
    'daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(hour=9, minute=30),  # 每天 9:30
    },
    'every-30-seconds': {
        'task': 'tasks.check_health',
        'schedule': 30.0,                # 每 30 秒
    },
}

@app.task
def clean_old_sessions():
    """清理过期会话"""
    db.execute("DELETE FROM sessions WHERE expires_at < NOW()")
    return "Sessions cleaned"

@app.task
def generate_daily_report():
    """生成日报"""
    stats = calculate_stats(yesterday())
    send_report_email(stats)
    return "Report sent"
```

启动 Beat：

```bash
# Beat 只负责调度——到点发消息给 Broker，不执行任务
celery -A tasks beat --loglevel=info

# 另起一个 Worker 来执行
celery -A tasks worker --loglevel=info
```

`crontab` 的语法和 Unix cron 完全一样：

```python
crontab(minute=0, hour=0)                     # 每天 0 点
crontab(minute=30, hour=8, day_of_week=1)     # 每周一 8:30
crontab(minute=0, hour=0, day_of_month='1-7') # 每月 1-7 号
```

## 路由——重要的事优先做

```python
app.conf.task_routes = {
    'tasks.send_email': {'queue': 'email'},
    'tasks.generate_report': {'queue': 'report'},
    'tasks.process_payment': {'queue': 'high_priority'},
}

# 启动多个 Worker，各消费不同的队列
# Worker 1：只处理支付（高优先级）
celery -A tasks worker -Q high_priority --concurrency=2

# Worker 2：只处理邮件
celery -A tasks worker -Q email --concurrency=4

# Worker 3：只处理报表
celery -A tasks worker -Q report --concurrency=2

# Worker 4：默认队列兜底
celery -A tasks worker -Q celery --concurrency=4
```

这样设置之后，支付任务永远不会被大批量邮件任务堵住——它走的是独立的 Worker 池。

## 监控——Flower

```bash
pip install flower
celery -A tasks flower --port=5555
# 打开 http://localhost:5555
```

Flower 提供了：
- 实时任务监控（成功率、失败率、耗时分布）
- Worker 状态（在线/离线、并发使用率）
- 任务搜索和过滤
- 任务的参数、结果、堆栈追踪
- 远程控制（取消、重新执行）

生产环境建议加认证：

```bash
celery -A tasks flower --port=5555 --basic_auth=admin:password
```

## 实际场景

### 场景一：Web 应用集成（Flask）

```python
# app.py
from flask import Flask, request, jsonify
from celery import Celery

app = Flask(__name__)
celery = Celery(
    'app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
)

@celery.task
def send_async_email(recipient, subject, body):
    """发送邮件——耗时 1-5 秒，不应该阻塞请求"""
    smtp.send(recipient, subject, body)
    return f"Email sent to {recipient}"

@app.post("/users")
def create_user():
    data = request.json
    user = User.create(data)
    # 发邮件不阻塞响应
    send_async_email.delay(user.email, "Welcome!", "...")
    return jsonify({"user_id": user.id}), 201

# 启动
# celery -A app.celery worker --loglevel=info
# flask run
```

### 场景二：Django 项目

```python
# celery.py（和 settings.py 同级）
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()   # 自动发现各 app 下的 tasks.py

# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
```

启动：

```bash
celery -A myproject worker --loglevel=info
celery -A myproject beat --loglevel=info
```

### 场景三：大文件处理

```python
@app.task(bind=True)
def process_large_csv(self, file_path):
    """逐块处理大 CSV，每块更新进度"""
    total_lines = count_lines(file_path)
    processed = 0

    for chunk in pd.read_csv(file_path, chunksize=10000):
        transform_and_save(chunk)
        processed += len(chunk)
        self.update_state(
            state='PROGRESS',
            meta={
                'processed': processed,
                'total': total_lines,
                'percent': round(processed / total_lines * 100, 1),
            }
        )

    return {'processed': processed, 'status': 'done'}
```

## 常见坑

### JSON 序列化——默认不接受复杂类型

```python
# 错误：datetime 不是 JSON 可序列化的
@app.task
def process_order(order):
    pass

# order = {'id': 1, 'created': datetime.now()}
# process_order.delay(order)  # ❌ kombu.exceptions.EncodeError

# 解决方案 1：传简单类型
process_order.delay(order_id=1)

# 解决方案 2：配置 pickle 序列化（不推荐——有安全风险）
app.conf.task_serializer = 'pickle'

# 解决方案 3：JSON 友好的数据类型
process_order.delay(order_id=1, created_iso="2026-06-04T10:00:00")
```

Celery 默认用 JSON 序列化任务参数——安全但只支持基本类型。**不要轻易切到 pickle**，因为它允许任意 Python 对象，有代码执行风险。把参数转成 JSON 友好的简单类型。

### Worker 用了旧代码

```bash
# 改了 tasks.py 后必须重启 Worker
celery -A tasks control shutdown   # 优雅关闭
celery -A tasks worker --loglevel=info   # 重新启动

# 或者用 auto-reload（开发环境用）
pip install watchdog
celery -A tasks worker --loglevel=info --autoreload
```

Worker 启动时加载 Python 模块到内存，之后代码修改不会自动生效。

### 任务不是「即发即到」

```python
# Broker 有传输延迟 + Worker 忙碌排队
result = my_task.delay()
time.sleep(0.1)                # ❌ 多半还是 PENDING
print(result.status)

# 正确做法：用 result.get(timeout=...) 等待
print(result.get(timeout=30))  # ✅ 阻塞直到完成或超时
```

### 不要在任务参数里传 ORM 对象

```python
# ❌ Django ORM 对象在 Worker 端可能状态过期
user = User.objects.get(id=1)
send_email.delay(user)

# ✅ 传 ID，Worker 端重新查询
send_email.delay(user_id=user.id)
```

Task 的参数在传给 Broker 之前被序列化，到 Worker 端再反序列化。传个 ORM 对象进去，到了 Worker 端变成一坨过期的 JSON。永远传 ID，在 Worker 端重新查。

## 总结

Celery 的核心就是三件事：**把任务交给 Broker → Worker 消费执行 → 结果写入 Backend**。理解了这个三角关系，剩下的（路由、签名、Beat、重试）都只是在这三个角色上叠加的配置。

```mermaid
flowchart LR
    P["Producer<br/>Web 进程"] -->|"task.delay()"| B["Broker<br/>消息队列"]
    B -->|"消费"| W["Worker<br/>执行进程"]
    W -->|"存结果"| R["Result Backend"]
    P -->|"查结果"| R
```

和前几篇的关联：
- 把 Celery 部署到 Docker 里（容器化系列）
- Celery 的 `@app.task` 就是 Python 装饰器（decorators.md）
- Beat 的定时任务就是 systemd timer / launchd `StartCalendarInterval` 的替代方案
