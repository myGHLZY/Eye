import sys
import unittest
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy.exc import DBAPIError, SQLAlchemyError

# PyCharm can run this file as a top-level module from the test directory.
backend_dir = str(Path(__file__).resolve().parents[1])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.database.database import DatabaseConfigurationError, get_database_engine


MYSQL_ERROR_MESSAGES = {
    1044: "账号没有访问所配置数据库的权限。",
    1045: "MySQL 拒绝登录。请检查账号、密码和账号允许的连接来源。",
    1049: "所配置的数据库不存在。请检查 MYSQL_DATABASE。",
    1142: "账号没有查询 conversations 表的权限。",
    1146: "当前数据库中没有 conversations 表。请检查 MYSQL_DATABASE。",
    2002: "无法连接 MySQL。请检查服务状态和连接地址。",
    2003: "无法连接 MySQL。请检查服务状态、主机和端口。",
    2005: "无法解析 MySQL 主机名。请检查 MYSQL_HOST。",
}
DEFAULT_ERROR_MESSAGE = "MySQL 连接测试失败。请检查本机配置。"


class DatabaseConnectionTest(unittest.TestCase):
    @contextmanager
    def _connection(self):
        app = create_app()
        try:
            with app.app_context():
                engine = get_database_engine()
                self.addCleanup(engine.dispose)
                with engine.connect() as connection:
                    yield connection
        except DatabaseConfigurationError as error:
            raise self.failureException(str(error)) from None
        except DBAPIError as error:
            code = next(iter(error.orig.args), None)
            raise self.failureException(
                MYSQL_ERROR_MESSAGES.get(code, DEFAULT_ERROR_MESSAGE)
            ) from None
        except SQLAlchemyError:
            raise self.failureException(DEFAULT_ERROR_MESSAGE) from None

    def test_mysql_connection(self):
        with self._connection() as connection:
            self.assertEqual(connection.exec_driver_sql("SELECT 1").scalar_one(), 1)

    def test_select_conversations(self):
        with self._connection() as connection:
            streaming_connection = connection.execution_options(stream_results=True)
            with streaming_connection.exec_driver_sql("SELECT * FROM conversations") as result:
                self.assertTrue(result.returns_rows)
                print("\nSELECT * FROM conversations")
                row_count = 0
                for row_count, row in enumerate(result.mappings(), start=1):
                    print(dict(row))
                print(f"共 {row_count} 行")
