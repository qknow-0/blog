# React 入门到精通

> 本文系列基于 React 19.2 + Vite 6 + TypeScript，每篇附带可运行的实操代码和终端输出。

这个系列从零开始写一个 React 应用。不假设你有 React 经验，但假设你有 JavaScript 基础（知道箭头函数、解构、Promise、async/await）。

## 你会学到什么

5 篇文章，从环境搭建一路写到能上线的完整应用：

| 篇 | 内容 | 学完后你能做什么 |
|----|------|------------------|
| [第 1 篇](01-setup-and-jsx.md) | 环境搭建 + JSX + 第一个组件 | 在本地跑起 React 项目，理解 JSX 和组件的基本写法 |
| [第 2 篇](02-state-and-events.md) | State、事件处理、表单 | 写出有交互的组件：计数器、输入框、列表增删 |
| [第 3 篇](03-props-and-composition.md) | Props、组件组合、数据流 | 把 UI 拆成可复用的小组件，父子间传递数据和事件 |
| [第 4 篇](04-effects-and-hooks.md) | useEffect、自定义 Hook、API 调用 | 从后端拉数据、处理加载态和错误、封装可复用逻辑 |
| [第 5 篇](05-router-and-project.md) | React Router、完整实战项目 | 多页面应用 + 搜索 + 详情——一个可部署的博客前台 |

## 和深度系列的关系

如果你读完教程系列后想知道「为什么这样设计」，去看同目录下的[深度系列](../index.md)：

- 为什么 `setState` 不是同步的？→ [React 渲染机制](../react-rendering.md)
- 为什么 `useEffect` 有闭包陷阱？→ [React Hooks 不完全设计史](../react-hooks-design.md)
- React 19 有什么新东西？→ [Server Components](../react-19-server-components.md) + [新 API 全景](../react-19-new-apis.md)

## 前提条件

- Node.js 20+（`node --version` 确认）
- 一个代码编辑器（VS Code 推荐）
- 终端（macOS 用 Terminal.app 或 iTerm2）
- JavaScript 基础（ES6+）
