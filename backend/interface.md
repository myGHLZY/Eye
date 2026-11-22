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
| GET | [`/api/database/tables/rows`](#api-database-table-rows) | 分页读取表记录，支持按字段精确筛选 |
| POST | [`/api/database/tables/rows`](#api-database-table-rows) | 新增一条记录 |
| PATCH | [`/api/database/tables/rows`](#api-database-table-rows) | 按原始主键更新一条记录 |
| DELETE | [`/api/database/tables/rows`](#api-database-table-rows) | 按主键删除一条记录 |
| GET | [`/api/database/schema/diagram`](#api-database-schema-diagram) | 读取当前库的全库 ER 图数据 |
| POST | [`/api/database/charts/bar/data`](#api-bar-chart-data) | 查询柱状图聚合数据 |
| POST | [`/api/database/charts/bar/render`](#api-bar-chart-render) | 将图表数据和样式渲染为 PNG |
| POST | [`/api/database/charts/pie/data`](#api-pie-chart-data) | 查询饼图分类数值及总量 |
| POST | [`/api/database/charts/pie/render`](#api-pie-chart-render) | 渲染饼图或环形图 PNG |

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

后端的 `app/service/bar_chart.py` 负责取数，`bar_chart_render.py` 负责渲染，`bar_chart_annotations.py` 负责误差棒和显著性标注。柱状图和饼图共用 `app/service/chart_support.py` 的数据库字段校验及 `app/util/chart.py` 的参数、字体和 PNG 工具。

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

PNG 响应带有 `X-Eye-Bar-Renderer: 3`。绘制显著性标注时，绘图区外的图例留出括号与星号所需的空间。

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

`aggregation` 可选 `sum` 或 `count`。合计需要非负数值字段，记录数可省略 `valueColumn`。分类为 SQL NULL 的行跳过，合计也跳过数值为 SQL NULL 的行。返回 `data.seriesName`、`total`、`combined` 及 `points`，每个点提供 `key`、`label` 和 `value`。聚合值为零的分类省略。超过 12 个正值分类时保留前 11 个，其余合并为「其他分类」，占比以完整总量计算。

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
