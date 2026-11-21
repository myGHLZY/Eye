# Eye 后端接口

本机 Flask 地址为 `http://127.0.0.1:5111`。前端开发服务器通过 `/api` 代理访问 Flask。数据库接口仅接受本机请求。

[接口测试文档](test/database_connection.yaml)采用 OpenAPI 3.0 格式，可导入 Apifox 或 Postman。请在本地测试请求中填写实际连接参数。

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | [`/api/health`](#api-health) | 检查 Flask 服务 |
| GET | [`/api/database/connection`](#api-database-connection-read) | 读取当前连接配置 |
| POST | [`/api/database/test-connection`](#api-database-connection-test) | 测试 MySQL 连接 |
| PUT | [`/api/database/connection`](#api-database-connection-save) | 保存并应用 MySQL 连接 |
| GET | [`/api/database/tables`](#api-database-tables) | 查询当前库的表名列表 |
| GET | [`/api/database/tables/detail?name=harvests`](#api-database-table-detail) | 查询指定表的结构和直接关系 |
| GET | [`/api/database/schema/diagram`](#api-database-schema-diagram) | 读取当前库的全库 ER 图数据 |

<a name="api-health"></a>

## 健康检查

`GET /api/health`

成功时返回 HTTP 200 和 `{"data":{"status":"ok"}}`。

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

保存成功时，Flask 将 MySQL 参数写入后端目录下的 `.env.database.json`。该文件包含连接凭据，已由 Git 忽略。服务重启时优先使用这份 MySQL 配置，其他设置仍从现有环境和 `.env` 加载。连接验证失败或写入失败时，继续使用此前的配置。

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

以下接口使用当前生效的 MySQL 连接，返回当前账号可见的结构元数据。连接切换后，下一次请求会读取新库。

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
| 404 | `TABLE_NOT_FOUND` | 当前数据库中没有该表 |
| 503 | `DATABASE_NOT_CONFIGURED` | 还未配置有效的 MySQL 连接参数 |
| 503 | `SCHEMA_READ_FAILED` | 数据库不可达或表结构无法读取 |
