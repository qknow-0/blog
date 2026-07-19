# Composite 模式：用 enum 递归表达「整体和部分一样」

> 文件夹里可以放文件，也可以放文件夹。菜单项里可以有子菜单。HTML 里 `div` 里可以套 `div`。这些场景有一个共同特点：**整体和部分是同一种东西，能递归嵌套**。Composite 模式就是这个——用同一套接口处理单个对象和对象的集合。

本文基于 Rust 1.96。

## 比喻：俄罗斯套娃

俄罗斯套娃——打开一个娃娃，里面还是一个娃娃，再打开，里面还有一个。你对最外层的操作（拿起、放下、摇晃）对整个嵌套结构都有效。

```text
最外层娃娃
  ├── 中层娃娃
  │   ├── 内层娃娃
  │   └── 内层娃娃
  └── 中层娃娃
```

不管是单独一个娃娃还是一组娃娃——它们都是「娃娃」。你可以对任意一层做相同的操作。

## GoF 定义

```text
Composite：
  将对象组合成树形结构以表示「部分-整体」的层次结构。
  Composite 使得客户端对单个对象和组合对象的使用具有一致性。

         ┌─────────────┐
         │  Component   │  ← 统一的接口（叶子和组合都实现它）
         │ + operation()│
         └──────┬───────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───┴────────┐    ┌─────────┴─────────┐
│   Leaf     │    │    Composite      │
│ 叶子节点    │    │ 包含子节点的集合    │
│ 没有子节点  │    │ children: Vec<...> │
└────────────┘    └───────────────────┘
```

## Java/C++ 的写法 vs Rust 的写法

传统 OOP 用一个抽象类 `Component` 让 `Leaf` 和 `Composite` 分别继承：

```java
// Java 版
interface Component { int size(); }
class File implements Component { /* ... */ }
class Folder implements Component {
    List<Component> children;
    int size() { return children.stream().mapToInt(Component::size).sum(); }
}
```

Rust 没有继承，**用 enum 递归**天然就是 Composite：

```rust
enum FileSystem {
    File { name: String, size: u64 },              // 叶子
    Folder { name: String, children: Vec<FileSystem> },  // 组合
}
```

enum 的每个变体就是树的一个节点。`Folder` 里 `children: Vec<FileSystem>` 就是递归嵌套——文件夹里可以放文件和文件夹。

## Rust 版：文件系统

```rust
enum FileSystem {
    File {
        name: String,
        size: u64,
    },
    Folder {
        name: String,
        children: Vec<FileSystem>,
    },
}

impl FileSystem {
    /// 计算总大小——叶子返回自己的大小，组合递归求和
    fn total_size(&self) -> u64 {
        match self {
            FileSystem::File { size, .. } => *size,     // 叶子：自己就是全部
            FileSystem::Folder { children, .. } => {      // 组合：子节点求和
                children.iter().map(|c| c.total_size()).sum()
            }
        }
    }

    /// 找到所有超过指定大小的文件（返回扁平的列表）
    fn find_large_files(&self, threshold: u64) -> Vec<String> {
        match self {
            FileSystem::File { name, size } => {
                if *size > threshold {
                    vec![name.clone()]
                } else {
                    vec![]
                }
            }
            FileSystem::Folder { children, .. } => {
                children.iter()
                    .flat_map(|c| c.find_large_files(threshold))
                    .collect()
            }
        }
    }

    /// 用缩进打印整个树
    fn print_tree(&self, depth: usize) {
        let indent = "  ".repeat(depth);
        match self {
            FileSystem::File { name, size } => {
                println!("{}📄 {} ({} bytes)", indent, name, size);
            }
            FileSystem::Folder { name, children } => {
                println!("{}📁 {}/", indent, name);
                for child in children {
                    child.print_tree(depth + 1);
                }
            }
        }
    }
}
```

用法：

```rust
let root = FileSystem::Folder {
    name: "src".into(),
    children: vec![
        FileSystem::File { name: "main.rs".into(), size: 2048 },
        FileSystem::Folder {
            name: "utils".into(),
            children: vec![
                FileSystem::File { name: "math.rs".into(), size: 4096 },
                FileSystem::File { name: "string.rs".into(), size: 1024 },
            ],
        },
    ],
};

println!("总大小: {} bytes", root.total_size());       // 7168
println!("大文件: {:?}", root.find_large_files(2000));  // ["main.rs", "math.rs"]
root.print_tree(0);
// 📁 src/
//   📄 main.rs (2048 bytes)
//   📁 utils/
//     📄 math.rs (4096 bytes)
//     📄 string.rs (1024 bytes)
```

**对单个文件和整个文件夹，`total_size()` 的调用方式一模一样**——这就是 Composite 的核心价值。

## 为什么 Rust 的 enum 比 OOP 的继承更适合 Composite

| | OOP 继承 | Rust enum |
|---|---|---|
| 加一种节点 | 写一个新 class | 加一个 enum 变体 |
| 加一个操作 | 每个 class 加一个方法 | 每个 match 分支加一行 |
| 所有变体一览 | 分散在不同文件 | **一个 enum 定义全部可见** |
| 递归引用 | `List<Component>` | `Vec<FileSystem>`——不用 Box |
| 内存布局 | 堆分配每个节点 | 栈+堆，enum 本身紧凑 |

**一个 enum 定义全部可见**——这是 Rust 最大的优势。看 enum 定义就知道整个树有哪些节点类型，不需要翻三个文件。

## 第二个例子：GUI 组件树

```rust
enum UIComponent {
    Button { label: String, width: u32, height: u32 },
    Text { content: String },
    Container {
        layout: Layout,
        children: Vec<UIComponent>,
    },
}

enum Layout { Vertical, Horizontal }

impl UIComponent {
    fn render(&self) -> String {
        match self {
            UIComponent::Button { label, .. } => {
                format!("[ {} ]", label)
            }
            UIComponent::Text { content } => content.clone(),
            UIComponent::Container { layout, children } => {
                let sep = match layout {
                    Layout::Vertical => "\n",
                    Layout::Horizontal => " | ",
                };
                children.iter()
                    .map(|c| c.render())
                    .collect::<Vec<_>>()
                    .join(sep)
            }
        }
    }
}
```

## 用 trait object 做 Composite（适应多种节点类型时）

enum 适合**节点种类已知**的场景。如果节点种类在运行期不确定（比如插件系统），用 trait + `Box<dyn>`：

```rust
trait Component {
    fn size(&self) -> u64;
    fn name(&self) -> &str;
}

struct MyFile { name: String, size: u64 }
impl Component for MyFile {
    fn size(&self) -> u64 { self.size }
    fn name(&self) -> &str { &self.name }
}

struct MyFolder {
    name: String,
    children: Vec<Box<dyn Component>>,  // ← trait object 递归
}

impl Component for MyFolder {
    fn size(&self) -> u64 {
        self.children.iter().map(|c| c.size()).sum()
    }
    fn name(&self) -> &str { &self.name }
}
```

选 enum 还是 trait object：

| | enum | trait object |
|---|---|---|
| 节点种类 | 编译期确定 | 运行期可扩展 |
| 内存 | 更紧凑 | 每个 Box 一次堆分配 |
| 读代码 | 一个 enum 看清所有变体 | 分散在各 impl 块 |
| 适合 | 文件系统、AST、GUI 组件 | 插件系统、用户可扩展节点 |

**优先用 enum**。只有确实需要在运行期添加新的节点类型时才用 `Box<dyn>`。

## 什么时候用

- 数据有天然的**树形层级**——文件系统、组织架构、菜单、AST
- 需要对单个对象和对象集合**做同样的操作**——计算大小、渲染、搜索
- 想加新的节点类型

**不用 Composite**：

- 没层级关系——别硬造树
- 整体和部分的行为完全不一样——叶子不需要 `children` 方法

## 小结

Composite 在 Rust 里比在 OOP 语言里更简单——enum + `Vec<Self>` 天然就是树。不用继承、不用抽象类、不用类型转换。

核心代码就这几行：

```rust
enum Node {
    Leaf { data: Data },
    Branch { data: Data, children: Vec<Node> },
}
```

一对 enum + match 替代了 OOP 里一整套 Component/Leaf/Composite 的继承体系。

---

**上一篇：** [Bridge 模式](bridge.md)
**下一篇：** [Decorator 模式](decorator.md)
**返回：** [设计模式：Rust 视角](index.md)
