# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Shared glue between Ansible and the ``forward-sdk`` Python package.

Every module and the inventory plugin build their client here, so connection
settings resolve the same way everywhere: task option, then ``FORWARD_*``
environment variable, then the legacy aliases this collection used before it was
built on the SDK.
"""
from __future__ import annotations

import os
import traceback

try:
    from forward_sdk import ForwardClient
    from forward_sdk.config import config_from_env
    from forward_sdk.errors import ForwardError

    HAS_SDK = True
    SDK_IMPORT_ERROR = None
except ImportError:  # pragma: no cover - exercised only without the SDK installed
    ForwardClient = None
    config_from_env = None
    ForwardError = Exception
    HAS_SDK = False
    SDK_IMPORT_ERROR = traceback.format_exc()

SDK_REQUIREMENT = "forward-sdk"
SDK_URL = "https://pypi.org/project/forward-sdk/"

# Environment variables the collection read before it used the SDK, mapped to the
# SDK's names. The SDK's own name wins when both are set.
LEGACY_ENV = {
    "FORWARD_BASE_URL": "FORWARD_URL",
    "FWD_HOST": "FORWARD_URL",
    "FWD_USER": "FORWARD_USERNAME",
    "FWD_PASS": "FORWARD_PASSWORD",
    "FORWARD_VALIDATE_CERTS": "FORWARD_VERIFY_TLS",
}


def resolved_environ(environ=None):
    """The environment with legacy variable names translated to the SDK's."""
    env = dict(os.environ if environ is None else environ)
    for legacy, current in LEGACY_ENV.items():
        if legacy in env and not env.get(current):
            env[current] = env[legacy]
    return env


def client_settings(params, environ=None):
    """Resolve SDK client settings from task parameters and the environment.

    Task parameters that are unset (``None``) fall through to the environment.
    """
    overrides = {}
    if params.get("base_url"):
        overrides["base_url"] = params["base_url"]
    if params.get("username"):
        overrides["username"] = params["username"]
    if params.get("password"):
        overrides["password"] = params["password"]
    if params.get("validate_certs") is not None:
        env_verify = resolved_environ(environ).get("FORWARD_VERIFY_TLS", "")
        private_ca = env_verify.lower() not in ("", "true", "false", "1", "0", "yes", "no", "on", "off")
        # validate_certs: true keeps a CA bundle path from FORWARD_VERIFY_TLS instead of replacing it with plain True.
        if not (params["validate_certs"] and private_ca):
            overrides["verify"] = bool(params["validate_certs"])
    if params.get("timeout") is not None:
        overrides["timeout"] = float(params["timeout"])
    if params.get("network_id"):
        overrides["network_id"] = params["network_id"]
    if params.get("snapshot_id"):
        overrides["snapshot_id"] = params["snapshot_id"]
    return config_from_env(environ=resolved_environ(environ), **overrides)


def build_client(params, environ=None):
    """Build a ``forward_sdk.ForwardClient``; raises ``ForwardError`` if misconfigured."""
    settings = client_settings(params, environ)
    base_url = settings.pop("base_url")
    return ForwardClient(base_url, **settings)


def require_sdk(module):
    """Fail the module with an install hint when ``forward-sdk`` is missing."""
    if not HAS_SDK:
        from ansible.module_utils.basic import missing_required_lib

        module.fail_json(msg=missing_required_lib(SDK_REQUIREMENT, url=SDK_URL), exception=SDK_IMPORT_ERROR)


def get_client(module):
    """Check for the SDK and build a client from ``module.params``, failing the module on error."""
    require_sdk(module)
    try:
        return build_client(module.params)
    except ForwardError as exc:
        module.fail_json(msg=str(exc))


def to_plain(value):
    """Convert SDK return values (pydantic models and friends) into JSON-safe data.

    Models are dumped with their API (camelCase) field names so results match
    what the Forward API itself returns.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {name: to_plain(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


def error_message(exc):
    """A one-line message for an SDK error, with the exception class for context."""
    return "%s: %s" % (type(exc).__name__, exc)
