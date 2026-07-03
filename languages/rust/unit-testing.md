# Rust 单元测试：食品出厂前的质检流程

> 本文基于 Rust 1.96。

写好代码就像做好一道菜，但能不能端上桌（发布），得先通过**食品质检**。Rust 的测试框架内建在语言里，不需要额外装 pytest、JUnit、Jest——`cargo test` 就是质检启动按钮。测试代码和业务代码可以放在同一个文件里（质检实验室和后厨在同一栋楼），编译期就能发现质检流程里的类型错误。

## 基本语法：搭建质检实验室

```rust
// src/lib.rs（后厨）
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {              // 质检实验室——和后厨隔开，但共享原料
    use super::*;

    #[test]               // 第一项检测：「加法是否等于 5」
    fn test_add() {
        assert_eq!(add(2, 3), 5);  // 对照标准配方检查
    }

    #[test]               // 第二项检测：「负数相加」
    fn test_add_negative() {
        assert_eq!(add(-1, -2), -3);
    }
}
```

`#[cfg(test)]` 告诉编译器：这个模块只在质检模式下才启用。正常生产（release 构建）时，质检实验室不上班，也不占地方。`#[test]` 标记每一项检测。

运行质检：

```bash
cargo test
```

输出：

```
running 2 tests
test tests::test_add ... ok
test tests::test_add_negative ... ok

test result: ok. 2 passed; 0 failed
```

`ok` = 合格，`failed` = 不合格。

## 常用断言：不同的检测工具

```rust
// 重量/尺寸对照
assert_eq!(result, expected);
assert_ne!(result, unexpected);

// 目视检测
assert!(value > 0);
assert!(result.is_ok());

// 质检员备注
assert_eq!(add(2, 3), 6, "2 + 3 应该等于 5，实际测出来是 {}", add(2, 3));
```

## 测试 panic：保质期检测

有些产品出厂时就预期它**会变质**——比如酸奶在保质期过了之后必然发酸。`#[should_panic]` 就是用来验证「这个东西确实会变质」的检测项目：

```rust
pub fn divide(a: i32, b: i32) -> i32 {
    if b == 0 {
        panic!("除数不能为零");
    }
    a / b
}

#[test]
#[should_panic(expected = "除数不能为零")]  // 确认：它确实会坏，而且必须是这种坏法
fn test_divide_by_zero() {
    divide(10, 0);
}
```

`expected` 参数可选——指定了就是精确到哪种「坏了」：发霉（"除数不能为零"）还是变味（别的内容），不指定就是只要 panic 就算通过。

## 测试 Result：质检设备出故障

有时不是产品不合格，而是**质检设备本身出了问题**：

```rust
#[test]
fn test_read_file() -> std::io::Result<()> {
    let content = std::fs::read_to_string("Cargo.toml")?;  // 读取质检单
    assert!(content.contains("[package]"));
    Ok(())
}
```

返回 `Err` 等于「质检设备故障，本批次检测无效」，而不是「产品不合格」。这样就不需要用 `unwrap()` 把设备故障强行当成产品问题来处理。

## 组织测试：内部质检 vs 第三方送检

```
src/
├── lib.rs              # 内部质检写在 #[cfg(test)] mod tests 里
├── main.rs
└── calculator.rs
tests/
└── integration_test.rs # 第三方送检放在 tests/ 目录下
```

**单元测试**和源码放一起，相当于工厂内部的质检实验室——可以看到原料配方（访问私有函数），也参与研发流程。

**集成测试**放 `tests/` 目录下，相当于送到第三方检测机构——只能从外面检查包装上的标签（调用公开 API），模拟真正消费者的视角：

```rust
// tests/integration_test.rs（第三方检测报告）
use my_crate::add;

#[test]
fn integration_test_add() {
    assert_eq!(add(1, 2), 3);
}
```

集成测试不需要 `#[cfg(test)]`——`tests/` 目录下的文件自动只在质检时编译，就像第三方检测机构只在送检时上班、平时不占用产线资源。

## 测试函数 vs 测试文件：不同的抽检模式

```rust
// 只跑特定检测项目
cargo test test_add              // 按检测名称过滤
cargo test tests::calculator     // 按检测部门过滤

// 标记为「抽检项目」，默认跳过
#[test]
#[ignore]                        // 比如需要 48 小时培养的微生物检测
fn test_slow_network_call() {
    // ...
}

cargo test -- --ignored          // 专项抽检——只跑被忽略的
cargo test -- --include-ignored  // 全部检
```

## 文档测试：菜谱上的示范步骤也要经过验证

Rust 的文档注释里的代码块也是质检项目：

```rust
/// 将两个整数相加。
///
/// # 示例
///
/// ```
/// use my_crate::add;
/// assert_eq!(add(2, 3), 5);
/// ```
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

`cargo test` 会编译并运行文档中所有代码块——就像菜谱上印的「成品示意图」也要实际做出来验证。文档写错了（图示和实物不符），测试直接挂。这迫使文档和代码始终保持一致。

## 测试组织最佳实践：按品类分组质检

一个中等复杂度的模块，质检体系长这样：

```rust
// src/calculator.rs（后厨的配方）
pub struct Calculator { /* ... */ }

impl Calculator {
    pub fn new() -> Self { /* ... */ }
    pub fn add(&mut self, value: i32) { /* ... */ }
    pub fn result(&self) -> i32 { /* ... */ }
}

#[cfg(test)]
mod tests {                    // 质检中心
    use super::*;

    // 质检前的准备工序——不需要 #[test]
    fn setup_calculator() -> Calculator {
        Calculator::new()
    }

    mod constructor {          // 包装检测组
        use super::*;

        #[test]
        fn new_calculator_has_zero_result() {
            let calc = setup_calculator();
            assert_eq!(calc.result(), 0);
        }
    }

    mod addition {             // 口味检测组
        use super::*;

        #[test]
        fn add_positive_numbers_works() {
            let mut calc = setup_calculator();
            calc.add(5);
            calc.add(3);
            assert_eq!(calc.result(), 8);
        }

        #[test]
        fn add_negative_numbers_works() {
            let mut calc = setup_calculator();
            calc.add(-5);
            assert_eq!(calc.result(), -5);
        }
    }
}
```

**子模块按功能分组**——`constructor`（包装组）、`addition`（口味组）。检测项名称读起来像句子：`addition::add_positive_numbers_works`。不需要额外的测试框架功能，Rust 的模块系统天然就是质检分组管理。

## cargo test 的质检模式

```bash
cargo test                    # 启动全面质检
cargo test -- --nocapture     # 公布质检报告中的所有细节（显示 println! 输出）
cargo test -- --test-threads=1  # 一个个检，不并行
cargo test integration_test   # 只检第三方送检项目

# 只检内部实验室，跳过文档验证和第三方送检
cargo test --lib
```

## 质检清单

1. **质检实验室和后厨在一起**——测试和源码放在同一个文件，不需要单独建测试目录（集成测试除外）
2. **`#[cfg(test)]` 保证质检不干涉生产**——测试代码只编入测试构建，不进入 release
3. **`cargo test` 一条命令启动全流程**——单元测试、集成测试、文档测试一次搞定
4. **菜谱也是质检项目**——文档里的代码块写错了自动发现
5. **模块系统天然就是质检分组**——不需要 describe/it/beforeEach，Rust 的 `mod` 就是分组管理

> 适合有 Rust 基础，需要编写和维护测试的读者。

**返回：** [Rust 笔记](index.md)
