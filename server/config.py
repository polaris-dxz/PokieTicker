import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / ".data"

_ENV_PATH_POINTER = ".env.path"


def _parse_env_path_pointer(pointer_file: Path, anchor: Path) -> Path | None:
    """Read first non-comment line from ``.env.path``; relative paths are relative to ``anchor``."""
    try:
        text = pointer_file.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line).expanduser()
        if not p.is_absolute():
            p = (anchor / p).resolve()
        else:
            p = p.resolve()
        return p
    return None


def resolved_env_file_path() -> Path:
    """实际参与加载的 ``.env`` 路径（供日志与 pydantic 共用）。

    解析顺序：

    1. 仓库根目录下的 ``.env.path``（与 ``server/`` 同级）：**仅一行**为要使用的 ``.env`` 的绝对路径，
       或相对路径（相对**该仓库根**）。无需在终端 ``export``。
       若存在符号链接双副本，会先试**逻辑根目录**（``Path(__file__).parent.parent``）下的
       ``.env.path``，再试 resolve 后的 ``PROJECT_ROOT`` 下的同名文件（同一 inode 则只读一次）。
    2. 环境变量 ``POKIETICKER_ENV_FILE``（可选，CI/脚本用）。
    3. 若未通过 1/2 指定文件：则默认使用逻辑根目录下的 ``.env``，否则 ``PROJECT_ROOT/.env``。

    **注意**：pydantic-settings 中 **操作系统环境变量优先于 .env 文件**。
    若 shell / IDE 里已有 ``ANTHROPIC_API_KEY``，会覆盖 ``.env`` 里的值。
    """
    logical_root = Path(__file__).parent.parent
    for root in (logical_root, PROJECT_ROOT):
        ptr = root / _ENV_PATH_POINTER
        if ptr.is_file():
            chosen = _parse_env_path_pointer(ptr, anchor=root)
            if chosen is not None:
                return chosen

    override = (os.environ.get("POKIETICKER_ENV_FILE") or "").strip()
    if override:
        return Path(override)

    logical_env = logical_root / ".env"
    canonical_env = PROJECT_ROOT / ".env"
    if logical_env.is_file():
        return logical_env
    if canonical_env.is_file():
        return canonical_env
    return logical_env


def _env_files() -> tuple[str, ...]:
    """仅从单一文件加载（不读 ``.data/.env``）；路径由 ``resolved_env_file_path()`` 决定。"""
    return (str(resolved_env_file_path()),)


class Settings(BaseSettings):
    polygon_api_key: str = ""
    anthropic_api_key: str = ""
    # API易 Anthropic 网关根地址，勿带 /v1；置空则走 SDK 默认（官方 api.anthropic.com）
    anthropic_base_url: str = "https://api.apiyi.com"
    # Layer 2 / story / range — API易 文档模型 id 为 claude-sonnet-4-6；官方可用 ANTHROPIC_BASE_URL 指向 console 并改此值
    anthropic_model_sonnet: str = "claude-sonnet-4-6"
    database_path: str = str(DATA_DIR / "pokieticker.db")
    models_dir: Path = DATA_DIR / "models"
    cache_dir: Path = DATA_DIR / "cache"

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
    )


settings = Settings()
