#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_api
short_description: Call the Forward Networks API (generic wrapper)
description:
  - Generic REST wrapper for calling Forward Networks APIs.
  - Intended as a building block for higher-level modules.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  username:
    description:
      - Forward username (HTTP Basic).
      - Can also be set via C(FWD_USER) or C(FORWARD_USERNAME).
      - If C(token) is set, token auth is used instead.
    type: str
  password:
    description:
      - Forward password (HTTP Basic).
      - Can also be set via C(FWD_PASS) or C(FORWARD_PASSWORD).
    type: str
  method:
    description: HTTP method.
    type: str
    choices: [GET, POST, PUT, PATCH, DELETE]
    default: GET
  path:
    description:
      - API path (no hostname), e.g. C(/api/v2/...).
    type: str
    required: true
  query_params:
    description: Query parameters.
    type: dict
    default: {}
  body:
    description:
      - Request body for non-GET methods.
      - If a dict/list, it is JSON-encoded.
    type: raw
  headers:
    description: Extra HTTP headers.
    type: dict
    default: {}
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: List something (example)
  forwardnetworks.forward.fwd_api:
    method: GET
    path: /api/example
  register: out
"""

RETURN = r"""
status_code:
  description: HTTP status code.
  type: int
  returned: always
json:
  description: Parsed JSON response (when possible).
  returned: when supported
  type: raw
text:
  description: Raw response body.
  type: str
  returned: always
response_headers:
  description: Response metadata from Ansible fetch_url.
  type: dict
  returned: always
url:
  description: Full request URL.
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "token": {"type": "str", "no_log": True},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool", "default": True},
            "timeout": {"type": "int", "default": 30},
            "method": {"type": "str", "choices": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
            "path": {"type": "str", "required": True},
            "query_params": {"type": "dict", "default": {}},
            "body": {"type": "raw"},
            "headers": {"type": "dict", "default": {}},
        },
        supports_check_mode=True,
    )

    method = module.params["method"].upper()
    if module.check_mode and method != "GET":
        module.exit_json(changed=False, skipped=True, msg="check_mode: skipping non-GET request")

    cfg = get_forward_config(module.params)
    try:
        client = ForwardClient(
            module,
            base_url=cfg["base_url"],
            token=cfg["token"],
            username=cfg["username"],
            password=cfg["password"],
            validate_certs=cfg["validate_certs"],
            timeout=cfg["timeout"],
        )
        out = client.request(
            method=method,
            path=module.params["path"],
            query_params=module.params["query_params"],
            body=module.params["body"],
            headers=module.params["headers"],
        )
        module.exit_json(changed=False, **out)
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
