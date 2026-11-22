import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_SETTINGS_PATH = BACKEND_DIR / ".env.database.json"
DEFAULT_MYSQL_SETTINGS = {
    "MYSQL_HOST": "127.0.0.1",
    "MYSQL_PORT": "3306",
    "MYSQL_DATABASE": "",
    "MYSQL_USER": "",
    "MYSQL_PASSWORD": "",
}
DATABASE_SETTING_KEYS = tuple(DEFAULT_MYSQL_SETTINGS)


def load_settings() -> dict[str, str]:
    load_dotenv(BACKEND_DIR / ".env")
    settings = {
        "LOG_LEVEL": os.getenv("EYE_LOG_LEVEL", "INFO").upper(),
        **{key: os.getenv(key, default) for key, default in DEFAULT_MYSQL_SETTINGS.items()},
    }

    saved = _read_database_settings()
    if saved.get("active") is False:
        settings.update(DEFAULT_MYSQL_SETTINGS)
    elif saved:
        settings.update({key: saved[key] for key in DATABASE_SETTING_KEYS})
    return settings


def database_connection_id(settings) -> str:
    identity = (
        settings["MYSQL_HOST"].casefold(),
        int(settings["MYSQL_PORT"]),
        settings["MYSQL_DATABASE"],
        settings["MYSQL_USER"],
    )
    return sha256(json.dumps(identity).encode("utf-8")).hexdigest()


def load_database_connections() -> dict[str, dict[str, str]]:
    saved = _read_database_settings()
    connections = saved.get("connections", {})
    if saved and saved.get("active") is not False:
        active = {key: saved[key] for key in DATABASE_SETTING_KEYS}
        connections[database_connection_id(active)] = active
    return connections


def _read_database_settings() -> dict:
    try:
        with DATABASE_SETTINGS_PATH.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_database_settings(
    settings: dict[str, str], previous: dict[str, str] | None = None,
) -> None:
    connections = load_database_connections()
    if previous is not None:
        connections.setdefault(database_connection_id(previous), previous)
    connections[database_connection_id(settings)] = settings
    write_database_connections(settings, connections)


def write_database_connections(
    active: dict[str, str] | None, connections: dict[str, dict[str, str]],
) -> None:
    saved = {**(active if active is not None else {"active": False}), "connections": connections}
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
            json.dump(saved, file)
            file.flush()
            os.fsync(file.fileno())
        temporary_path.replace(DATABASE_SETTINGS_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)
