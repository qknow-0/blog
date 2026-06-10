# 第 2 篇：State、事件处理与表单

> 本文基于 React 19.2，代码承接第 1 篇的 `react-blog` 项目。

## 从静态卡片到互动页面

第 1 篇写的博客卡片是死的——数据写死在变量里，没法改。这篇我们要让页面活起来：点击按钮、输入文字、列表增删。这些都依赖一个概念——**state**。

## `useState`：组件的记忆

```tsx
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>点击了 {count} 次</p>
      <button onClick={() => setCount(count + 1)}>+1</button>
    </div>
  );
}
```

逐行理解：

| 代码 | 含义 |
|------|------|
| `useState(0)` | 声明一个状态，初始值为 `0` |
| `count` | 当前状态值（只读，不要直接改） |
| `setCount(count + 1)` | 更新状态——React 会用新值重新渲染组件 |

**只有通过 `setState` 修改，React 才知道要重渲染。** `count = 5` 不会触发任何 UI 变化。

### 状态是独立的

```tsx
function App() {
  return (
    <div>
      <Counter />
      <Counter />
      <Counter />
    </div>
  );
}
```

三个 `<Counter />`，各自有独立的 `count`——点其中一个，其他两个不变。每次调用 `useState`，React 在该组件实例上分配一块独立的存储空间。

### 用函数更新——读到的是最新值

```tsx
// ❌ 连续两次 setCount 用同一个旧 count
setCount(count + 1);  // count 是 0 → 设为 1
setCount(count + 1);  // count 还是 0 → 设为 1（不是 2！）

// ✅ 函数式更新——每次拿到最新值
setCount(c => c + 1);  // c = 0 → 返回 1
setCount(c => c + 1);  // c = 1 → 返回 2
```

当你基于旧值计算新值时，始终用函数式更新。

## 事件处理

React 的事件和原生 DOM 事件很像，但有细微区别：

```tsx
// 原生 HTML
<button onclick="handleClick()">

// React — 驼峰命名 + 传函数引用不是字符串
<button onClick={handleClick}>

// React — 需要传参时用箭头函数
<button onClick={() => handleClick(post.id)}>
```

所有 React 事件都是合成事件（SyntheticEvent）——React 在顶层统一管理事件代理，而不是在每个 DOM 节点上单独绑定。对开发者来说，行为上几乎一致。

### 阻止默认行为

```tsx
// 原生：return false
<a href="#" onclick="return false">

// React：preventDefault()
function handleClick(e: React.MouseEvent) {
  e.preventDefault();
  console.log('链接被点击，但不会跳转');
}

<a href="/somewhere" onClick={handleClick}>点我</a>
```

## 实战：添加博客文章列表

把第 1 篇的 App 改造成一个可管理的文章列表。

```tsx
// App.tsx
import { useState } from 'react';

interface Post {
  id: number;
  title: string;
  body: string;
}

let nextId = 0;

function App() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;

    const newPost: Post = {
      id: nextId++,
      title: title.trim(),
      body: body.trim(),
    };

    setPosts([newPost, ...posts]);    // 新文章放最前面
    setTitle('');                      // 清空表单
    setBody('');
  }

  function handleDelete(id: number) {
    setPosts(posts.filter(p => p.id !== id));
  }

  return (
    <div className="app">
      <h1>我的博客</h1>

      {/* 表单区域 */}
      <form onSubmit={handleSubmit} className="form">
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="文章标题"
        />
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          placeholder="写点什么..."
          rows={4}
        />
        <button type="submit">发布</button>
      </form>

      {/* 文章列表 */}
      {posts.length === 0 ? (
        <p className="empty">还没有文章，写一篇吧。</p>
      ) : (
        posts.map(post => (
          <article key={post.id} className="card">
            <h2>{post.title}</h2>
            <p>{post.body}</p>
            <button
              className="delete-btn"
              onClick={() => handleDelete(post.id)}
            >
              删除
            </button>
          </article>
        ))
      )}
    </div>
  );
}

export default App;
```

### 这段代码里的关键模式

**1. 受控组件（Controlled Component）**

```tsx
<input
  value={title}                       // 值由 React state 控制
  onChange={e => setTitle(e.target.value)}  // 输入变化 → 更新 state
/>
```

输入框的值完全由 React state 决定——不是 DOM 自己管理的。这让你可以在任何时候读取、修改、验证输入值。这就是「React 是真相来源」在表单上的体现。

**2. 不变性更新**

```tsx
// 添加——不修改原数组，创建新数组
setPosts([newPost, ...posts]);

// 删除——filter 返回新数组，原数组不变
setPosts(posts.filter(p => p.id !== id));
```

React 用 `Object.is` 比较新旧 state——如果引用相同，跳过重渲染。直接 `posts.push(newPost)` 不会触发渲染。

**3. 列表渲染的 key**

```tsx
posts.map(post => <article key={post.id}>
```

`key` 帮助 React 识别哪些元素变了、哪些是新增的、哪些该删除。没有 key 或 key 不稳定的后果是 React 可能复用错误的 DOM 节点，导致状态错乱。

## 表单输入类型

### 文本输入

```tsx
const [text, setText] = useState('');
<input type="text" value={text} onChange={e => setText(e.target.value)} />
```

### 文本域

```tsx
const [body, setBody] = useState('');
<textarea value={body} onChange={e => setBody(e.target.value)} />
```

### 复选框

```tsx
const [checked, setChecked] = useState(false);
<label>
  <input
    type="checkbox"
    checked={checked}
    onChange={e => setChecked(e.target.checked)}
  />
  同意条款
</label>
```

### 下拉选择

```tsx
const [category, setCategory] = useState('tech');
<select value={category} onChange={e => setCategory(e.target.value)}>
  <option value="tech">技术</option>
  <option value="life">生活</option>
  <option value="reading">阅读</option>
</select>
```

注意 React 里 `checked` 和 `value` 是 attribute，不是 property——和原生 HTML 不同。

## 给文章列表加上样式

打开 `src/index.css`，追加：

```css
.form {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form input,
.form textarea {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  font-family: inherit;
  outline: none;
}

.form input:focus,
.form textarea:focus {
  border-color: #1a73e8;
}

.form button {
  align-self: flex-end;
  background: #1a73e8;
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
}

.form button:hover {
  background: #1557b0;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.card h2 {
  font-size: 1.2rem;
  margin-bottom: 8px;
}

.card p {
  color: #555;
  margin-bottom: 12px;
}

.delete-btn {
  background: none;
  border: none;
  color: #e53935;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0;
}

.delete-btn:hover {
  text-decoration: underline;
}

.empty {
  text-align: center;
  color: #999;
  margin-top: 60px;
}
```

保存，浏览器里应该看到完整的表单和文章列表功能——能写文章、能看到列表、能删除。三组 state（`posts`、`title`、`body`）各司其职，通过事件串联成一个可用的界面。

## 状态提升：两个组件共享数据

当前所有东西都在 `App` 组件里。如果要拆成 `<PostForm>` 和 `<PostList>` 两个独立组件，它们怎么共享 `posts` 状态？

答案是**把状态提升到最近的公共父组件**：

```tsx
function App() {
  const [posts, setPosts] = useState<Post[]>([]);

  return (
    <div className="app">
      <h1>我的博客</h1>
      <PostForm onPublish={post => setPosts([post, ...posts])} />
      <PostList posts={posts} onDelete={id => setPosts(posts.filter(p => p.id !== id))} />
    </div>
  );
}

function PostForm({ onPublish }: { onPublish: (post: Post) => void }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    onPublish({ id: nextId++, title: title.trim(), body: body.trim() });
    setTitle('');
    setBody('');
  }

  return (
    <form onSubmit={handleSubmit} className="form">
      <input value={title} onChange={e => setTitle(e.target.value)} placeholder="标题" />
      <textarea value={body} onChange={e => setBody(e.target.value)} placeholder="内容" rows={4} />
      <button type="submit">发布</button>
    </form>
  );
}

function PostList({ posts, onDelete }: { posts: Post[]; onDelete: (id: number) => void }) {
  if (posts.length === 0) return <p className="empty">还没有文章。</p>;
  return posts.map(post => (
    <article key={post.id} className="card">
      <h2>{post.title}</h2>
      <p>{post.body}</p>
      <button className="delete-btn" onClick={() => onDelete(post.id)}>删除</button>
    </article>
  ));
}
```

这就是 React 的数据流：**状态在顶层，props 往下传，回调往上冒**。

## 本篇要点

| 概念 | 一句话 |
|------|--------|
| `useState` | 组件的记忆——改了它，组件重渲染 |
| 函数式更新 | `setCount(c => c + 1)` — 基于旧值算新值 |
| 受控组件 | 表单值由 state 驱动，不是 DOM 自己管 |
| 不变性更新 | 创建新数组/对象，不要就地改旧值 |
| 状态提升 | 共享状态放在最近的公共父组件 |

下一章深入 Props 和组件组合——怎么把 UI 拆成高内聚、低耦合的小块。
