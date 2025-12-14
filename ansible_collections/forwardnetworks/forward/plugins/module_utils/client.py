from __future__ import annotations

import json
import base64
from urllib.parse import urlencode, urljoin

from ansible.module_utils.urls import fetch_url


class ForwardApiError(Exception):
    pass


def build_auth_header(token: str) -> str:
    return build_basic_auth_header(username=token, password="")


def build_basic_auth_header(username: str, password: str) -> str:
    # Forward OpenAPI indicates HTTP Basic auth.
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _join_url(base_url: str, path: str) -> str:
    if not base_url:
        raise ForwardApiError("base_url is required (or set FORWARD_BASE_URL)")
    if not path:
        raise ForwardApiError("path is required")
    base = base_url.rstrip("/") + "/"
    p = path.lstrip("/")
    return urljoin(base, p)


class ForwardClient:
    def __init__(
        self,
        module,
        base_url: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        validate_certs: bool = True,
        timeout: int = 30,
    ):
        self.module = module
        self.base_url = base_url
        self.token = token
        self.username = username
        self.password = password
        self.validate_certs = validate_certs
        self.timeout = timeout

        if not (self.token or self.username):
            raise ForwardApiError("token or username is required (set FORWARD_TOKEN or FWD_USER/FORWARD_USERNAME)")

    def request(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
        body=None,
        headers: dict | None = None,
        allow_status: set[int] | None = None,
    ):
        url = _join_url(self.base_url, path)
        if query_params:
            url = f"{url}?{urlencode(query_params, doseq=True)}"

        if self.token:
            auth_header = build_auth_header(self.token)
        else:
            auth_header = build_basic_auth_header(self.username, self.password or "")

        req_headers = {"Authorization": auth_header}
        if headers:
            req_headers.update(headers)

        data = None
        if body is not None and method.upper() not in {"GET", "HEAD"}:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                req_headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                data = body.encode("utf-8")
            elif isinstance(body, (bytes, bytearray)):
                data = body
            else:
                raise ForwardApiError(f"Unsupported body type: {type(body)}")

        resp, info = fetch_url(
            self.module,
            url,
            method=method.upper(),
            headers=req_headers,
            data=data,
            timeout=self.timeout,
        )

        status = info.get("status", 0)
        raw_bytes = b""
        if resp is not None:
            raw_bytes = resp.read()

        raw = raw_bytes.decode("utf-8", errors="replace")

        # Forward APIs often return JSON, but keep both raw+parsed.
        parsed = None
        content_type = (info.get("content_type") or "").lower()
        if raw and ("json" in content_type or raw.lstrip().startswith(("{", "["))):
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None

        allow_status = allow_status or set()

        if not (200 <= status < 300) and status not in allow_status:
            raise ForwardApiError(f"Forward API request failed: {status} {info.get('msg', '')} body={raw}")

        return {
            "url": url,
            "status_code": status,
            "json": parsed,
            "text": raw,
            "bytes": raw_bytes,
            "response_headers": {k: v for k, v in info.items() if isinstance(k, str)},
        }
