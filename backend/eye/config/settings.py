import os
from pathlib import Path

from dotenv import load_dotenv


def load_settings() -> dict[str, str]:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    return {"LOG_LEVEL": os.getenv("EYE_LOG_LEVEL", "INFO").upper()}
