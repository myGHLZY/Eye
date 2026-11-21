# Eye

Eye 是数据库可视化项目的 Flask 后端。当前提供后端分层结构与健康检查接口，DAO 提供基础读取接口，Mapper 为后续数据映射预留。

## 后端结构

| 路径 | 职责 |
| --- | --- |
| `backend/wsgi.py` | Flask 应用入口 |
| `backend/eye/controller/` | HTTP 路由与请求处理 |
| `backend/eye/service/` | 应用业务逻辑 |
| `backend/eye/entity/` | 业务实体 |
| `backend/eye/dao/` | 数据读取和持久化 |
| `backend/eye/mapper/` | 数据库查询与记录映射 |
| `backend/eye/config/` | 环境配置加载 |
| `backend/eye/util/` | 通用响应等工具 |

## 启动

使用 Python 3.10 或更新版本。以下命令以 Python 3.12 为例，在项目根目录执行。

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app wsgi run --host 127.0.0.1 --port 5000
```

在另一个终端执行 `curl http://127.0.0.1:5000/api/health`，预期 HTTP 200，返回 `{"data":{"status":"ok"}}`。

## 配置

- `backend/.env.example` 是随仓库提交的脱敏模板。
- `backend/.env` 是本机配置，由 Git 忽略。克隆后可执行 `cp backend/.env.example backend/.env` 创建。进程环境变量优先于此文件，`EYE_LOG_LEVEL` 默认为 `INFO`。
