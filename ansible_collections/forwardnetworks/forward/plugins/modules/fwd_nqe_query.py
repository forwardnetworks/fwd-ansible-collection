#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_nqe_query
short_description: Run a Forward Networks NQE query (scaffold)
description:
  - Runs a Network Query Engine (NQE) query via the Forward Networks API.
  - This is a scaffold; you may need to set C(path) to match your Forward API endpoint.
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
  path:
    description:
      - API path for running the query.
      - Defaults to C(/api/nqe) based on the included OpenAPI spec.
    type: str
    default: /api/nqe
  network_id:
    description: Forward network identifier.
    type: str
    required: true
  snapshot_id:
    description: Optional snapshot identifier.
    type: str
  query_id:
    description: NQE query identifier.
    type: str
    required: true
  parameters:
    description: Query parameters payload.
    type: dict
    default: {}
  options:
    description: Optional execution options (limit/offset/sort/etc).
    type: dict
    default: {}
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Run NQE query (endpoint is an example)
  forwardnetworks.forward.fwd_nqe_query:
    network_id: "123"
    query_id: "abcd"
    parameters:
      device_filter: "core-*"
  register: out
"""

RETURN = r"""
result:
  description: Response payload from the Forward API.
  type: raw
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
            "path": {"type": "str", "default": "/api/nqe"},
            "network_id": {"type": "str", "required": True},
            "snapshot_id": {"type": "str"},
            "query_id": {"type": "str", "required": True},
            "parameters": {"type": "dict", "default": {}},
            "options": {"type": "dict", "default": {}},
        },
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(changed=False, skipped=True, msg="check_mode: skipping query execution")

    path = module.params.get("path") or "/api/nqe"

    query_params = {"networkId": module.params["network_id"]}
    if module.params.get("snapshot_id"):
        query_params["snapshotId"] = module.params["snapshot_id"]

    payload = {"queryId": module.params["query_id"], "parameters": module.params["parameters"]}
    if module.params["options"]:
        payload["queryOptions"] = module.params["options"]

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
        out = client.request(method="POST", path=path, query_params=query_params, body=payload)
        module.exit_json(changed=False, result=out.get("json"), url=out.get("url"))
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
