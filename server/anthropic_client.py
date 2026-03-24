"""Shared Anthropic HTTP client.

默认使用 API易（apiyi）Anthropic 兼容网关；可通过环境变量改回官方或其它中转。

- API易：``ANTHROPIC_BASE_URL=https://api.apiyi.com``（不要带 ``/v1`` 后缀）
- 官方：``ANTHROPIC_BASE_URL=https://api.anthropic.com`` 或置空（见 ``get_anthropic_client``）
- API易 模型 ID 与官方日期后缀不同，见 ``config.anthropic_model_*`` 默认值（如 ``claude-sonnet-4-6``）
"""

from __future__ import annotations

import json
import os
import threading

import anthropic

from server.config import settings

_anthropic_auth_token_env_lock = threading.Lock()


def upstream_http_status(exc: BaseException) -> int | None:
    """HTTP status from Anthropic / gateway (401 = bad key, 404 = bad model, etc.)."""
    code = getattr(exc, "status_code", None)
    if isinstance(code, int) and 100 <= code <= 599:
        return code
    return None


def auth_error_hint(status_code: int | None) -> str:
    """Short Chinese hint for common client errors (esp. 401 invalid token on API易)."""
    if status_code != 401:
        return ""
    base = (settings.anthropic_base_url or "").strip().lower()
    if "apiyi.com" in base:
        return (
            " 【如何解决】401 表示网关不认可当前密钥：请到 apiyi.com 控制台重新复制 **sk-** 开头的 API 密钥，"
            "写入 ANTHROPIC_API_KEY（不要用 Anthropic 官网 console 的 key）。"
            "确认 ANTHROPIC_BASE_URL=https://api.apiyi.com 且无多余空格。"
            "若 shell / IDE 里设置了 **ANTHROPIC_AUTH_TOKEN**，请删除（Anthropic SDK 会同时带 Bearer，"
            "部分网关会优先校验它导致 401）；改完后**重启**后端。"
        )
    return (
        " 【如何解决】401：请核对 ANTHROPIC_API_KEY 是否与 ANTHROPIC_BASE_URL 匹配"
        "（官方 key 仅用于 https://api.anthropic.com）。"
    )


def format_anthropic_error(exc: BaseException) -> str:
    """Readable message for logs / HTTP ``detail`` (helps debug 4xx/5xx from gateway)."""
    parts: list[str] = [str(exc)]
    code = getattr(exc, "status_code", None)
    if code is not None:
        parts.append(f"http_status={code}")
    body = getattr(exc, "body", None)
    if isinstance(body, str) and body.strip():
        parts.append(body.strip()[:4000])
    elif isinstance(body, dict):
        parts.append(json.dumps(body, ensure_ascii=False)[:4000])
    resp = getattr(exc, "response", None)
    if resp is not None:
        text = getattr(resp, "text", None)
        if text:
            parts.append(text[:4000])
    return " | ".join(p for p in parts if p)


def get_anthropic_client() -> anthropic.Anthropic:
    """Instantiate ``Anthropic`` with key + optional ``base_url``."""
    key = (settings.anthropic_api_key or "").strip()
    base = (settings.anthropic_base_url or "").strip()
    kwargs: dict = {"api_key": key}
    if base:
        kwargs["base_url"] = base
    # API易文档：anthropic-beta 置空，避免触发网关不支持的 beta 能力
    if "apiyi.com" in base.lower():
        kwargs["default_headers"] = {"anthropic-beta": ""}

    # SDK 在 auth_token=None 时仍会从 os.environ 读取 ANTHROPIC_AUTH_TOKEN。
    # 若与 X-Api-Key 并存，部分中转网关会优先校验 Bearer，导致 401（与 .env 里 key 是否正确无关）。
    with _anthropic_auth_token_env_lock:
        saved_bearer = os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        try:
            return anthropic.Anthropic(**kwargs)
        finally:
            if saved_bearer is not None:
                os.environ["ANTHROPIC_AUTH_TOKEN"] = saved_bearer
