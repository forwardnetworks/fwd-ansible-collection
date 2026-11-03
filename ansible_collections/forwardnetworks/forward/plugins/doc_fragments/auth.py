# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Documentation fragment for Forward Networks connection options.
"""


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
requirements:
  - forward-sdk (Python package, Python 3.10 or newer) on the host that runs the module
options:
  base_url:
    description:
      - Base URL of the Forward Networks instance, for example C(https://fwd.app).
      - Falls back to the E(FORWARD_URL) environment variable (aliases E(FORWARD_BASE_URL) and E(FWD_HOST)).
    type: str
  username:
    description:
      - API token access key (or a login name).
      - Falls back to E(FORWARD_USERNAME) (alias E(FWD_USER)).
    type: str
  password:
    description:
      - API token secret (or a password).
      - Falls back to E(FORWARD_PASSWORD) (alias E(FWD_PASS)).
    type: str
  validate_certs:
    description:
      - Whether to validate TLS certificates.
      - When unset, falls back to E(FORWARD_VERIFY_TLS) (alias E(FORWARD_VALIDATE_CERTS)), then to C(true).
      - To verify against a private CA, set E(FORWARD_VERIFY_TLS) to the CA bundle path.
    type: bool
  timeout:
    description:
      - Read timeout in seconds.
      - Falls back to E(FORWARD_TIMEOUT), then to the SDK default (five minutes).
    type: float
notes:
  - Retries, rate limiting and the other transport settings are handled by C(forward-sdk) and configured with its E(FORWARD_RETRIES) and
    E(FORWARD_RATE_LIMIT_RPM) environment variables.
  - Run these modules on a host that has network access to Forward, usually C(localhost) with C(connection local), since they call the API rather
    than the managed devices.
"""
