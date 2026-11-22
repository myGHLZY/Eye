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
| 工作台 | `/#/` | `src/views/WorkspaceView.vue` | 快捷进入数据库连接、图例图库和通用设置 |
| 数据库 / 数据库连接 | `/#/database/sources` | `src/views/DatabaseConnectionView.vue` | 填写 MySQL 参数，测试连接或保存为后端当前连接 |
| 数据库 / 数据库连接 / 库名 | `/#/database/connections/:connectionId` | `src/views/TableSchemaView.vue` | 浏览表、字段及类型，查看主外键和表关系图 |
| 可视化 / 折线、柱状图与标记 | `/#/visualization/chart-types` | `src/views/ChartTypesView.vue` | 41 个本地图例 |
| 可视化 / 图像、等值线与场 | `/#/visualization/images-contours-fields` | `src/views/ImagesContoursView.vue` | 48 个本地图例 |
| 可视化 / 统计图 | `/#/visualization/statistics` | `src/views/StatisticsView.vue` | 28 个本地图例 |
| 可视化 / 饼图与极坐标图 | `/#/visualization/pie-polar` | `src/views/PiePolarView.vue` | 10 个本地图例 |
| 可视化 / 子图、坐标轴与画布 | `/#/visualization/subplots-axes-figures` | `src/views/SubplotsAxesView.vue` | 36 个本地图例 |
| 可视化 / 特殊图 | `/#/visualization/specialty-plots` | `src/views/SpecialtyPlotsView.vue` | 12 个本地图例，雷达图排第一 |
| 图卡打开的工作台 | `/#/visualization/workbench/:chartId` | `src/views/ChartWorkbenchView.vue` | 查看所选图例、所需字段和 Python 示例代码 |
| 制作柱状图 | `/#/visualization/bar-chart/:chartId` | `src/views/BarChartEditorView.vue` | 选择数据库，调整样式并预览柱状图 |
| EyeAgent | `/#/eye-agent` | `src/views/EyeAgentView.vue` | 用自然语言描述问题，获取表关联、指标和图表建议 |
| 系统设置 / 通用设置 | `/#/settings/general` | `src/views/GeneralSettingsView.vue` | 界面主题和日期格式 |
| 系统设置 / 服务配置 | `/#/settings/service` | `src/views/ServiceSettingsView.vue` | Flask 服务地址与接口请求超时 |

工作台、导航切换、数据库连接、库结构浏览和图例图库已可用。待接入的业务页面展示功能规划。

六类图库共展示 175 个图例。点击图片进入对应图表工作台，从工作台可以回到图例所在分类。已有制作功能的图例显示彩色，其余图例使用灰度遮罩。 [Matplotlib 官方图库](https://matplotlib.org/stable/gallery/index.html) · [特殊图库](https://matplotlib.org/stable/gallery/specialty_plots/index.html)

`npm run build` 会生成静态文件到 `dist/`。部署静态文件时，由站点的反向代理把同域的 `/api` 请求转发给 Flask。

## 连接 MySQL

启动监听 5111 的 Flask 后端后，在侧栏点击 **数据库 → 数据库连接** 打开表单。已保存的库名可通过旁边的箭头展开。填写 MySQL 主机、端口、数据库名、用户名和密码。页面会显示后端当前配置的非密码字段。使用需要密码的账号时，每次提交请重新输入密码。

- **测试连接** 使用表单参数执行 `SELECT 1`。
- **保存并连接** 在验证通过后更新 Flask 设置，并按库名在「数据库连接」下加入一项。已保存的连接记录会在后端重启后继续显示。

## 数据库结构和 ER 图

在 **数据库 → 数据库连接** 下点击库名。左侧可搜索并选择数据表，右侧查看字段类型、主外键、可空性、默认值和备注。页面按所选连接读取结构。点击右上角的「断开连接」可移除此库的已保存连接，并返回连接表单。同名数据库来自不同连接时，可悬停库名查看主机、端口与用户名。

「字段」页签上方显示表结构，下面的「表数据」按实际字段生成记录表格。可切换页码、每页条数和刷新数据，也可选择字段进行精确筛选或查询 NULL。

点击「新增记录」或某一行的「编辑」，表单会按字段类型和默认值提供可选的填写方式。删除记录需确认，增删改成功后会自动刷新列表。编辑和删除依赖表的完整主键，复合主键也支持。数据库账号的权限与唯一键、外键约束决定操作能否成功。

「关系图」使用 `@antv/x6` 2.18.1 的核心库，在 Vue 2 组件中渲染 SVG 表节点。组件用 X6 的 Port 将连线定位到对应字段。图中显示当前表及其直接关联的表，连线由外键指向被引用字段。点击同库的表可切换查看，点击连线或下方约束可高亮对应字段连线。拖动可调整图上位置，支持缩放及适应画布。

点页面顶部的 **查看 ER 图**，主内容区会切换到当前库的关系图。点「返回数据库表」回到此库的表列表。Dagre 自动排列所有可见基本表，X6 绘制表名、字段、类型和库内外键。表卡片按字段宽度排版，超长内容以省略号表示，悬停可查看全文。红色 PK 表示主键，绿色 FK 表示外键。连线上标注外键字段名，点选连线可以高亮同一约束的所有字段映射，点选表可打开字段详情。无外键的表也会显示在画布中。

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
| `src/api/database.js` | 管理 MySQL 连接、读取表结构和操作表数据 |
| `src/api/health.js` | 健康接口请求 |
| `vite.config.js` | 前端开发端口和接口代理 |

新增导航项时，在 `src/views/` 下创建独立的 `.vue` 文件，再将路径、标题和组件添加到 `MainView.vue` 的导航配置中。


## 制作柱状图

图库在「折线、柱状图与标记」分类中把柱状图放在第一张。已支持制作的图例显示彩色并提供制作入口。完成新的图表编辑器后，在 `src/data/chartExamples.js` 的 `chartEditorRoutes` 加入图例 ID 和对应编辑路由，其他图例以灰度显示。

从柱状图工作台点击「制作柱状图」，从已连接的数据库中选择数据表和字段。聚合方式支持记录数、合计、平均值、最大值、最小值和占比。除记录数外，都要选择数值字段。

例如在 `machine_hours` 按 `machine_id` 分类、选 `hours` 作为数值字段，最大值和最小值对应每台农机的最长和最短单次作业工时。占比显示每台农机总工时占全部农机总工时的百分比，即使预览只显示前 24 类也按全部分类计算。

切到「图表样式」，从带色板预览的下拉框选择预设色组，会按顺序应用到各柱。柱数超过色组颜色数时会循环使用。展开「逐柱调整」可单独改色和编辑图例名称。「统一配色」可同时为所有柱设置同一种颜色。配置修改后会自动刷新 PNG 预览，预览区可以下载图片。数据来源可每 5 秒检查一次，也可点击「刷新数据」。

展开「柱间距与纵轴刻度」后，可拖动滑块调整 X 轴柱间距和 Y 轴刻度密度。Y 轴目标格数越多，刻度越密。点击「恢复默认间距」可重新使用默认柱间距和自动刻度。

可自定义横轴名称、纵轴名称和图例位置。横轴名称留空时使用分类字段名。「边框与背景」可以添加绘图区边框或整张图的外框，设置颜色和粗细，开启柱形轮廓，并分别设置画布和绘图区背景或导出透明 PNG。

「网格与基线」可分别开关横向网格线、纵向网格线和零值基线，并选择网格线颜色与线型。「画布与导出」提供横版、方形、竖版和 130、200、300 DPI 的 PNG 设置。预览和下载使用相同配置。

预览下方可查看各分类的柱高，并添加误差棒和显著性标注。误差棒可以逐柱输入幅度。采用「平均值」聚合时，可以改用数据库按分类计算的样本标准差（SD）或标准误（SEM）。显著性标注从两根柱子中选一对，填已有检验的 p 值自动标星，或直接选 `*`、`**`、`***`、`ns`。可添加多组比较。

如果预览提示 5111 端口正在运行旧版 Flask 渲染服务，重新运行后端入口后刷新页面即可加载新样式参数。

数据选择、样式配置和预览分别由 `ChartDataPicker.vue`、`ChartAppearanceFields.vue`、`ChartPreview.vue` 提供。共享组件位于 `src/components/chart/`。

逐柱配色由 `ChartBarStyleFields.vue` 提供。数据库结果重新排序后，颜色和图例名称仍绑定原来的分类。`ChartPalettePicker.vue` 用于选择带预览的色组，`ChartColorPicker.vue` 用于选择单色，两者可用在其他图表编辑器。预设定义在 `src/data/chartPalettes.js`，其中七组期刊风格配色参考 [ggsci 配色文档](https://nanx.me/ggsci/reference/)。

## 制作饼图

从「饼图与极坐标图 → 饼图」工作台点击「制作饼图」。选择数据库、表、分类字段，再选择「记录数」或非负数值的「合计」。分类较多时，较小分类合并为「其他分类」，仍计入总量。

可选预设色组，并在预览下方逐个修改扇区颜色和查看占比。图表样式包含标题、标签、图例位置、突出扇区、起始角度、旋转方向、环形、描边、透明背景和导出 DPI。可手动刷新数据或每 5 秒自动更新，并下载 PNG。
