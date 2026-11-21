import os
from pathlib import Path

from dotenv import load_dotenv


def load_settings() -> dict[str, str]:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    return {
        "LOG_LEVEL": os.getenv("EYE_LOG_LEVEL", "INFO").upper(),
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", ""),
        "MYSQL_USER": os.getenv("MYSQL_USER", ""),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
    }
