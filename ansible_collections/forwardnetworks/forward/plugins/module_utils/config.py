from __future__ import annotations

import os


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_forward_config(params: dict) -> dict:
    base_url = (
        params.get("base_url")
        or os.environ.get("FORWARD_BASE_URL")
        or os.environ.get("FWD_HOST")
    )
    token = params.get("token") or os.environ.get("FORWARD_TOKEN")

    username = params.get("username") or os.environ.get("FORWARD_USERNAME") or os.environ.get("FWD_USER")
    password = params.get("password") or os.environ.get("FORWARD_PASSWORD") or os.environ.get("FWD_PASS")

    validate_certs = params.get("validate_certs")
    if validate_certs is None:
        validate_certs = _env_bool(os.environ.get("FORWARD_VALIDATE_CERTS"), True)

    timeout = params.get("timeout")
    if timeout is None:
        timeout = _env_int(os.environ.get("FORWARD_TIMEOUT"), 30)

    return {
        "base_url": base_url,
        "token": token,
        "username": username,
        "password": password,
        "validate_certs": validate_certs,
        "timeout": timeout,
    }
