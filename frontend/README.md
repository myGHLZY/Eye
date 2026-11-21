# Eye 前端

使用 Vue 2.7、Vue Router、Element UI 和 Vite。主页面是 Eye 的工作台，提供数据库、可视化、EyeAgent 和系统设置入口。

## 启动前端

需要 Node.js 18、20 或 22 及以上版本。用 VS Code 打开前端工程。桌面上的 `Eye` 就是前端工程目录，从 GitHub 检出的完整仓库中，前端工程位于 `frontend/`。在对应目录的集成终端执行以下命令。

```bash
npm ci
npm run dev
```

启动后访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。在终端按 `Ctrl+C` 停止服务。

## 主页面与导航

`MainView.vue` 保留 Element UI 布局和侧栏。每个可点击的导航项都有独立的路由和 Vue 文件，页面显示在 Main 内容区。子菜单支持展开，当前项与页头面包屑会随路由切换。浏览器前进、后退和刷新都能回到对应页面。

| 导航 | 路由 | 页面文件 | 功能 |
| --- | --- | --- | --- |
| 工作台 | `/#/` | `src/views/WorkspaceView.vue` | 快捷进入数据源管理、表与关系、图例图库和通用设置 |
| 数据库 / 数据源管理 | `/#/database/sources` | `src/views/DataSourcesView.vue` | 选择 MySQL 数据源、配置连接并检查连通性 |
| 数据库 / 表与关系 | `/#/database/schema` | `src/views/TableSchemaView.vue` | 浏览表、字段及类型，查看主外键和表关系图 |
| 数据库 / 数据预览 | `/#/database/preview` | `src/views/DataPreviewView.vue` | 分页查看样例数据，按字段筛选和排序 |
| 可视化 / 折线、柱状图与标记 | `/#/visualization/chart-types` | `src/views/ChartTypesView.vue` | 41 个本地图例 |
| 可视化 / 图像、等值线与场 | `/#/visualization/images-contours-fields` | `src/views/ImagesContoursView.vue` | 48 个本地图例 |
| 可视化 / 统计图 | `/#/visualization/statistics` | `src/views/StatisticsView.vue` | 28 个本地图例 |
| 可视化 / 饼图与极坐标图 | `/#/visualization/pie-polar` | `src/views/PiePolarView.vue` | 10 个本地图例 |
| 可视化 / 子图、坐标轴与画布 | `/#/visualization/subplots-axes-figures` | `src/views/SubplotsAxesView.vue` | 36 个本地图例 |
| 图卡打开的工作台 | `/#/visualization/workbench/:chartId` | `src/views/ChartWorkbenchView.vue` | 查看所选图例、所需字段和 Python 示例代码 |
| EyeAgent | `/#/eye-agent` | `src/views/EyeAgentView.vue` | 用自然语言描述问题，获取表关联、指标和图表建议 |
| 系统设置 / 通用设置 | `/#/settings/general` | `src/views/GeneralSettingsView.vue` | 界面主题、日期格式和默认每页条数 |
| 系统设置 / 服务配置 | `/#/settings/service` | `src/views/ServiceSettingsView.vue` | Flask 服务地址与接口请求超时 |

工作台、导航切换和图例图库已可用。各业务页面以「待接入」展示功能规划。

五类图库按 Matplotlib 官方栏目顺序展示全部 163 个图例。点击图片进入对应图表工作台，从工作台可以回到图例所在分类。导航名称、图卡标题和字段说明使用中文。图库与工作台使用半透明遮罩标识待接入的示例，图卡可点击。 [Matplotlib 官方图库](https://matplotlib.org/stable/gallery/index.html)

`npm run build` 会生成静态文件到 `dist/`。部署静态文件时，由站点的反向代理把同域的 `/api` 请求转发给 Flask。

## 目录

| 路径 | 职责 |
| --- | --- |
| `src/main.js` | 初始化 Vue 和路由 |
| `src/App.vue` | 应用根组件 |
| `src/router/index.js` | 注册 Main 和各导航子路由 |
| `src/views/MainView.vue` | 共用布局、侧栏导航和子路由配置 |
| `src/views/` | 各导航项的独立页面 |
| `src/components/ModuleOverview.vue` | 各页面共用的功能概览卡片 |
| `src/components/ChartGallery.vue` | 五个分类共用的图卡布局 |
| `src/assets/chart-preview.css` | 待接入图例的遮罩样式 |
| `src/data/chartExamples.js` | 分类、图例名称、所需字段和原始示例链接 |
| `public/visualization/` | 本地图例图片和 Matplotlib 许可文件 |
| `src/api/health.js` | 健康接口请求 |
| `vite.config.js` | 前端开发端口和接口代理 |

新增导航项时，在 `src/views/` 下创建独立的 `.vue` 文件，再将路径、标题和组件添加到 `MainView.vue` 的导航配置中。
