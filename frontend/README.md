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
| 工作台 | `/#/` | `src/views/WorkspaceView.vue` | 快捷进入数据库连接、表与关系、图例图库和通用设置 |
| 数据库 / 数据库连接 | `/#/database/sources` | `src/views/DatabaseConnectionView.vue` | 填写 MySQL 参数，测试连接或保存为后端当前连接 |
| 数据库 / 表与关系 | `/#/database/schema` | `src/views/TableSchemaView.vue` | 浏览表、字段及类型，查看主外键和表关系图 |
| 可视化 / 折线、柱状图与标记 | `/#/visualization/chart-types` | `src/views/ChartTypesView.vue` | 41 个本地图例 |
| 可视化 / 图像、等值线与场 | `/#/visualization/images-contours-fields` | `src/views/ImagesContoursView.vue` | 48 个本地图例 |
| 可视化 / 统计图 | `/#/visualization/statistics` | `src/views/StatisticsView.vue` | 28 个本地图例 |
| 可视化 / 饼图与极坐标图 | `/#/visualization/pie-polar` | `src/views/PiePolarView.vue` | 10 个本地图例 |
| 可视化 / 子图、坐标轴与画布 | `/#/visualization/subplots-axes-figures` | `src/views/SubplotsAxesView.vue` | 36 个本地图例 |
| 图卡打开的工作台 | `/#/visualization/workbench/:chartId` | `src/views/ChartWorkbenchView.vue` | 查看所选图例、所需字段和 Python 示例代码 |
| EyeAgent | `/#/eye-agent` | `src/views/EyeAgentView.vue` | 用自然语言描述问题，获取表关联、指标和图表建议 |
| 系统设置 / 通用设置 | `/#/settings/general` | `src/views/GeneralSettingsView.vue` | 界面主题和日期格式 |
| 系统设置 / 服务配置 | `/#/settings/service` | `src/views/ServiceSettingsView.vue` | Flask 服务地址与接口请求超时 |

工作台、导航切换、数据库连接、表与关系和图例图库已可用。待接入的业务页面展示功能规划。

五类图库按 Matplotlib 官方栏目顺序展示全部 163 个图例。点击图片进入对应图表工作台，从工作台可以回到图例所在分类。导航名称、图卡标题和字段说明使用中文。图库与工作台使用半透明遮罩标识待接入的示例，图卡可点击。 [Matplotlib 官方图库](https://matplotlib.org/stable/gallery/index.html)

`npm run build` 会生成静态文件到 `dist/`。部署静态文件时，由站点的反向代理把同域的 `/api` 请求转发给 Flask。

## 连接 MySQL

启动监听 5111 的 Flask 后端后，在侧栏打开 **数据库 → 数据库连接**。填写 MySQL 主机、端口、数据库名、用户名和密码。页面会显示后端当前配置的非密码字段。使用需要密码的账号时，每次提交请重新输入密码。

- **测试连接** 使用表单参数执行 `SELECT 1`。
- **保存并连接** 在验证通过后更新 Flask 设置，后续查询会使用新连接。配置保存在后端本地，重启后继续生效。

## 表与关系

在 **数据库 → 表与关系** 中，左侧搜索并选择数据表，右侧查看字段类型、主外键、可空性、默认值和备注。页面使用 Flask 当前生效的 MySQL 连接。保存新连接后，重新打开页面或点「刷新表列表」即可读取新库。

「关系图」使用 `@antv/x6` 2.18.1 的核心库，在 Vue 2 组件中渲染 SVG 表节点。组件用 X6 的 Port 将连线定位到对应字段。图中显示当前表及其直接关联的表，连线由外键指向被引用字段。点击同库的表可切换查看，点击连线或下方约束可高亮对应字段连线。拖动可调整图上位置，支持缩放及适应画布。

点页面顶部的 **查看 ER 图**，主内容区会切换到当前库的关系图。点「返回表与关系」回到表列表。Dagre 自动排列所有可见基本表，X6 绘制表名、字段、类型和库内外键。表卡片按字段宽度排版，超长内容以省略号表示，悬停可查看全文。红色 PK 表示主键，绿色 FK 表示外键。连线上标注外键字段名，点选连线可以高亮同一约束的所有字段映射，点选表可打开字段详情。无外键的表也会显示在画布中。

关系来自 MySQL 实际声明的外键约束。复合外键在图中按字段配对连线，在约束列表中合为一组。跨库的可见关系按库名限定，表详情浏览范围是当前连接配置的数据库。

[AntV X6 官方 ER 图示例](https://x6.antv.antgroup.com/en/examples/showcase/practices/er/)

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
| `src/components/TableRelationsGraph.vue` | AntV X6 关系图、图布局和交互 |
| `src/api/database.js` | 管理 MySQL 连接及读取表结构 |
| `src/api/health.js` | 健康接口请求 |
| `vite.config.js` | 前端开发端口和接口代理 |

新增导航项时，在 `src/views/` 下创建独立的 `.vue` 文件，再将路径、标题和组件添加到 `MainView.vue` 的导航配置中。
