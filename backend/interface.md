# Eye 后端接口

本机 Flask 地址为 `http://127.0.0.1:5111`。前端开发服务器通过 `/api` 代理访问 Flask。数据库接口仅接受本机请求。

[接口测试文档](test/database_connection.yaml)采用 OpenAPI 3.0 格式，可导入 Apifox 或 Postman。请在本地测试请求中填写实际连接参数。

后端在 INFO 级别记录请求时间、监听端口、HTTP 方法和接口路径。

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | [`/api/health`](#api-health) | 检查 Flask 服务 |
| GET | [`/api/database/connection`](#api-database-connection-read) | 读取当前连接配置 |
| GET | [`/api/database/connections`](#api-database-connections) | 列出导航可用的数据库连接 |
| DELETE | [`/api/database/connections/{connectionId}`](#api-database-connection-disconnect) | 断开并移除指定连接 |
| POST | [`/api/database/test-connection`](#api-database-connection-test) | 测试 MySQL 连接 |
| PUT | [`/api/database/connection`](#api-database-connection-save) | 保存并应用 MySQL 连接 |
| GET | [`/api/database/tables`](#api-database-tables) | 查询当前库的表名列表 |
| GET | [`/api/database/tables/detail?name=harvests`](#api-database-table-detail) | 查询指定表的结构和直接关系 |
| GET | [`/api/database/sources`](#api-database-views) | 列出可用于绘图的数据表和视图 |
| GET | [`/api/database/sources/detail`](#api-database-views) | 查询数据源的字段名称和类型 |
| POST | [`/api/database/views/preview`](#api-database-views) | 生成定义并预览可视化查询 |
| POST | [`/api/database/views/categories`](#api-database-views) | 读取转宽表可用的类别值 |
| POST | [`/api/database/views`](#api-database-views) | 确认后创建视图 |
| GET | [`/api/database/views/rows`](#api-database-views) | 预览已保存视图 |
| GET | [`/api/database/tables/rows`](#api-database-table-rows) | 分页读取表记录，支持按字段精确筛选 |
| POST | [`/api/database/tables/rows`](#api-database-table-rows) | 新增一条记录 |
| PATCH | [`/api/database/tables/rows`](#api-database-table-rows) | 按原始主键更新一条记录 |
| DELETE | [`/api/database/tables/rows`](#api-database-table-rows) | 按主键删除一条记录 |
| GET | [`/api/database/schema/diagram`](#api-database-schema-diagram) | 读取当前库的全库 ER 图数据 |
| POST | [`/api/database/charts/bar/data`](#api-bar-chart-data) | 查询柱状图聚合数据 |
| POST | [`/api/database/charts/bar/render`](#api-bar-chart-render) | 将图表数据和样式渲染为 PNG |
| POST | [`/api/database/charts/pie/data`](#api-pie-chart-data) | 查询饼图分类数值及总量 |
| POST | [`/api/database/charts/pie/render`](#api-pie-chart-render) | 渲染饼图或环形图 PNG |
| POST | [`/api/database/charts/radar/data`](#api-specialty-charts) | 查询雷达图指标 |
| POST | [`/api/database/charts/radar/render`](#api-specialty-charts) | 渲染雷达图 PNG |
| POST | [`/api/database/charts/sankey/data`](#api-specialty-charts) | 查询桑基图流量 |
| POST | [`/api/database/charts/sankey/render`](#api-specialty-charts) | 渲染桑基图 PNG |
| POST | [`/api/database/charts/{line,scatter,heatmap}/data`](#api-additional-charts) | 查询折线、散点或热力图数据 |
| POST | [`/api/database/charts/{line,scatter,heatmap}/render`](#api-additional-charts) | 渲染对应图表 PNG |
| POST | [`/api/database/charts/subplot/render`](#api-subplot-chart) | 读取并渲染多子图组合 |

<a name="api-health"></a>

## 健康检查

`GET /api/health`

成功时返回 HTTP 200 和 `{"data":{"status":"ok"}}`。

<a name="api-database-connections"></a>

## 列出数据库连接

`GET /api/database/connections`

返回 HTTP 200 和 `data.connections` 数组。每项提供 `id`、`database`、`host`、`port`、`username`。密码留在后端本地。此前成功保存的连接和当前通过本地配置设置的连接都可从列表打开。保存另一个数据库时，也会保留原先通过 `.env` 配好的当前连接。仅测试成功的连接不会加入记录。没有可用配置时，数组为空。

```json
{
  "data": {
    "connections": [
      {"id": "连接标识", "database": "agriculture", "host": "127.0.0.1", "port": 3306, "username": "eye_user"}
    ]
  }
}
```

读取本地连接文件失败时，返回 HTTP 500 和错误码 `DATABASE_CONNECTIONS_READ_FAILED`。

<a name="api-database-connection-disconnect"></a>

## 断开数据库连接

`DELETE /api/database/connections/{connectionId}`

路径参数使用[数据库连接列表](#api-database-connections)返回的 `id`。接口从本地移除这条连接记录。断开默认连接时，Flask 清空默认配置并释放连接池。重启后保持已断开状态，其他连接仍可通过各自的标识浏览。再次连接时使用「保存并连接」。

成功或指定连接已断开时返回 HTTP 200。

```json
{
  "data": {"status": "ok", "message": "数据库连接已断开。"}
}
```

| HTTP 状态 | `error.code` | 含义 |
| --- | --- | --- |
| 403 | `LOCAL_ACCESS_REQUIRED` | 请求来自本机以外的地址 |
| 500 | `DATABASE_SETTINGS_WRITE_FAILED` | 无法保存断开结果 |

<a name="api-database-connection-read"></a>

## 读取当前连接

`GET /api/database/connection`

成功时返回 HTTP 200 和当前使用的主机、端口、数据库名、用户名。密码始终省略。空配置中的数据库名和用户名为空字符串，无法解析的端口返回 `null`。接口返回的是后端的配置，连通性可通过测试接口确认。

```json
{
  "data": {
    "host": "127.0.0.1",
    "port": 3306,
    "database": "eye_demo",
    "username": "eye_user"
  }
}
```

## 测试与保存连接

<a name="api-database-connection-test"></a>

### 测试连接

`POST /api/database/test-connection`

使用本次提交的参数连接 MySQL 并执行 `SELECT 1`。完成后关闭测试连接。

<a name="api-database-connection-save"></a>

### 保存连接

`PUT /api/database/connection`

执行相同的连通性检查。验证通过后保存参数，更新 Flask 设置，并切换后续查询使用的数据库引擎。

### 共用请求和响应

两个接口均使用 `Content-Type: application/json`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `host` | 字符串 | 必填，MySQL 的 IP 或主机名 |
| `port` | 整数 | 必填，范围 1 至 65535，MySQL 通常使用 3306 |
| `database` | 字符串 | 必填，已有数据库的名称 |
| `username` | 字符串 | 必填，MySQL 用户名 |
| `password` | 字符串 | 可省略或传空字符串，表示空密码 |

```json
{
  "host": "127.0.0.1",
  "port": 3306,
  "database": "eye_demo",
  "username": "eye_user",
  "password": "本地填写"
}
```

成功时返回 HTTP 200，`data.status` 为 `ok`，`data.message` 为「数据库连接测试成功。」或「数据库连接已保存并生效。」。

保存成功时，Flask 将 MySQL 参数写入后端目录下的 `.env.database.json`。该文件也保存通过页面验证并保存的历史连接和凭据，已由 Git 忽略。主机、端口、库名和用户名相同的连接会更新原记录。服务重启时优先使用这份 MySQL 配置，其他设置仍从现有环境和 `.env` 加载。连接验证失败或写入失败时，继续使用此前的配置。

### 错误响应

| HTTP 状态 | `error.code` | 含义 |
| --- | --- | --- |
| 400 | `INVALID_DATABASE_SETTINGS` | JSON 格式或字段无效 |
| 403 | `LOCAL_ACCESS_REQUIRED` | 请求来自本机以外的地址 |
| 503 | `DATABASE_CONNECTION_FAILED` | MySQL 无法连接或拒绝访问 |
| 500 | `DATABASE_SETTINGS_WRITE_FAILED` | 后端无法保存设置，仅适用于保存接口 |

```json
{
  "error": {
    "code": "INVALID_DATABASE_SETTINGS",
    "message": "端口必须是 1 到 65535 之间的整数。"
  }
}
```

## 表与关系

这三个接口都接受可选查询参数 `connectionId`。传入[数据库连接列表](#api-database-connections)的 `id` 时，返回该连接账号可见的结构元数据，当前默认连接保持不变。省略该参数时，使用当前生效的 MySQL 连接。

<a name="api-database-tables"></a>

### 读取数据表

`GET /api/database/tables`

成功返回 HTTP 200。 `data.database` 是当前库名，`data.tables` 是按名称排列的基本表名称，空库返回空数组。

```json
{
  "data": {
    "database": "agriculture",
    "tables": ["harvests", "plots"]
  }
}
```

<a name="api-database-table-detail"></a>

### 读取表的字段和直接关系

`GET /api/database/tables/detail?name=harvests`

`name` 为必填查询参数，使用表列表返回的原始名称。客户端应对名称做 URL 编码。成功返回 HTTP 200。

```json
{
  "data": {
    "database": "agriculture",
    "table": "harvests",
    "columns": [
      {"name": "id", "type": "INT", "nullable": false, "default": null, "comment": null, "primaryKey": true, "foreignKey": false},
      {"name": "plot_id", "type": "INT", "nullable": false, "default": null, "comment": "地块", "primaryKey": false, "foreignKey": true}
    ],
    "relations": [
      {
        "name": "fk_harvest_plot",
        "source": {"schema": "agriculture", "table": "harvests"},
        "target": {"schema": "agriculture", "table": "plots"},
        "columns": [{"source": "plot_id", "target": "id"}]
      }
    ]
  }
}
```

- `columns` 按表中的列顺序排列。`type` 为 SQLAlchemy 读取的类型文本，`default` 为数据库默认值文本或 `null`，`comment` 为字段注释或 `null`。
- `relations` 包含从当前表发出与指向当前表的可见外键约束。`source` 是外键所在表，`target` 是被引用表。复合外键通过同一约束下的 `columns` 按定义顺序返回字段映射。自引用只返回一次。
- 账号的 MySQL 元数据访问范围决定跨库及同库关系的可见性。表详情可以查询当前数据库中的基本表。

<a name="api-database-schema-diagram"></a>

### 读取全库 ER 图数据

`GET /api/database/schema/diagram`

成功返回 HTTP 200。 `tables` 包含当前库可见的所有基本表及按定义顺序排列的字段。字段提供名称、MySQL 原始类型和主外键标记。`relations` 沿用[表详情](#api-database-table-detail)的约束格式，包含两个端点都可见的库内外键。没有外键的表也会返回。空库的两个数组均为空。

```json
{
  "data": {
    "database": "agriculture",
    "tables": [
      {"name": "harvests", "columns": [
        {"name": "id", "type": "int", "primaryKey": true, "foreignKey": false},
        {"name": "plot_id", "type": "int", "primaryKey": false, "foreignKey": true}
      ]},
      {"name": "plots", "columns": [
        {"name": "id", "type": "int", "primaryKey": true, "foreignKey": false}
      ]}
    ],
    "relations": [
      {
        "name": "fk_harvest_plot",
        "source": {"schema": "agriculture", "table": "harvests"},
        "target": {"schema": "agriculture", "table": "plots"},
        "columns": [{"source": "plot_id", "target": "id"}]
      }
    ]
  }
}
```

### 表结构接口错误响应

| HTTP 状态 | `error.code` | 含义 |
| --- | --- | --- |
| 400 | `TABLE_NAME_REQUIRED` | 表详情缺少表名 |
| 403 | `LOCAL_ACCESS_REQUIRED` | 请求来自本机以外的地址 |
| 404 | `TABLE_NOT_FOUND` | 所选数据库中没有该表 |
| 404 | `DATABASE_CONNECTION_NOT_FOUND` | 找不到指定的数据库连接 |
| 500 | `DATABASE_CONNECTIONS_READ_FAILED` | 无法读取本地连接记录 |
| 503 | `DATABASE_NOT_CONFIGURED` | 还未配置有效的 MySQL 连接参数 |
| 503 | `SCHEMA_READ_FAILED` | 数据库不可达或表结构无法读取 |

<a name="api-database-table-rows"></a>

## 数据表记录

四个方法均使用 `/api/database/tables/rows`。查询参数 `name` 使用表列表返回的原始表名。`connectionId` 使用数据库连接列表返回的标识，写入时必填，查询省略时使用当前默认连接。

### 分页查询

`GET /api/database/tables/rows?connectionId=连接标识&name=plantings&page=1&pageSize=20`

| 参数 | 说明 |
| --- | --- |
| `page` | 页码从 1 开始，默认 1。超过末页时返回实际最后一页 |
| `pageSize` | 默认 20，允许 1 至 100 |
| `filterColumn` | 可选，使用返回值中 `filterable` 为真的字段名 |
| `filterValue` | 使用 MySQL 等值比较，空字符串可作为筛选值 |
| `filterNull` | 传 `1` 查询 SQL NULL，与 `filterValue` 二选一 |

返回 HTTP 200。 `data.rows` 是以实际字段名为键的对象数组，`page`、`pageSize`、`total` 是实际页码、页大小和匹配的记录数。存在主键的表按主键顺序分页。`primaryKey` 列出主键字段，`canChangeRows` 表示能否通过主键编辑或删除单条记录。

`data.columns` 按定义顺序返回字段及类型，并提供 `kind`、`nullable`、`hasDefault`、`required`、`insertable`、`editable`、`filterable`、`options` 供页面生成表单。派生列由 MySQL 生成。二进制值使用十六进制字符串，JSON 列使用 JSON 文本字符串，`DECIMAL`、浮点和超出 JavaScript 安全整数范围的值返回字符串。SQL NULL 返回 JSON `null`，JSON 列中的 JSON null 返回字符串 `"null"`。

### 新增、编辑和删除

以下请求均使用 `Content-Type: application/json`，并传入查询参数 `connectionId` 和 `name`。

| 方法 | 请求体示例（以 `fields` 表为例） | 成功状态 |
| --- | --- | --- |
| POST | `{"values":{"name":"北区","hectares":"12.5","soil":"silt","tenure":"owned","first_sown_on":"2025-04-01","first_harvest_on":"2025-08-02"}}` | 201 |
| PATCH | `{"key":{"id":7},"values":{"hectares":"13.0"}}` | 200 |
| DELETE | `{"key":{"id":7}}` | 200 |

成功响应为 `{"data":{"status":"ok"}}`。新增时可省略自动增长字段、有默认值的字段和允许为 NULL 的字段。显式传 `null` 会写入 SQL NULL。编辑仅提交修改的字段，`key` 仍使用编辑前的完整主键值。使用复合主键时，`key` 需包含其中每一列。没有可用主键的表可以浏览、筛选，在账号有写权限时也可以新增记录。增删改使用所选连接的 MySQL 账号权限。

| HTTP 状态 | 错误码 | 含义 |
| --- | --- | --- |
| 400 | `INVALID_TABLE_ROWS` | 分页、筛选、主键或待写入字段无效 |
| 400 | `TABLE_NAME_REQUIRED` / `DATABASE_CONNECTION_REQUIRED` | 缺少表名或写操作的连接标识 |
| 403 | `TABLE_ROWS_ACCESS_DENIED` | 当前 MySQL 账号没有操作权限 |
| 404 | `TABLE_NOT_FOUND` / `TABLE_ROW_NOT_FOUND` | 表或记录已不存在 |
| 409 | `TABLE_ROW_KEY_REQUIRED` | 表没有可用于定位记录的主键 |
| 409 | `TABLE_ROW_DUPLICATE` / `TABLE_ROW_FOREIGN_KEY` | 唯一约束或外键约束阻止写入 |
| 409 | `TABLE_ROW_BUSY` | 记录正被其他操作锁定 |
| 413 | `TABLE_ROW_PAYLOAD_TOO_LARGE` | 写请求体超过 1 MiB |
| 503 | `TABLE_ROWS_UNAVAILABLE` | 无法执行操作，请检查数据库连接及表结构 |

<a name="api-bar-chart-data"></a>

## 查询柱状图数据

`POST /api/database/charts/bar/data`

后端的 `app/service/bar_chart.py` 负责取数和渲染，`bar_chart_annotations.py` 负责误差棒和显著性标注。各图表共用 `app/service/chart_support.py` 的数据库字段校验及 `app/util/chart.py` 的参数、字体和 PNG 工具。

连接列表返回的 `id` 对应 `connectionId`。请求提供表名、分类字段与聚合方式。`count` 可省略 `valueColumn`，其余方式均需要数值字段。

| `aggregation` | 方式 | 计算规则 |
| --- | --- | --- |
| `count` | 记录数 | 每个分类的记录条数 |
| `sum` | 合计 | 每个分类的数值总和 |
| `average` | 平均值 | 每个分类的数值平均值 |
| `max` | 最大值 | 每个分类中的最高值 |
| `min` | 最小值 | 每个分类中的最低值 |
| `share` | 占比 | 每个分类的数值总和 ÷ 所有分类的数值总和 × 100 |

```json
{
  "connectionId": "连接标识",
  "table": "machine_hours",
  "categoryColumn": "machine_id",
  "aggregation": "share",
  "valueColumn": "hours"
}
```

返回 `data.points`、`data.seriesName` 和 `data.truncated`。每个数据点形如 `{"label":"1","value":25}`。`share` 同时返回 `data.valueUnit: "%"`，此时示例数值 25 表示 25%。

`average` 的数据点另外提供 `sampleSize`（非空数值条数）、`sampleSd`（样本标准差）和 `sampleSem`（标准误，SD ÷ √n）。记录少于两条时 SD 和 SEM 返回 `null`。

分类为 SQL NULL 的行不参与统计。除记录数外，聚合会跳过数值为 SQL NULL 的行。按聚合值降序、分类字段升序返回前 24 个分类。超过 24 个分类时 `truncated` 为 `true`，占比的分母仍包含全部符合条件的分类。数值有正有负时按实际合计计算，可能出现负占比或超过 100% 的占比。有符合条件的记录且分母为 0 时返回 HTTP 400。没有符合条件的记录时返回空数组。分类名称超过 120 个字符时附带稳定的 `key`，用于保留该分类的样式。

<a name="api-bar-chart-render"></a>

## 渲染柱状图

`POST /api/database/charts/bar/render`

传入 1 至 24 个数据点和样式。成功返回 `image/png`。前端用响应体创建 Blob URL 用于预览和下载。修改样式时复用已有数据。切换字段或聚合方式时重新取数，定时检查发现聚合数据有变化时重新渲染。

```json
{
  "points": [
    {"label":"apple", "value":40}, {"label":"blueberry", "value":100},
    {"label":"cherry", "value":30}, {"label":"orange", "value":55}
  ],
  "style": {
    "barColors": ["tab:red", "tab:blue", "tab:red", "tab:orange"],
    "barLabels": ["red", "blue", "_red", "orange"],
    "title": "各类水果的供应量",
    "yLabel": "水果供应量",
    "legendTitle": "水果颜色",
    "showLegend": true,
    "showValues": true
  }
}
```

`barColors` 和 `barLabels` 按数据点顺序传递，长度应与 `points` 相同。逐柱图例会跳过空名称和以下划线开头的名称。统一配色可省略这两个数组，通过 `color` 设置柱形颜色，通过 `legendLabel` 设置系列名称。

将取数结果中的 `valueUnit: "%"` 传入 `style.valueUnit`，纵轴刻度和柱顶数值就会显示百分号。省略该字段时沿用普通数字格式。

`style.barSpacing` 是 X 轴柱中心距的倍率，允许 0.7 至 2，默认 1。`style.yTickBins` 是 Y 轴的目标刻度格数，允许 3 至 12 的整数。Matplotlib 会根据数据范围选用合适的刻度间隔。省略该字段或传 `null` 时使用自动刻度。

`style.xLabel` 和 `style.yLabel` 分别设置横轴和纵轴名称，最多 60 字符。`style.showGrid` 控制横向网格线。工作台默认传 `false`，直接调用渲染接口时省略可沿用接口默认的网格样式。

| 样式字段 | 取值与用途 |
| --- | --- |
| `frameMode` | `none` 无外框（默认）、`axes` 左轴与底轴、`plot` 绘图区四边、`canvas` 整张图外框 |
| `frameColor`、`frameWidth` | 外框颜色和粗细，默认 `#485b76`、1 磅 |
| `showBarOutline`、`barOutlineColor`、`barOutlineWidth` | 控制柱形轮廓，默认关闭、`#263c5a`、1 磅 |
| `figureColor`、`plotColor` | 画布与绘图区的背景颜色，默认均为白色 |
| `transparentBackground` | 为 `true` 时输出带透明背景的 PNG，默认关闭 |
| `showVerticalGrid`、`showZeroLine` | 纵向网格线和零值基线，默认分别为关闭、开启 |
| `gridColor`、`gridStyle` | 网格颜色和线型。线型可选 `solid`、`dashed`、`dotted`，默认 `#e4ebf4`、`solid` |
| `legendPosition` | `auto` 自动（默认）、`top-right` 右上角、`top-left` 左上角、`bottom` 图表下方 |
| `chartSize`、`dpi` | `wide` 横版 9:5（默认）、`square` 方形 1:1、`portrait` 竖版 3:4。DPI 可选 130（默认）、200、300 |

颜色使用 `#RRGGBB`，外框和柱形轮廓粗细范围均为 0.5 至 3 磅。

### 误差棒与显著性

`style.errorBars` 是与 `points` 等长的数组。每项为非负数或 `null`。数字表示相对于柱高上下相同的误差幅度，`null` 表示该柱不画误差棒。百分比图中的手动幅度以百分点计。

`style.significance` 最多接受 8 组比较。`left` 和 `right` 是 `points` 中两个不同柱子的零基索引。每组比较传入 `pValue` 或 `label`。标注格式为 `*`、`**`、`***` 或 `ns`。输入已有的 p 值时，依次使用 `p < 0.001`、`p < 0.01`、`p < 0.05` 对应的三个、两个、一个星号，其他结果显示 `ns`。

```json
{
  "errorBars": [0.5, null, 1.2],
  "significance": [
    {"left": 0, "right": 1, "pValue": 0.004},
    {"left": 0, "right": 2, "label": "*"}
  ]
}
```

PNG 响应带有 `X-Eye-Bar-Renderer: 4`。绘制显著性标注时，绘图区外的图例留出括号与星号所需的空间。

### 分组、堆叠与渐变

取数请求加 `groupColumn`（不同于 `categoryColumn`）可按两个分类维度统计合计、平均值、记录数、最大值、最小值或占比，返回 `points` 和 `series`。每个系列提供 `label`、`key` 和与横轴分类同序的 `values`，缺少的组合补零。最多 24 个横轴分类和 8 个系列。堆叠柱高是各段聚合值之和。渲染时将 `series` 与 `points` 一起传入，并设置 `style.layout` 为 `grouped` 或 `stacked`。可通过 `style.seriesColors` 逐系列配色。普通柱状图可开启 `style.gradient`，使用所选柱色生成渐变。误差棒和显著性标注适用于普通柱状图。

两个接口参数不合法时返回 HTTP 400 和 `INVALID_BAR_CHART`。常见格式与样式错误使用统一提示。字段选择错误、占比分母为零等需要不同处理的情况保留具体说明。超过 32 KiB 的请求返回 HTTP 413。取数接口沿用表结构接口的连接和数据表错误响应。

<a name="api-pie-chart-data"></a>

## 查询饼图数据

`POST /api/database/charts/pie/data`

```json
{
  "connectionId": "连接标识",
  "table": "harvest_loads",
  "categoryColumn": "planting_id",
  "aggregation": "sum",
  "valueColumn": "tonnes"
}
```

`aggregation` 可选 `sum`、`count`、`average`、`max` 或 `min`，记录数可省略 `valueColumn`。饼图以各分类聚合值的和作为分母，聚合值须非负，合计模式也要求原始数值非负。分类为 SQL NULL 的行跳过，数值聚合也跳过数值为 SQL NULL 的行。返回 `data.seriesName`、`total`、`combined` 及 `points`，每个点提供 `key`、`label` 和 `value`。聚合值为零的分类省略。超过 12 个正值分类时保留前 11 个，其余合并为「其他分类」。

<a name="api-pie-chart-render"></a>

## 渲染饼图

`POST /api/database/charts/pie/render`

`points` 接受 1 至 12 个扇区，每项有 `label` 和大于零的 `value`。成功返回 `image/png`。可选 `style` 字段如下。

| 字段 | 作用 |
| --- | --- |
| `title`、`legendTitle` | 图表标题和图例标题 |
| `legendPosition` | `right`、`bottom` 或 `none` |
| `labelMode` | `percent` 显示百分比、`value` 显示数值、`none` 隐藏 |
| `colors` | 依扇区顺序提供等长的 `#RRGGBB` 数组 |
| `startAngle`、`clockwise` | 起始角度 0 至 360 度和顺时针开关 |
| `highlight`、`donut` | 突出扇区的零基索引或 `null`、环形开关 |
| `showOutline`、`outlineColor` | 扇区描边开关和颜色 |
| `figureColor`、`transparentBackground`、`dpi` | 背景颜色、透明背景和导出 DPI（130、200、300） |

小于 3.5% 的扇区省略片内标签，工作台数据表仍可查看数值和占比。参数错误返回 HTTP 400 和 `INVALID_PIE_CHART`。请求体上限为 32 KiB。取数接口沿用表结构接口的连接和数据表错误响应。

<a name="api-database-views"></a>

## 视图与可视化数据源

`GET /api/database/sources?connectionId=...` 返回 `tables`、`views` 数组。`GET /api/database/sources/detail?connectionId=...&name=...` 返回 `columns`，每列有 `name`、`type`。各图表接口在原有 `table` 参数中也可以接收视图名称。

`POST /api/database/views/preview` 接收 `connectionId`、`spec` 和可选的 `drafts`。可视化步骤返回生成的 `query`、`columns`、`rows`（最多 20 行）、`truncated`。SQL 编辑仅返回待保存的查询定义，MySQL 在实际创建时校验。

| 构建方式 | `spec` 字段 |
| --- | --- |
| SQL | `mode: "sql"`，`sql` 是一条 SELECT 或 WITH 查询。 |
| 两表连接 | `mode: "join"`，`left`、`right` 指定来源，`joinType` 为 `inner` 或 `left`。`conditions` 为 `{left,right}` 字段对数组，按 AND 匹配；`columns` 为 `{side,name,alias}` 输出字段数组。 |
| 长表转宽表 | `mode: "pivot"`，`source` 指定来源，`row` 是行字段，`category` 是列类别字段，`metric` 是数值字段。`aggregation` 支持 `sum`、`average`、`max`、`min`、`count`，记录数可省略 `metric`。`columns` 为 `{value,alias}` 数组，最多 16 列。 |
| 筛选行 | `mode: "filter"`，`source` 指定来源，`match` 为 `all` 或 `any`，`conditions` 为 `{field,operator,value}` 数组。运算符支持 `eq`、`ne`、`gt`、`gte`、`lt`、`lte`、`contains`、`isNull`、`notNull`。空值判断可省略 `value`。 |
| 选择与重命名字段 | `mode: "project"`，`source` 指定来源，`columns` 是按输出顺序排列的 `{name,alias}` 数组。 |
| 计算新列 | `mode: "compute"`，`source`、`alias` 分别是来源和新列名。`inputMode: "fields"` 使用 `operands`（2 至 32 项），每项包含 `kind`（`field` 或 `number`）、`value`，第二项起还需 `operator`（`add`、`subtract`、`multiply`、`divide`）。`inputMode: "formula"` 使用 `expression`，支持数值字段、数字、括号和四则运算。 |
| 分箱 | `mode: "bin"`，提供 `source`、`field`、`alias` 和递增的 `boundaries`。分界值属于从该值开始的区间，空值仍为空。 |
| 宽表转长表 | `mode: "unpivot"`，提供 `source`、保留字段数组 `keys`，以及展开字段数组 `columns: [{name,alias}]`。`alias` 是生成的类别值，`categoryAlias` 与 `valueAlias` 指定新列名。 |
| 去重或保留最新 | `mode: "dedupe"`，`source` 与 `method: "distinct"` 可移除完全重复的行。使用 `method: "latest"` 时，还要传分组字段 `keys` 和排序字段 `order`，可选 `tie` 决定排序相同时保留哪条。 |
| 排名与累计 | `mode: "window"`，`scope: "group"` 先按 `keys` 分组，每组一行。`aggregation` 支持 `sum`、`average`、`count`、`min`、`max`，结果列名用 `summaryAlias`，除记录数外需提供 `metric`。 |

计算新列的旧协议仍接受 `left`、`right`（均为 `{kind,value}`）和 `operator`。公式中含空格或特殊字符的字段名用反引号包裹。

按组汇总可选 `operation: "summary"` 仅输出分组与汇总值，也可用 `rank`、`denseRank`、`runningSum`、`runningCount` 对汇总行继续计算。后四种方式使用 `alias` 指定计算结果列，使用 `direction` 指定方向。`order` 可用分组字段，留空时按汇总值排序。`partitionKeys` 可从分组字段中选择，用来分别计算。这里的 `runningCount` 累计的是汇总后的组数。

`scope: "detail"`（省略 `scope` 时的旧协议）保留明细行。`keys` 为窗口分区字段，可为空数组，`order` 为排序字段，`direction` 为 `asc` 或 `desc`，`alias` 为结果列名。累计合计需要 `metric`，累计可指定 `tie`。

来源使用 `db:名称` 指向数据库中的表或视图，使用 `draft:标识` 指向中间表。中间表定义通过 `drafts: [{id,spec}]` 随请求传入。工作台本地保留这些配置，最终创建时将依赖查询一并嵌入视图定义。

`POST /api/database/views/categories` 接收 `connectionId`、`source`、`column`、`drafts`，返回 `values`（最多 80 个）和 `truncated`。

`POST /api/database/views` 在预览参数基础上增加 `name` 和 `confirmed: true`。创建成功返回 HTTP 201 和视图名称、查询定义。同名时返回 HTTP 409。创建使用 `SQL SECURITY INVOKER`。

`GET /api/database/views/rows?connectionId=...&name=...` 返回已保存视图的 `columns`、`rows`（最多 20 行）和 `truncated`。

图表取数的 `aggregation: "raw"` 表示按记录读取数值列，适用于柱状、饼图、折线、雷达、桑基、热力图及组合子图。各图仍适用各自的预览上限。长表热力图每个行列组合、分组雷达图每个指标系列组合须各有至多一条可绘制记录；重复时接口返回 HTTP 400。

<a name="api-specialty-charts"></a>

## 雷达图与桑基图

| 图表 | 取数请求 | 渲染请求 |
| --- | --- | --- |
| 雷达图 | `POST /api/database/charts/radar/data`，以 `categoryColumn` 为指标，可用 `groupColumn` 比较多个系列 | 将 `points` 和可选 `series` 发至 `POST /api/database/charts/radar/render`。支持 `style.title`、`colors`、`fill` |
| 桑基图 | `POST /api/database/charts/sankey/data`，用 `categoryColumn` 作来源、`groupColumn` 作目标 | 将 `flows` 发至 `POST /api/database/charts/sankey/render`。支持 `style.title`、`colors`、`flowOpacity`、`showFlowValues` |

取数沿用数据库连接、表名和数值字段参数。工作台支持 `sum` 与 `count`。雷达图要求 3 至 12 个非负指标。桑基图每条 `flows` 记录包含 `source`、`target`、`value` 及可选的 `sourceKey`、`targetKey`，绘制最多 24 条双列流向。流带宽度与 `value` 成正比。`showFlowValues: true` 可在图上标注流量，标签密集时优先显示大流量。渲染结果为 PNG。

<a name="api-additional-charts"></a>

## 折线图、散点图与热力图

每种图使用 `POST /api/database/charts/{kind}/data` 和 `POST /api/database/charts/{kind}/render`。取数沿用 `connectionId`、`table`、`categoryColumn`、`valueColumn` 和可选的 `groupColumn`。渲染将取数结果和 `style` 一同提交。

| `kind` | 生成规则 |
| --- | --- |
| `line` | 横轴升序，数值与日期按实际间距绘制。可用第二字段分系列，缺失值会断线。最多 96 个横轴位置和 8 个系列。 |
| `scatter` | `categoryColumn` 可为数值、日期或类别，`valueColumn` 必须是数值，`groupColumn` 可选。每条原始记录是一个点，可用 `maxPoints` 设置预览点数（1 至 500），最多 8 组。 |
| `heatmap` | 长表模式用 `categoryColumn` 为行、`groupColumn` 为列，可按合计、记录数、平均值、最大值或最小值着色。宽表模式用 `layout: "wide"` 将 `valueColumns` 按选择顺序绘为列。缺失格显示灰色，最多 24 行、16 列。 |

散点图返回 `series` 和 `xType`。日期或类别横轴附带 `points`，供前端显示刻度文字。渲染样式支持 `markerShape`（`circle`、`square`、`triangle`、`diamond`、`cross`）、`markerSize`、`opacity`、`hollow`、`showGrid` 和 `showLegend`。数值横轴可用 `fit` 显示线性拟合及 R²、RMSE，用 `referenceLine` 显示 `y = x`。

热力图 PNG 的分辨率由渲染请求中的 `style.dpi` 控制，可选整数 130（默认）、200 或 300。

宽表取数示例。以 `year` 为行，读取 `Q1` 至 `Q4` 的原值。`rowMin`、`rowMax` 为可选的数值行范围，包含端点。行字段重复时可使用 `sum`、`average`、`min` 或 `max` 分别汇总每列。

```json
{
  "layout": "wide",
  "connectionId": "连接标识",
  "table": "UKgas",
  "categoryColumn": "year",
  "valueColumns": ["Q1", "Q2", "Q3", "Q4"],
  "aggregation": "raw",
  "rowMin": 1963,
  "rowMax": 1986
}
```

<a name="api-subplot-chart"></a>

## 多子图组合

`POST /api/database/charts/subplot/render` 接受 `panels` 与 `style`，返回 `image/png`。最多 6 个子图，`style.columns` 允许 1 至 3 列，另支持总标题、题注、图例与 DPI。`kind` 支持 `bar`、`line`、`bar_line`、`scatter` 与 `overlay`。

- `bar_line` 用 `selection.secondaryValueColumn` 指定折线数值字段，柱与线采用同一横轴和聚合口径。设 `rightAxis: true` 可让折线使用右纵轴。
- `scatter` 的取数协议和样式与独立散点图一致。单独子图通过 `primaryStyle` 设置散点样式，重合子图通过 `layers[].style` 设置。旧请求里的 `panel.fit` 仍可使用。
- `overlay` 使用 `layers`，包含两个带 `kind`（`bar`、`line` 或 `scatter`）和 `selection` 的子图配置。两组数据分别查询，横轴按同类型的类别、日期或数值对齐。`rightAxis: true` 将第二张子图分配给右纵轴。
- 重合子图中的 `bar` 和 `line` 可用 `selection.groupColumn` 分组，也可用 `selection.secondaryValueColumn` 为同一横轴选取第二个数值字段。多系列柱形按横轴值并排，两个数值字段共用聚合方式。
- `panel.title`、`xLabel`、`yLabel`、`rightLabel` 分别设置子图标题及轴名。`panel.style` 支持 `backgroundColor`、`grid`（`none`、`x`、`y`、`both`）、`frame`（`none`、`axes`、`box`）、`legend`（`inherit`、`none`、`auto`、`top-left`、`top-right`、`bottom`）、`tickRotation`（`null`、`0`、`25`、`45`）及左右纵轴范围 `yMin`、`yMax`、`rightYMin`、`rightYMax`。范围可传 `null` 以保留自动缩放。
- `layers[].style` 支持 `color`、`opacity`、`legendLabel`、`lineStyle`（`solid`、`dashed`、`dotted`）、`lineWidth`、`markers`、`lineMarker`（`circle`、`triangle`、`square`、`diamond`）、`lineMarkerSize` 和散点的 `markerSize`。可用 `layers[].secondSeriesStyle` 单独设置第二系列。其他图形使用 `panel.primaryStyle`，`bar_line` 的折线使用 `panel.secondaryStyle`。`panel.style.legendFrame` 控制图例边框。
