import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_SETTINGS_PATH = BACKEND_DIR / ".env.database.json"


def load_settings() -> dict[str, str]:
    load_dotenv(BACKEND_DIR / ".env")
    settings = {
        "LOG_LEVEL": os.getenv("EYE_LOG_LEVEL", "INFO").upper(),
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", ""),
        "MYSQL_USER": os.getenv("MYSQL_USER", ""),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
    }

    try:
        with DATABASE_SETTINGS_PATH.open(encoding="utf-8") as file:
            saved = json.load(file)
    except FileNotFoundError:
        return settings

    for key in settings:
        if key.startswith("MYSQL_"):
            settings[key] = saved[key]
    return settings


def save_database_settings(settings: dict[str, str]) -> None:
    file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=DATABASE_SETTINGS_PATH.parent,
        prefix=".env.database.",
        delete=False,
    )
    temporary_path = Path(file.name)
    try:
        with file:
            json.dump(settings, file)
            file.flush()
            os.fsync(file.fileno())
        temporary_path.replace(DATABASE_SETTINGS_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)
