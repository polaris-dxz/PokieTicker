from pydantic_settings import BaseSettings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / ".data"


def _env_file() -> str:
    """Prefer .data/.env, fallback to project root .env."""
    for p in (DATA_DIR / ".env", PROJECT_ROOT / ".env"):
        if p.exists():
            return str(p)
    return str(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    polygon_api_key: str = ""
    anthropic_api_key: str = ""
    database_path: str = str(DATA_DIR / "pokieticker.db")
    models_dir: Path = DATA_DIR / "models"
    cache_dir: Path = DATA_DIR / "cache"

    model_config = {"env_file": _env_file(), "env_file_encoding": "utf-8"}


settings = Settings()
