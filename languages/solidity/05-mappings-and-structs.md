# Solidity（五）：映射与结构体——链上的数据组织

> mapping 是哈希表，但不能遍历。那怎么拿到「所有用户」的列表？答案是另开一个数组单独记录。Solidity 的链上数据组织需要两套数据结构配合——这是它和 Web2 后端最大的思维差异。

## mapping：存得进去，取不出来（遍历）

```solidity
contract MappingDemo {
    // key → value 的哈希表
    mapping(address => uint256) public balances;
    //      ^^^^^^^  ^^^^^^^^
    //      键类型    值类型

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // ❌ 不能做的事
    // function getAllUsers() public view returns (...) {
    //     你不能遍历 mapping——没有 .length，没有 .keys()，没有迭代器
    // }
}
```

mapping 不能遍历。这是 EVM 的设计选择——mapping 的存储位置是 `keccak256(key + slot)` 算出来的哈希值，键是分散的，不是连续的。

```text
balances[Alice]   → keccak256(Alice_address + 0)  → 存在槽 X
balances[Bob]     → keccak256(Bob_address + 0)    → 存在槽 Y
```

X 和 Y 之间没有顺序关系。想知道所有用户？你必须自己维护一个数组。

## 映射 + 数组：最常见的数据模式

```solidity
contract UserManager {
    struct User {
        string name;
        uint256 balance;
        bool exists;  // ← 关键：mapping 没法判断键存不存在
    }

    mapping(address => User) public users;
    address[] public userList;  // ← 用数组单独记录所有用户地址

    function addUser(string memory name) public payable {
        require(!users[msg.sender].exists, "Already exists");

        users[msg.sender] = User(name, msg.value, true);
        userList.push(msg.sender);
    }

    function getUserCount() public view returns (uint256) {
        return userList.length;  // ← 遍历用数组的 length
    }

    function getAllUsers() public view returns (address[] memory) {
        return userList;
    }
}
```

这是 Solidity 的标准模式——**mapping 做 O(1) 查找，数组做遍历**。

## mapping 的高级用法

```solidity
contract AdvancedMapping {
    // 嵌套 mapping
    mapping(address => mapping(address => uint256)) public allowances;
    // ERC20 的 allowance 系统:
    // allowances[owner][spender] = 授权额度

    function approve(address spender, uint256 amount) public {
        allowances[msg.sender][spender] = amount;
    }

    // mapping 的 key 可以是 enum
    enum Tier { Basic, Pro, Enterprise }
    mapping(Tier => uint256) public tierPrices;

    // 但不能是 mapping、动态数组、struct
    // ❌ mapping(uint256[] => uint256) 不合法
}
```

## struct：把相关字段打包

```solidity
contract StructDemo {
    struct Proposal {
        address proposer;
        string description;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 deadline;
        bool executed;
    }

    Proposal[] public proposals;

    function createProposal(string memory desc) public {
        proposals.push(Proposal({
            proposer: msg.sender,
            description: desc,
            forVotes: 0,
            againstVotes: 0,
            deadline: block.timestamp + 3 days,
            executed: false
        }));
    }

    // 更新 struct 的字段——用 storage 引用
    function vote(uint256 proposalId, bool support) public {
        Proposal storage prop = proposals[proposalId];
        //    ^^^^^^^ 注意：这里是 storage 引用，修改直接作用于原数据
        require(block.timestamp < prop.deadline, "Voting ended");

        if (support) {
            prop.forVotes += 1;
        } else {
            prop.againstVotes += 1;
        }
    }
}
```

关键点：`Proposal storage prop` 用的是 storage 位置——`prop.forVotes += 1` 直接修改 `proposals[proposalId]`。如果写成 `Proposal memory prop`，改了不影响原数组——这是一个非常容易踩的坑。

## 数组：push、pop 和 gas 的真相

```solidity
contract ArrayDemo {
    uint256[] public numbers;

    function pushDemo() public {
        numbers.push(42);
        // gas: ~20,000（首次写存储槽）+ 数组长度更新
    }

    function popDemo() public {
        numbers.pop();
        // gas: 删除操作 ~5,000，有 15,000 gas 退款
        // 只删最后一个元素——O(1)
    }

    function deleteMiddle(uint256 index) public {
        // ❌ 简单写法——会留空洞（index 位置变成 0，但数组长度不变）
        delete numbers[index];

        // ✅ 正确写法——和最后一个元素交换后 pop
        numbers[index] = numbers[numbers.length - 1];
        numbers.pop();
    }

    function removeBySwap(uint256 index) public {
        // ✅ 更省 gas 的写法——交换并 pop（不保证顺序）
        numbers[index] = numbers[numbers.length - 1];
        numbers.pop();
    }
}
```

数组的删除有三种方式，gas 差异很大：

| 方式 | gas | 副作用 |
|------|-----|--------|
| `delete arr[i]` | 低 | 重置为 0，但数组长度不变 |
| `arr[i] = arr[last]; pop()` | 中 | 交换后 pop——不保证原顺序 |
| 前移所有元素 | **极高** | 保持顺序——链上绝大多数情况不做这个 |

## 实战：一个简单的代币账本

```solidity
contract SimpleToken {
    string public name = "Simple Token";
    string public symbol = "SIM";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    address[] public holders;  // 记录所有持币地址

    event Transfer(address indexed from, address indexed to, uint256 value);

    function mint(address to, uint256 amount) public {
        if (balanceOf[to] == 0) {
            holders.push(to);  // 新用户——加到数组
        }
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) public {
        require(balanceOf[msg.sender] >= amount, "Insufficient");

        if (balanceOf[to] == 0 && amount > 0) {
            holders.push(to);
        }

        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
    }

    function holderCount() public view returns (uint256) {
        return holders.length;
    }
}
```

这就是一个最小可用的 ERC20 代币的核心逻辑。真实开发中用 OpenZeppelin 的标准实现——但这个例子展示了 mapping + 数组 + struct 的实际组合方式。

## 小结

- **mapping = 哈希表**，O(1) 查找但不能遍历
- **数组 = 遍历通道**，用 mapping 查、用数组遍历——两者缺一不可
- **struct 打包字段**，更新用 `storage` 引用（不是 memory）
- **删除数组元素**：交换最后元素再 pop——不要前移

下一篇讲继承与接口——Solidity 也支持多重继承，而且用的是和 Python 一模一样的 C3 线性化。

---

**上一篇：** [（四）函数、修饰器与事件](04-functions-and-modifiers.md)
**下一篇：** [（六）继承、接口与抽象合约](06-inheritance-and-interfaces.md)
