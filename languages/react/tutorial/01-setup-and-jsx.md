# 第 1 篇：环境搭建、JSX 与第一个组件

> 本文基于 React 19.2 + Vite 6 + TypeScript。

## 为什么用 Vite 而不是 Create React App

Create React App（CRA）曾经是 React 官方推荐的脚手架，但已经两年没维护了。Vite 是现在的标准选择：

| | CRA | Vite |
|------|-----|------|
| 启动速度 | 30s+（Webpack） | <1s（ESBuild） |
| HMR 热更新 | 2-5s | 即时 |
| TypeScript | 需额外配置 | 开箱即用 |
| 生产构建 | Webpack | Rollup |

**全系列都用 Vite。**

## 创建项目

```bash
# 确保 Node.js 版本 >= 20
node --version
# v22.11.0

# 用 Vite 创建 React + TypeScript 项目
npm create vite@latest react-blog -- --template react-ts
```

看到这个输出：

```
Scaffolding project in react-blog...

Done. Now run:

  cd react-blog
  npm install
  npm run dev
```

```bash
cd react-blog
npm install
```

安装完成后看一下项目结构：

```bash
tree -L 2 -I node_modules
```

```
react-blog/
├── index.html              # 入口 HTML
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/                 # 静态资源（不经过构建）
└── src/
    ├── main.tsx            # 应用入口，React 挂载点
    ├── App.tsx             # 根组件
    ├── App.css
    └── index.css
```

Vite 生成的项目比 CRA 简洁得多——没有 `src/reportWebVitals.ts` 之类你永远不会改的文件。

## 启动开发服务器

```bash
npm run dev
```

```
VITE v6.x.x  ready in 320 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

浏览器打开 `http://localhost:5173/`，看到 Vite + React logo 页面——项目跑起来了。

## 入口文件发生了什么

打开 `index.html`：

```html
<!doctype html>
<html>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

关键就两行：
- `<div id="root">` — React 的挂载点，整个应用都渲染在这个 div 里
- `<script type="module" src="/src/main.tsx">` — Vite 的入口，加载 `main.tsx`

再看 `src/main.tsx`：

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

三件事：

1. **`createRoot(document.getElementById('root')!)`** — 告诉 React 在 `#root` div 上创建根节点（React 18+ 的方式）
2. **`<StrictMode>`** — 开发模式下多做一次渲染，帮你发现潜在问题（生产环境无效）
3. **`<App />`** — 渲染根组件

`!` 是 TypeScript 的非空断言——`getElementById` 可能返回 `null`，但我们确定 `#root` 存在。

## 你的第一个组件

打开 `src/App.tsx`，删掉模板代码，改写成这样：

```tsx
function App() {
  return (
    <div>
      <h1>我的博客</h1>
      <p>每一行代码都有它的理由。</p>
    </div>
  );
}

export default App;
```

保存，浏览器自动刷新——你看到了新内容。Vite 的 HMR（Hot Module Replacement）在文件变更时把改动推送进浏览器，不刷新页面。

## JSX：在 JavaScript 里写 HTML

上面的 `<h1>` 不是 HTML，是 **JSX**——JavaScript 的语法扩展。Babel 或 TypeScript 把它编译成普通的 JavaScript：

```tsx
// 你写的 JSX
const element = <h1 className="title">Hello</h1>;

// 编译后（简化版）
import { jsx as _jsx } from "react/jsx-runtime";
const element = _jsx("h1", { className: "title", children: "Hello" });
```

### JSX 和 HTML 的几个关键差异

**1. `className` 不是 `class`**

```tsx
// ❌
<div class="container">

// ✅
<div className="container">
```

`class` 是 JavaScript 的保留字。React 用 `className` 代替。

**2. 用 `{}` 嵌入 JavaScript**

```tsx
const name = 'Alice';
const element = <h1>Hello, {name}</h1>;       // Hello, Alice

const sum = <p>1 + 1 = {1 + 1}</p>;           // 1 + 1 = 2

const items = ['🍎', '🍌', '🍇'];
const list = (
  <ul>
    {items.map(item => <li key={item}>{item}</li>)}
  </ul>
);
```

花括号里可以放任何 JavaScript 表达式——变量、函数调用、三元运算符、`map`、`filter`。但不能放语句（`if`、`for`、`while`）。

**3. 所有标签必须闭合**

```tsx
// ❌ HTML 里可以这样
<br>
<img src="a.png">

// ✅ JSX 里必须闭合
<br />
<img src="a.png" />
```

**4. 返回的内容必须有单一根元素**

```tsx
// ❌ 不能返回两个平级元素
return (
  <h1>Title</h1>
  <p>Content</p>
);

// ✅ 包在一个 div 里
return (
  <div>
    <h1>Title</h1>
    <p>Content</p>
  </div>
);

// ✅ 或者用 Fragment——不产生额外的 DOM 节点
import { Fragment } from 'react';

return (
  <Fragment>
    <h1>Title</h1>
    <p>Content</p>
  </Fragment>
);

// ✅ Fragment 的简写形式
return (
  <>
    <h1>Title</h1>
    <p>Content</p>
  </>
);
```

**5. 用 `{}` 设置属性**

```tsx
const imageUrl = 'https://example.com/photo.png';

// ❌ 字符串里拼接——在 JSX 里不生效
<img src="{imageUrl}" />      // src 就是 "{imageUrl}" 这个字符串

// ✅ 用花括号
<img src={imageUrl} />
```

## 写一个带数据的博客卡片

把 `App.tsx` 改成一个展示博客文章的卡片：

```tsx
function App() {
  const post = {
    title: '为什么 Redux 的 boilerplate 不是多余的',
    author: 'Wei',
    date: '2026-06-10',
    tags: ['React', '状态管理'],
    excerpt: '每次写 Redux 都觉得在写样板代码。但样板代码消除的不只是灵活性——还有可追溯性。'
  };

  return (
    <div className="app">
      <article className="card">
        <h1>{post.title}</h1>
        <div className="meta">
          <span>{post.author}</span> · <span>{post.date}</span>
        </div>
        <div className="tags">
          {post.tags.map(tag => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
        <p className="excerpt">{post.excerpt}</p>
      </article>
    </div>
  );
}

export default App;
```

加点样式——打开 `src/index.css`，删掉默认样式，写入：

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

.app {
  max-width: 720px;
  margin: 40px auto;
  padding: 0 16px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.card h1 {
  font-size: 1.5rem;
  margin-bottom: 12px;
}

.meta {
  color: #888;
  font-size: 0.875rem;
  margin-bottom: 12px;
}

.tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tag {
  background: #e8f0fe;
  color: #1a73e8;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
}

.excerpt {
  color: #555;
  font-size: 1rem;
}
```

保存后浏览器里应该看到一张干净的博客卡片：

```
┌─────────────────────────────────────┐
│                                     │
│  为什么 Redux 的 boilerplate        │
│  不是多余的                          │
│                                     │
│  Wei · 2026-06-10                   │
│                                     │
│  [React] [状态管理]                  │
│                                     │
│  每次写 Redux 都觉得在写样板代码...   │
│                                     │
└─────────────────────────────────────┘
```

## 本篇要点

- **Vite** 是 React 开发的现代标准，告别 Webpack 的慢
- **JSX** 是 JavaScript，不是 HTML——`className`、`{}` 表达式、标签闭合
- **组件**就是一个返回 JSX 的函数
- **`createRoot` + `render`** 把 React 组件树挂载到页面上的某个 DOM 节点

下一篇会把这张静态卡片变成有交互的页面——按钮点击、状态变化、表单输入。
