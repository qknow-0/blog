# 图形编程：窗口系统与 GPU API

同一个目标——在窗口里画一个红绿蓝渐变的三角形——分别走 macOS、Windows、Linux 的原生路径。三篇文章各自独立完整：窗口创建、GPU 初始化、shader、渲染循环、同步、构建命令和常见坑都在同一篇里，不依赖另外两篇。

## 文章

- [Cocoa + Metal：在 macOS 上画一个三角形，从窗口到像素](cocoa-metal.md) — 2026-11-19
  - AppKit 窗口、`CAMetalLayer`、运行时编译 MSL、管线状态对象、drawable 与呈现
- [Win32 + Direct3D 11：在 Windows 上画一个三角形，从消息循环到交换链](win32-d3d11.md) — 2026-11-19
  - 消息循环、`WndProc`、COM 引用计数、DXGI flip model、HLSL、资源与视图分离
- [XCB + Vulkan：在 Linux 上画一个三角形，把 GPU 的每一步都写出来](xcb-vulkan.md) — 2026-11-19
  - XCB 请求 / 回复、Vulkan 初始化链、swapchain、render pass、semaphore / fence

## 对照表

| 维度 | Cocoa + Metal | Win32 + D3D11 | XCB + Vulkan |
|:-----|:--------------|:--------------|:-------------|
| 窗口系统 | AppKit（`NSWindow` / `NSView`） | Win32（`CreateWindowExW`） | XCB（`xcb_create_window`） |
| 图形 API | Metal | Direct3D 11 | Vulkan |
| 呈现 | `CAMetalLayer` + WindowServer | DXGI 交换链 | 应用自建 `VkSwapchainKHR` |
| 同步 | 框架内部处理 | DXGI + driver | semaphore / fence 全手写 |
| shader | MSL（运行时或 `xcrun metal`） | HLSL（`D3DCompile` 或 `fxc`） | GLSL → SPIR-V（`glslc`） |
| 状态管理 | 不可变 PSO | 上下文状态 + 状态对象 | 不可变 pipeline |
| demo 行数 | ~260 | ~410 | ~820 |
| 典型失败模式 | Metal 验证层 | HRESULT | 验证层 + 自己排查同步 |

## 怎么读

- **按平台读**：只做 macOS 就看 Metal，只做 Windows 就看 D3D11，只做 Linux 就看 Vulkan；每篇都能单独跑起来。
- **按设计读**：先读 Metal 建立「设备 / 队列 / 管线 / 每帧四步」的直觉，再读 D3D11 看状态管理的另一种取舍，最后读 Vulkan 看全部显式接管时多出来的代码长什么样。
- **对照读**：三篇用的是同一个「无顶点缓冲、按顶点编号生成三角形」的技巧，可以直接比较窗口、呈现、同步和 shader 的差异。

## 验证边界

- Metal 与 Vulkan 的 demo 在作者环境中实际运行通过（Metal 在 Apple M3 上；Vulkan 在 Ubuntu 24.04 + llvmpipe + Xvfb 上）。
- D3D11 的 demo 在 macOS 上用 mingw-w64 完成交叉编译和链接检查，运行时需要 Windows 10/11；文章里明确标注了这一点。
- 所有 shader 都实际编译过，命令和输出与文章一致。

## 延伸阅读

- [C++ 面向对象系列](../../languages/cpp/oop/index.md) — 类型设计、封装、继承与运算符重载
- [C++ 并发：共享白板、原子操作与内存序](../../languages/cpp/concurrency.md) — Vulkan 的同步概念和 CPU 内存序不是一回事，但「谁等谁」的思路相通
- [C++ 编译与链接：菜单、厨房和分店](../../languages/cpp/compile-and-link.md) — 理解 MoltenVK、加载器和驱动之间的关系
