# Eye

Eye 是数据库可视化项目的 Flask 后端。当前提供后端分层结构、健康检查接口以及 MySQL 连接测试，DAO 提供基础读取接口，Mapper 为后续数据映射预留。

## 后端结构

| 路径 | 职责 |
| --- | --- |
| `backend/wsgi.py` | Flask 应用入口 |
| `backend/app/controller/` | HTTP 路由与请求处理 |
| `backend/app/service/` | 应用业务逻辑 |
| `backend/app/entity/` | 业务实体 |
| `backend/app/dao/` | 数据读取和持久化 |
| `backend/app/mapper/` | 数据库查询与记录映射 |
| `backend/app/config/` | 环境配置与 MySQL 连接引擎 |
| `backend/app/util/` | 通用响应等工具 |
| `backend/test/` | 后端测试 |

## 启动

使用 Python 3.10 或更新版本。以下命令以 Python 3.12 为例，在项目根目录执行。

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python wsgi.py
```

服务监听 `0.0.0.0:5001`。在另一个终端执行 `curl http://127.0.0.1:5001/api/health`，预期 HTTP 200，返回 `{"data":{"status":"ok"}}`。

## 配置

- `backend/.env.example` 是随仓库提交的脱敏模板。
- `backend/.env` 是本机配置，由 Git 忽略。克隆后可执行 `cp backend/.env.example backend/.env` 创建。进程环境变量优先于此文件，`EYE_LOG_LEVEL` 默认为 `INFO`。

## MySQL 连接测试

在 `backend/.env` 填写 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER` 和 `MYSQL_PASSWORD`。主机默认是 `127.0.0.1`，端口默认是 `3306`。数据库需已存在，账号需有访问权限。密码中含有空格或 `#` 时，可用引号包住值。

在 `backend/` 下激活虚拟环境后执行。首次添加数据库支持后，先重新安装依赖。

```bash
python -m pip install -r requirements.txt
python -m unittest -v test.test_database
```

测试文件位于 `backend/test/test_database.py`。它直接连接配置的 MySQL 并执行 `SELECT 1`，无需启动 Flask 服务。成功时输出 `OK`，失败时输出简短提示并返回非零退出码。
