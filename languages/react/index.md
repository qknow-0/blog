# React 系列

> 本文系列基于 React 19.2（2026 年 6 月最新稳定版），涉及版本特性会标注最低支持版本。

React 不是一个「学习一次，到处写代码」的库——它是一个围绕声明式 UI、单向数据流、组件化构建的思想体系。

## 深度系列

不逐行翻译文档，从设计决策的角度理解 React：为什么这样设计、不这样会有什么问题。

- [React 心智模型：声明式 UI 到底改变了什么](react-mental-model.md) — 2026-06-10
- [React Hooks 不完全设计史：闭包陷阱与依赖数组](react-hooks-design.md) — 2026-06-10
- [React 渲染机制：Virtual DOM、Fiber 与批量更新](react-rendering.md) — 2026-06-10
- [React 19：Server Components 是对 Web 架构的重新分层](react-19-server-components.md) — 2026-06-10
- [React 19 新 API 全景：Actions 与状态管理新范式](react-19-new-apis.md) — 2026-06-10

## 入门到精通教程

从零开始写一个 React 应用——环境搭建、组件、路由、状态管理，每篇可运行，五篇写成一个完整的博客。

- [React 入门到精通](tutorial/index.md) — 2026-06-10（5 篇）
  - [第 1 篇：环境搭建、JSX 与第一个组件](tutorial/01-setup-and-jsx.md) — 2026-06-10
  - [第 2 篇：State、事件处理与表单](tutorial/02-state-and-events.md) — 2026-06-10
  - [第 3 篇：Props、组件组合与数据流](tutorial/03-props-and-composition.md) — 2026-06-10
  - [第 4 篇：useEffect、自定义 Hook 与 API 调用](tutorial/04-effects-and-hooks.md) — 2026-06-10
  - [第 5 篇：React Router 与实战——构建完整的博客应用](tutorial/05-router-and-project.md) — 2026-06-10

## 阅读路径

- **没写过 React，但写过其他框架**：从教程系列第 1 篇开始，再到深度系列第 1 篇理解根本思维差异
- **写过一些 React，想系统理解设计决策**：直接读深度系列
- **写过 Class 组件，不理解 Hooks 的坑**：深度系列第 2 篇
- **页面卡顿、不必要重渲染**：深度系列第 3 篇
- **想了解 React 19 有什么新东西**：深度系列第 4、5 篇
