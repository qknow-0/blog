# Solidity 系列

从 EVM 世界观到链上安全，七篇覆盖 Solidity 智能合约开发的全部核心概念。

> 本文基于 Solidity 0.8.35。

## 阅读顺序

1. **[（一）EVM 世界观——Solidity 不是一个普通的编程语言](01-evm-and-basics.md)** — 2026-06-15
   - 世界计算机、gas 即燃料、代码即法律、自动售货机比喻

2. **[（二）类型与变量——256 位是默认，不是奢侈](02-types-and-variables.md)** — 2026-06-15
   - 值类型与引用类型、uint256 的底层原因、bytes/string 的工作原理

3. **[（三）Storage vs Memory——数据的两种活法](03-storage-and-memory.md)** — 2026-06-15
   - storage 是硬盘 memory 是内存、gas 成本对比、calldata 与 stack

4. **[（四）函数、修饰器与事件](04-functions-and-modifiers.md)** — 2026-06-15
   - view/pure/payable、modifier 的 AOP 机制、event 是最便宜的存储

5. **[（五）映射与结构体——链上的数据组织](05-mappings-and-structs.md)** — 2026-06-15
   - mapping 是哈希表但不能遍历、struct 组合、数组的链上成本

6. **[（六）继承、接口与抽象合约](06-inheritance-and-interfaces.md)** — 2026-06-15
   - 多重继承 C3 线性化、抽象合约 vs 接口、library 的无状态复用

7. **[（七）安全——重入攻击与链上陷阱](07-security.md)** — 2026-06-15
   - 重入攻击、访问控制、闪电贷、溢出保护，每个都带真实攻击案例
