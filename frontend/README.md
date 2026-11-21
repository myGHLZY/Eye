# Eye 前端

使用 Vue 2.7、Vue Router、Element UI 和 Vite。主页面提供 Flask 健康接口的连接测试。

## 启动前端

需要 Node.js 18、20 或 22 及以上版本。在 VS Code 打开 Eye 仓库，在集成终端从仓库根目录执行以下命令。首次运行用 `npm ci` 安装依赖。

```bash
cd frontend
npm ci
npm run dev
```

启动后访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。在终端按 `Ctrl+C` 停止服务。

## 测试后端连接

点击首页的「测试连接」。页面向 `GET /api/health` 发起请求，Vite 将请求代理到 `http://127.0.0.1:5111`。联调时请让 Flask 监听 `5111`，成功时页面显示 `{"data":{"status":"ok"}}`。

需要给 Flask 指定端口时，可在 `backend/` 执行 `python -m flask --app wsgi run --host 127.0.0.1 --port 5111`。

`npm run build` 会生成静态文件到 `dist/`。部署静态文件时，由站点的反向代理把同域的 `/api` 请求转发给 Flask。

## 目录

| 路径 | 职责 |
| --- | --- |
| `src/main.js` | 初始化 Vue 和路由 |
| `src/App.vue` | 应用根组件 |
| `src/router/` | 页面路由 |
| `src/views/MainView.vue` | 主页面和健康检查按钮 |
| `src/api/health.js` | 健康接口请求 |
| `vite.config.js` | 前端开发端口和接口代理 |

新增页面时，在 `src/views/` 下创建独立的 `.vue` 文件，并在 `src/router/index.js` 添加路由。
