# Solidity（二）：类型与变量——256 位是默认，不是奢侈

> Solidity 的整数默认是 256 位。为什么？不是因为它「需要这么大的数」，而是因为 EVM 的栈槽就是 256 位宽。你用 uint8，底层还是放在一个 256 位的槽里。

## 值类型 vs 引用类型

Solidity 变量分两大类：

```text
值类型（拷贝值本身）              引用类型（拷贝指向数据的引用）
────────────────────              ──────────────────────
bool                              array（定长/动态）
int/uint（8 到 256 位）           struct
address                           mapping
bytes1 ~ bytes32（定长）
enum
```

**值类型**：赋值时复制值。`b = a` 之后改 b，a 不变。

**引用类型**：赋值时复制引用（指向同一块数据）。`b = a` 之后通过 b 改了数据，a 也看到变化。这很危险——你用一个变量改数据，另一个变量的返回结果也变了。第三个篇会详细讲 Storage/Memory 的关系。

## 整数：uint256 为什么是默认

```solidity
uint256 bigNumber = 115792089237316195423570985008687907853269984665640564039457584007913129639935;
//    ↑ 0 到 2²⁵⁶-1，约 1.15 × 10⁷⁷——比宇宙中原子数还大

uint8 smallNumber = 255;
//   ↑ 0 到 255，手工指定范围
```

EVM 的栈槽是 256 位。数据只能以 256 位为单位进出。你写 `uint8`，编译器会在 256 位里只取最低 8 位，但存储还是占一个 256 位的槽。

**什么时候用 uint8/uint16？**

只有在 struct 中打包存储时——Solidity 会把小于 256 位的变量塞进同一个槽来省 gas：

```solidity
contract Packing {
    // 三个变量在同一个 256 位槽中——读一次 SLOAD 全拿到
    uint128 public a;   // 占前 128 位
    uint64  public b;   // 占中间 64 位
    uint64  public c;   // 占后 64 位
    // 总共 256 位 = 1 个槽——省 gas

    // 如果不指定位数，三个 uint256 各占一个槽——要多花两次 SLOAD
}
```

Solidity 0.8+ 默认**溢出检查**——`uint8(255) + 1` 会 revert 而不是变成 0。不需要 SafeMath 库了。

## address 和 address payable

```solidity
address public owner = 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbD;
//      ↑ 20 字节的十六进制值——以太坊地址

address payable public wallet = payable(0x742d...);
//      ↑ 可以接收 ETH 的地址——多了 .transfer() 和 .send() 方法
```

| 用法 | 代码 | 说明 |
|------|------|------|
| 转账 ETH | `payable(addr).transfer(1 ether)` | 2300 gas 上限，失败自动 revert |
| 发送 ETH | `payable(addr).send(1 ether)` | 2300 gas 上限，失败返回 false |
| 低层调用 | `addr.call{value: 1 ether}("")` | 无 gas 上限，返回 bool + data |

`<address>.balance` 返回地址的 ETH 余额（以 wei 为单位）。常用转换：

```solidity
1 ether = 10^18 wei
1 gwei  = 10^9 wei

msg.value >= 0.01 ether    // 判断用户是否转了 > 0.01 ETH
```

## bool：不能隐式转换

```solidity
bool public isActive = true;

// ❌ if (1) { ... }          // 编译错误！int 不能当 bool 用
// ❌ isActive == 1           // 编译错误！
// ✅ 必须显式使用 true/false
```

Go 和 Rust 没有隐式转换的严格性在 Solidity 上同样适用——写每一行都要求显式。

## bytes：三种形态

```solidity
// 1. bytesN —— 定长字节数组（值类型，便宜）
bytes32 public hash = keccak256(abi.encodePacked("hello"));
//      ↑ 正好 32 字节，放在栈上，gas 极低

// 2. bytes —— 动态字节数组（引用类型，贵）
bytes public dynamicData = "hello world";
//      ↑ 可以改变长度，存在 storage 里，操作成本高

// 3. string —— UTF-8 字符串（本质就是 bytes，但不允许 .length 和下标访问）
string public name = "Alice";
//      ↑ 和 bytes 的区别：string 不允许你按字节操作
```

实用建议：

```solidity
// ✗ 不要用 string 来做拼接——gas 极高
// ✓ 能定长就用 bytes32——在栈上操作，几乎免费
bytes32 key = keccak256(abi.encodePacked(user, id));

// string 和 bytes 之间的转换
bytes memory b = bytes(someString);
string memory s = string(someBytes);
```

## enum：有限状态的命名

```solidity
enum State { Pending, Active, Closed, Cancelled }
State public currentState = State.Pending;

function activate() public {
    require(currentState == State.Pending, "Not pending");
    currentState = State.Active;
}
```

enum 在 Solidity 里不是 int 的别名——不能直接和整数运算。需要显式转换。

## 常量与不可变量

```solidity
// constant：编译期常量——不占 storage，代码里直接嵌入值
uint256 public constant MAX_SUPPLY = 10000;

// immutable：部署期不可变量——部署时赋值，之后不变。比 storage 便宜
address public immutable owner;

constructor() {
    owner = msg.sender;  // immutable 只能在构造函数里赋值
}
```

gas 对比：读 storage 变量 ~2,100 gas（热），读 constant ~3 gas（和加法一样）。

## 小结

- **uint256 是 EVM 栈槽决定的**，不是奢侈——小类型只在 struct 打包时有用
- **address** 是 20 字节的以太坊地址，`address payable` 多了转账方法
- **bytes32 > bytes > string**：定长 > 动态，能定长就别动态，省 gas
- **constant/immutable** 省 gas——编译期嵌入或部署时赋值一次

下一篇讲 Storage vs Memory——为什么同样一段代码，数据放 storage 还是 memory 决定了 gas 是 20000 还是 3。

---

**上一篇：** [（一）EVM 世界观](01-evm-and-basics.md)
**下一篇：** [（三）Storage vs Memory——数据的两种活法](03-storage-and-memory.md)
