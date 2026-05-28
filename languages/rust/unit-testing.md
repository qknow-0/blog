# Rust 单元测试：编译器帮你测

> 本文基于 Rust 1.85。

Rust 的测试框架内建在语言里。不需要装 pytest、JUnit、Jest——`cargo test` 开箱即用。测试代码和业务代码放在同一个文件里，编译期也能捕获测试中的类型错误。

## 基本语法

```rust
// src/lib.rs
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    fn test_add_negative() {
        assert_eq!(add(-1, -2), -3);
    }
}
```

`#[cfg(test)]` 告诉编译器这个模块只在 `cargo test` 时编译，正常构建不包含测试代码。`#[test]` 标记测试函数。

运行：

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

## 常用断言

```rust
// 相等/不等
assert_eq!(result, expected);
assert_ne!(result, unexpected);

// 布尔
assert!(value > 0);
assert!(result.is_ok());

// 自定义错误消息
assert_eq!(add(2, 3), 6, "2 + 3 应该等于 5，实际得到 {}", add(2, 3));
```

## 测试 panic

用 `#[should_panic]` 验证函数确实会 panic：

```rust
pub fn divide(a: i32, b: i32) -> i32 {
    if b == 0 {
        panic!("除数不能为零");
    }
    a / b
}

#[test]
#[should_panic(expected = "除数不能为零")]
fn test_divide_by_zero() {
    divide(10, 0);
}
```

`expected` 参数可选——指定了就是精确匹配 panic 消息的子串，不指定就是只要 panic 就算通过。

## 测试 Result

测试可以直接返回 `Result`，用 `?` 传播错误：

```rust
#[test]
fn test_read_file() -> std::io::Result<()> {
    let content = std::fs::read_to_string("Cargo.toml")?;
    assert!(content.contains("[package]"));
    Ok(())
}
```

返回 `Err` 就等于测试失败，不需要 `unwrap()`。

## 组织测试：单元 vs 集成

```
src/
├── lib.rs              # 单元测试写在 #[cfg(test)] mod tests 里
├── main.rs
└── calculator.rs
tests/
└── integration_test.rs # 集成测试放 tests/ 目录下
```

**单元测试**和源码放一起，可以访问私有函数。**集成测试**放 `tests/` 目录下，只能调用公开 API，模拟外部使用者。

```rust
// tests/integration_test.rs
use my_crate::add;  // 只能 import pub 函数

#[test]
fn integration_test_add() {
    assert_eq!(add(1, 2), 3);
}
```

集成测试不需要 `#[cfg(test)]`——`tests/` 目录下的文件自动只被 `cargo test` 编译。

## 测试函数 vs 测试文件

```rust
// 只跑特定测试
cargo test test_add              // 按名称过滤
cargo test tests::calculator     // 按模块过滤

// 忽略慢测试
#[test]
#[ignore]                        // 默认跳过
fn test_slow_network_call() {
    // ...
}

cargo test -- --ignored          // 只跑被忽略的
cargo test -- --include-ignored  // 全部跑
```

## 文档测试

Rust 的文档注释里的代码块也是测试：

```rust
/// 两个整数相加。
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

`cargo test` 会编译并运行文档中所有代码块。文档写错了，测试直接挂——倒逼文档和代码保持一致。

## 测试组织最佳实践

一个中等复杂度的模块，测试结构长这样：

```rust
// src/calculator.rs
pub struct Calculator { /* ... */ }

impl Calculator {
    pub fn new() -> Self { /* ... */ }
    pub fn add(&mut self, value: i32) { /* ... */ }
    pub fn result(&self) -> i32 { /* ... */ }
}

#[cfg(test)]
mod tests {
    use super::*;

    // 辅助函数——不需要 #[test]
    fn setup_calculator() -> Calculator {
        Calculator::new()
    }

    mod constructor {
        use super::*;  // 子模块需要重新 import

        #[test]
        fn new_calculator_has_zero_result() {
            let calc = setup_calculator();
            assert_eq!(calc.result(), 0);
        }
    }

    mod addition {
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

**子模块按功能分组**——`constructor`、`addition`。测试名读起来像句子：`addition::add_positive_numbers_works`。不需要额外的测试框架功能，Rust 的模块系统就够了。

## 和 cargo 的配合

```bash
cargo test                    # 全部测试
cargo test -- --nocapture     # 显示 println! 输出
cargo test -- --test-threads=1  # 单线程跑
cargo test integration_test   # 只跑集成测试

# 只跑 lib 的测试，跳过 doctest 和集成测试
cargo test --lib
```

## 关键点

1. **测试和代码放一起**——不需要单独建测试目录（除非集成测试）
2. **`#[cfg(test)]` 保证测试不编译到 release 里**
3. **`cargo test` 一条命令搞定**——单元测试、集成测试、文档测试
4. **文档也是测试**——代码块写错了自动发现
5. **模块系统组织测试**——不需要 describe/it/beforeEach，Rust 的 `mod` 天然分层

> 适合有 Rust 基础，需要编写和维护测试的读者。
