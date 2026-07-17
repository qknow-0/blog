# MetaGPT 源码阅读（六）：7 段值得复制的 Python 代码

> 基于 MetaGPT 最新版本。

前 5 篇讲了架构、Role、消息、Prompt。这一篇**只看代码**——从 22 万行 Python 中挑出 7 段可以直接学习的实现，每段都标注了「你可以怎么用」。

## 1. LLM 输出修复管道——策略模式 + Pipeline

**文件**：`metagpt/utils/repair_llm_raw_output.py`（399 行）

**问题**：开源 LLM 的输出格式不可靠。JSON 多一个 `}`、少一个 `/`、key 的大小写不对——这些都会导致 `json.loads()` 抛异常。

**方案**：不是「检测到错误就重试」，而是「先尝试修复，修不好再重试」。

```python
class RepairType(Enum):
    CS = "case sensitivity"        # "Shared knowledge" → "Shared Knowledge"
    RKPM = "required key pair missing"  # 缺了 [/CONTENT] 闭合标签
    SCM = "special character missing"   # [CONTENT] 里少了 /
    JSON = "json format"           # 多余的 [ 或 } 或行尾注释
```

每种修复是一个独立函数，按类型分发：

```python
def _repair_llm_raw_output(output: str, req_key: str, repair_type=None) -> str:
    repair_types = [repair_type] if repair_type else list(RepairType)
    for repair_type in repair_types:
        if repair_type == RepairType.CS:
            output = repair_case_sensitivity(output, req_key)
        elif repair_type == RepairType.RKPM:
            output = repair_required_key_pair_missing(output, req_key)
        elif repair_type == RepairType.SCM:
            output = repair_special_character_missing(output, req_key)
        elif repair_type == RepairType.JSON:
            output = repair_json_format(output)
    return output
```

每个修复函数只做一件事。看 `repair_json_format` 怎么处理注释：

```python
def repair_json_format(output: str) -> str:
    # 去掉 JSON 行尾的 # 或 // 注释——但跳过字符串内的
    arr = output.split("\n")
    new_arr = []
    for json_line in arr:
        comment_index = -1
        for match in re.finditer(r"(\".*?\"|\'.*?\')|(#|//)", json_line):
            if match.group(1):   # 在字符串值内 → 跳过
                continue
            if match.group(2):   # 真正的注释 → 记录位置
                comment_index = match.start(2)
                break
        if comment_index != -1:
            json_line = json_line[:comment_index].rstrip()
        new_arr.append(json_line)
    return "\n".join(new_arr)
```

Regex 先匹配引号内的内容，再匹配注释符号——能区分 `{"url": "http://example.com"}`（`//` 在字符串内，不删）和 `{"key": "val"} // 注释`（删掉注释）。

**更绝的是 JSON 修复的重试机制**：

```python
@retry(
    stop=lambda rs: stop_after_attempt(3 if config.repair_llm_output else 0)(rs),
    wait=wait_fixed(1),
    after=run_after_exp_and_passon_next_retry(logger),
)
def retry_parse_json_text(output: str) -> Union[list, dict]:
    parsed_data = CustomDecoder(strict=False).decode(output)
    return parsed_data
```

`run_after_exp_and_passon_next_retry` 在重试前调用 `repair_invalid_json(output, error)` —— 拿到 JSON 解析错误的具体行号和列号，精确修复那个位置：

```python
def repair_invalid_json(output: str, error: str) -> str:
    pattern = r"line ([0-9]+) column ([0-9]+)"
    matches = re.findall(pattern, error, re.DOTALL)
    line_no = int(matches[0][0]) - 1
    col_no = int(matches[0][1]) - 1

    arr = output.split("\n")
    line = arr[line_no].strip()
    if line.endswith("],"):
        new_line = line.replace("]", "")     # 多余的 ]
    elif line.endswith("},") and not output.endswith("},"):
        new_line = line.replace("}", "")     # 多余的 }
    elif "," not in line:
        new_line = f"{line},"                # 缺逗号
    # ... 十几种具体修复策略
    arr[line_no] = new_line
    return "\n".join(arr)
```

**你可以怎么用**：外部 API / 用户输入 / LLM 输出的文本处理，不要只做「解析成功/失败」的二元判断。做一个修复管道——先尝试自动修复常见错误，修不好再报错。修复策略按类型拆分，每个函数只管一种错误。

## 2. CustomDecoder——让 `json.loads` 容忍不规范的输入

**文件**：`metagpt/utils/custom_decoder.py`（297 行）

**问题**：LLM 输出的 JSON 经常有 Python 社区习惯但 JSON 标准不允许的写法——单引号、三引号、无引号 key、NaN/Infinity。

**方案**：继承 Python 内置的 JSON decoder，覆盖 scanner 行为。

```python
def _scan_once(string, idx):
    nextchar = string[idx]

    if nextchar in ("'", '"'):
        # 支持三引号：'''xxx''' 或 """xxx"""
        if idx + 2 < len(string) and string[idx + 1] == nextchar and string[idx + 2] == nextchar:
            return parse_string(string, idx + 3, strict, delimiter=nextchar * 3)
        else:
            # 支持单引号：'xxx'（JSON 标准不允许）
            return parse_string(string, idx + 1, strict, delimiter=nextchar)
    elif nextchar == "{":
        return parse_object(...)
    elif nextchar == "N" and string[idx:idx+3] == "NaN":
        return parse_constant("NaN"), idx + 3    # JSON 标准没有 NaN
    elif nextchar == "I" and string[idx:idx+8] == "Infinity":
        return parse_constant("Infinity"), idx + 8  # JSON 标准没有 Infinity
    # ...
```

通过覆盖 Python 内置 decoder 的 `_scan_once`，在不改变 JSON 解析逻辑的前提下，扩展了它接受的语法。`CustomDecoder(strict=False)` 比 `json.loads(s, strict=False)` 宽容得多。

**你可以怎么用**：任何接受「人类手写的 JSON-like 文本」的场景——配置文件、LLM 输出、用户输入——都值得换掉标准 `json.loads`。写一个宽松 decoder，投入产出比极高。

## 3. CostManager 继承体系——Template Method

**文件**：`metagpt/utils/cost_manager.py`（150 行）

**问题**：不同 LLM 提供商的计费方式不同。OpenAI 按 token 计费，Fireworks 按模型规模分级计费，本地模型免费。

**方案**：基类定义「更新消耗」的接口，子类覆盖计费逻辑。

```python
class CostManager(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0
    max_budget: float = 10.0
    token_costs: dict = TOKEN_COSTS   # {model: {prompt: $/1k, completion: $/1k}}

    def update_cost(self, prompt_tokens, completion_tokens, model):
        """基类：按 token 数 × 单价 计算"""
        cost = (
            prompt_tokens * self.token_costs[model]["prompt"]
            + completion_tokens * self.token_costs[model]["completion"]
        ) / 1000
        self.total_cost += cost


class TokenCostManager(CostManager):
    """本地模型免费——覆盖为只计数、不计费"""
    def update_cost(self, prompt_tokens, completion_tokens, model):
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        # 不更新 total_cost


class FireworksCostManager(CostManager):
    """Fireworks 按模型规模分级计费"""
    def model_grade_token_costs(self, model: str) -> dict:
        size = re.findall(r".*-([0-9.]+)b", model)
        size = float(size[0]) if size else -1
        if 0 < size <= 16:   return COSTS["16"]     # 小模型
        elif size <= 80:     return COSTS["80"]     # 大模型
        else:                return COSTS["-1"]     # 未知
```

**你可以怎么用**：当你的类只有一个方法在不同场景下行为不同——不要用 if-else 分支，用一个基类 + 多个子类覆盖那个方法。MetaGPT 用了 `NamedTuple`（`Costs`）做返回值——不可变、可解构、自带类型提示。

## 4. ContextMixin——优雅的配置优先级链

**文件**：`metagpt/context_mixin.py`（102 行）

**问题**：Role 和 Action 都需要访问 config、context、llm，但这些资源可能有私有副本（private）也可能共享（从 context 继承）。优先级是：私有 > 共享 > 默认。

**方案**：一个 Mixin 类，用 property 实现优先级链。

```python
class ContextMixin(BaseModel):
    private_context: Optional[Context] = Field(default=None, exclude=True)
    private_config: Optional[Config] = Field(default=None, exclude=True)
    private_llm: Optional[BaseLLM] = Field(default=None, exclude=True)

    @property
    def config(self) -> Config:
        """优先私有配置，否则从 context 继承"""
        if self.private_config:
            return self.private_config
        return self.context.config

    @property
    def llm(self) -> BaseLLM:
        """懒初始化：第一次访问时从 config 创建，后续直接复用"""
        if not self.private_llm:
            self.private_llm = self.context.llm_with_cost_manager_from_llm_config(
                self.config.llm
            )
        return self.private_llm
```

`Field(exclude=True)` 保证私有字段在序列化时被排除——不会污染 JSON 输出。

所有 Role 和 Action 都 `class Role(ContextMixin, BaseModel)` 继承这个 Mixin。加一个新资源（比如 `private_memory`）只需要在 Mixin 里加一个 property。

**你可以这么用**：有「私有/共享/默认」三层优先级需求的任何配置系统，用 Mixin + property 实现。比到处写 `getattr(self, 'x', None) or getattr(self.context, 'x', None) or default` 干净得多。

## 5. `exp_cache` 装饰器——经验缓存

**文件**：`metagpt/exp_pool/decorator.py`（~200 行）

**问题**：LLM 调用昂贵。如果一个问题之前已经完美解决过了，应该直接返回缓存的结果。

**方案**：装饰器拦截函数调用 → 查缓存中有没有完美结果 → 有就跳过执行 → 没有就执行并把结果存到经验池。

```python
def exp_cache(
    query_type=QueryType.SEMANTIC,
    manager=None, scorer=None,
    perfect_judge=None, context_builder=None, serializer=None, tag=None,
):
    def decorator(func):
        @functools.wraps(func)
        async def get_or_create(args, kwargs):
            if not config.exp_pool.enabled:  # 功能开关
                return await func(*args, **kwargs)

            handler = ExpCacheHandler(
                func=func, args=args, kwargs=kwargs,
                query_type=query_type,
                exp_manager=manager,      # 查缓存
                exp_scorer=scorer,        # 评分
                exp_perfect_judge=perfect_judge,  # 判断"完美"
                context_builder=context_builder,  # 从缓存构建上下文
                serializer=serializer,    # 序列化请求/结果
                tag=tag,
            )
            await handler.fetch_experiences()
            # ...
```

所有组件都是可替换的——`scorer`、`perfect_judge`、`context_builder`、`serializer` 都有默认实现，但也都可以注入自定义版本。

`config.exp_pool.enabled` 做总开关——关掉后装饰器等于透明，直接调原函数。生产环境如果经验池出问题了，关掉就是。

**你可以怎么用**：任何昂贵的函数调用（LLM API、数据库查询、外部服务），用装饰器模式加缓存层。关键是缓存判断逻辑（什么是"完美结果"）要和缓存框架解耦——都做成可注入的组件。

## 6. Tree-Sitter 代码净化

**文件**：`metagpt/utils/sanitize.py`（184 行）

**问题**：LLM 生成的代码经常夹杂解释文字、多余的 markdown 围栏、或者只有部分代码是可运行的。

**方案**：两步净化：

```python
# 第 1 步：找到最长可解析的代码段（暴力但有效）
def code_extract(text: str) -> str:
    lines = text.split("\n")
    longest = (0, 0)
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            if syntax_check("\n".join(lines[i:j+1])):
                if len(lines[i:j+1]) > longest_len:
                    longest = (i, j)
    return "\n".join(lines[longest[0]:longest[1]+1])

# 第 2 步：用 tree-sitter 解析，提取可达定义（消除死代码）
def sanitize(code: str, entrypoint: str = None) -> str:
    tree = parser.parse(bytes(code, "utf8"))
    # 收集 import、class、function、assignment
    # 如果指定 entrypoint，只保留调用链上可达的定义
    if entrypoint:
        name2deps = get_deps(definition_nodes)      # 分析依赖
        reachable = get_function_dependency(entrypoint, name2deps)  # BFS 可达
        # 只保留可达部分
```

`get_deps` 用 DFS 在每个 AST 节点中收集标识符引用，`get_function_dependency` 用 BFS 从 entrypoint 出发找所有可达函数。组合起来就是**代码死消除**——对 LLM 输出做 tree-shaking。

`traverse_tree` 是非递归的 tree-sitter 遍历：

```python
def traverse_tree(node: Node) -> Generator[Node, None, None]:
    cursor = node.walk()
    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break
```

不用递归，用 tree-sitter 的 cursor API 做迭代遍历——内存安全、可中断。

**你可以怎么用**：任何需要「从 LLM 输出中提取纯净代码」的场景——代码生成、自动补全、test case 生成——先 `code_extract` 再 `sanitize`。两步分离：第一步暴力找，第二步精确净化。

## 7. Skill 声明式加载——YAML → Pydantic

**文件**：`metagpt/learn/skill_loader.py`（101 行）

**问题**：Agent 的能力定义需要人可写、机器可解析、带类型校验。

**方案**：YAML 文件定义 Skill → Pydantic model 校验 → 代码消费。

```python
class Example(BaseModel):
    ask: str
    answer: str

class Parameter(BaseModel):
    type: str
    description: str = None

class Skill(BaseModel):
    name: str
    description: str = None
    x_prerequisite: Dict = Field(default=None, alias="x-prerequisite")
    parameters: Dict[str, Parameter] = None
    examples: List[Example]
    returns: Returns

class SkillsDeclaration(BaseModel):
    skillapi: str
    entities: Dict[str, Entity]
    components: Components = None

    @staticmethod
    async def load(skill_yaml_file_name=None) -> "SkillsDeclaration":
        data = await aread(filename=skill_yaml_file_name)
        skill_data = yaml.safe_load(data)
        return SkillsDeclaration(**skill_data)   # YAML → Pydantic，自动校验
```

YAML 文件写错一个字 → `SkillsDeclaration(**skill_data)` 直接抛 Pydantic ValidationError，告诉你是哪个字段、什么类型不匹配。不需要手写校验逻辑。

`alias="x-prerequisite"` 让 YAML 可以用 `x-prerequisite`（带连字符），Python 代码用 `x_prerequisite`（下划线）。

**你可以这么用**：任何「人类写配置、代码消费配置」的场景，YAML + Pydantic 是最小摩擦的方案。Pydantic 的 `alias` 解决 YAML/JSON 的命名差异，`BaseModel(**dict)` 一把梭校验。

## 小结

| # | 模式 | 来源文件 | 核心思想 |
|---|---|---|---|
| 1 | 修复管道 | `repair_llm_raw_output.py` | 多策略修复 → 精确重试，而非盲目重试 |
| 2 | 宽松 JSON decoder | `custom_decoder.py` | 覆盖内置 scanner，容忍不规范输入 |
| 3 | 计费模板方法 | `cost_manager.py` | 基类定义接口，子类覆盖计费逻辑 |
| 4 | 配置优先级 Mixin | `context_mixin.py` | property 实现 priv > shared > default |
| 5 | 经验缓存装饰器 | `exp_pool/decorator.py` | 可注入组件的缓存拦截器 |
| 6 | Tree-sitter 净化 | `sanitize.py` | AST 解析 + 暴力提取 + BFS 死代码消除 |
| 7 | YAML→Pydantic | `learn/skill_loader.py` | 声明式加载 + 自动校验 |

---

## 系列完整目录

| 篇 | 主题 |
|---|---|
| 一 | 架构总览：Role、Action、Environment 三角 |
| 二 | Role 系统：三种 react 模式 + RoleContext |
| 三 | Environment 与消息系统：cause_by + watch |
| 四 | 值得学的 8 个设计模式 |
| 五 | Prompt 系统：分层继承 + JSON 命令格式 |
| 六 | 7 段值得复制的 Python 代码 |
