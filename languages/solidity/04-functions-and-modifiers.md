# Solidity（四）：函数、修饰器与事件

> view 不是文档注释——是编译器的硬约束。modifier 是 Solidity 版的 AOP——把权限检查从业务逻辑里抽出来。event 是最便宜的存储——花 375 gas 记一条日志，回头看只需要一个离线索引。

## 函数的四种可见性

```solidity
contract VisibilityDemo {
    function publicFunc()    public    { /* 任何人（内部 + 外部 + 其他合约）都可以调 */ }
    function externalFunc()  external  { /* 只能从合约外部调（EOA 或其他合约） */ }
    function internalFunc()  internal  { /* 本合约 + 子合约可以调 */ }
    function privateFunc()   private   { /* 只有本合约能调，子合约也不行 */ }
}
```

| 可见性 | 内部调用 | 外部调用 | 常用场景 |
|--------|---------|---------|---------|
| `public` | ✅ | ✅ | 暴露给所有人 |
| `external` | ❌ | ✅ | 只给外部调——比 public 省 gas（参数不用拷贝到 memory） |
| `internal` | ✅ | ❌ | 继承时复用的内部逻辑 |
| `private` | ✅ | ❌ | 不暴露的实现细节 |

**注意**：`external` 比 `public` 省 gas——外部调用走 calldata 直读，不复制到 memory。

## 状态可变性：view 和 pure

```solidity
contract MutabilityDemo {
    uint256 public x = 10;

    // ❌ view 函数里修改状态——编译报错
    // function badView() public view { x = 5; }  // 不通过

    // ✅ view 承诺只读
    function readX() public view returns (uint256) {
        return x;  // 只读——OK
    }

    // ✅ pure 承诺连读都不读
    function add(uint256 a, uint256 b) public pure returns (uint256) {
        return a + b;  // 不读不改——OK
    }
}
```

| 修饰符 | 读状态变量 | 写状态变量 | 调用者 gas |
|--------|----------|----------|-----------|
| 无 | ✅ | ✅ | 花 gas |
| `view` | ✅ | ❌ | 本地调用免费 |
| `pure` | ❌ | ❌ | 本地调用免费 |

**view 和 pure 的免费调用只对本地节点有效**。如果你在某处交易中调了一个 view 函数——依然消耗 gas（因为是交易的一部分）。

## payable：函数能收钱

```solidity
contract PayableDemo {
    // 没有 payable——发 ETH 过来会 revert
    function donate() public payable {
        // msg.value 就是这次调用附带的 ETH 数量（单位 wei）
        require(msg.value >= 0.01 ether, "Minimum donation 0.01 ETH");
        // ETH 自动存入合约余额
    }

    function getBalance() public view returns (uint256) {
        return address(this).balance;  // 合约的 ETH 余额
    }
}
```

如果一个函数没有 `payable`，而你调用时发送了 ETH——交易会直接 revert。这是以太坊的设计——默认不收钱，必须显式声明。

## modifier：Solidity 版的 AOP

```solidity
contract ModifierDemo {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // 定义一个 modifier——权限检查逻辑
    modifier onlyOwner() {
        require(msg.sender == owner, "Not the owner");
        _;  // ← 执行被修饰的函数体
    }

    // 用 modifier 装饰器语法
    function withdraw() public onlyOwner {
        payable(owner).transfer(address(this).balance);
        // 函数体在 modifier 的 _; 位置执行
    }
}
```

`modifier` 的本质就是 AOP（面向切面编程）——把横切逻辑（权限检查、重入锁、参数验证）从业务逻辑中抽离出来。执行顺序：

```text
函数开始
  → modifier 的 _; 之前的代码
  → 函数体本身
  → modifier 的 _; 之后的代码（如果有）
```

常用 modifier 模式：

```solidity
// 重入锁
modifier nonReentrant() {
    require(!locked, "Reentrant call");
    locked = true;
    _;
    locked = false;
}

// 参数验证
modifier validAddress(address addr) {
    require(addr != address(0), "Zero address");
    _;
}
```

## event：最便宜的存储

```solidity
contract EventDemo {
    // 声明 event——最多三个 indexed 参数
    event Transfer(address indexed from, address indexed to, uint256 value);

    function transfer(address to, uint256 amount) public {
        // 发 event——花 ~375 gas + 每字节 8 gas
        emit Transfer(msg.sender, to, amount);
    }
}
```

event 为什么便宜？

```text
storage 写状态变量: 20,000 gas（链上持久，永久保存）
event 写日志:         375 gas + 8/字节（链上日志，不存状态树）

event 是写入交易收据里的日志——全节点能看到，但合约不能读取。
就像邮寄——你寄出去了（emit），自己不保存副本（合约内不能查询 event）。
```

`indexed` 参数可以被外部（如 Ethers.js）按条件查询，但最多三个。不加 `indexed` 的参数存在日志的 data 段，无法用于搜索筛选。

## 接收 ETH 的三种方式

```solidity
contract ReceiveDemo {
    // 方式 1：有 calldata——匹配特定函数选择器
    function donate() public payable { }

    // 方式 2：无 calldata——兜底。data 不为空时触发
    fallback() external payable { }

    // 方式 3：无 calldata——兜底。data 为空时触发（纯 ETH 转账）
    receive() external payable { }
}
```

优先级：

```text
交易带 calldata
  → 匹配到函数选择器 → 执行该函数（如果有 payable）
  → 没匹配到        → 执行 fallback()（如果有）
交易不带 calldata（纯 ETH 转账）
  → receive() 存在  → 执行 receive()
  → receive() 不存在 → 执行 fallback()（如果 fallback 有 payable）
```

## 小结

- **external > public**——外部调用用 external 省 gas
- **view/pure** = 编译器硬约束——不是文档注释，违规编译不过
- **modifier** = Solidity 的 AOP——权限、重入锁、参数校验
- **event** 是花 375 gas 记永久日志——外部可查，合约不可读
- **receive/fallback** = ETH 接收的兜底机制——防止 ETH 锁死在合约里

下一篇讲 mapping 和 struct——Solidity 怎么在链上组织复杂数据。

---

**上一篇：** [（三）Storage vs Memory](03-storage-and-memory.md)
**下一篇：** [（五）映射与结构体——链上的数据组织](05-mappings-and-structs.md)
