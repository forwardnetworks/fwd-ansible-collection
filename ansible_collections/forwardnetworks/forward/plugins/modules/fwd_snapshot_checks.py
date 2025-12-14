#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_checks
short_description: Retrieve Forward Networks snapshot checks
description:
  - Lists checks for a snapshot (C(GET /api/snapshots/{snapshotId}/checks)) or retrieves a specific check (C(/checks/{checkId})).
  - Useful for pre/post automation that wants to validate existing intent checks.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  snapshot_id:
    description: Snapshot identifier to inspect.
    type: str
    required: true
  check_id:
    description: Optional check identifier. When set, only that check is returned.
    type: str
  type:
    description:
      - Filter by check type(s), e.g., C(NQE), C(Predefined).
      - Matches the API C(type) parameter.
    type: list
    elements: str
    choices: [Isolation, Reachability, Existential, QueryStringBased, Predefined, NQE]
  priority:
    description: Filter checks by priority.
    type: list
    elements: str
    choices: [NOT_SET, LOW, MEDIUM, HIGH]
  status:
    description:
      - Filter checks by execution status.
      - Values NONE/PROCESSING are accepted but API never returns them.
    type: list
    elements: str
    choices: [NONE, PASS, FAIL, ERROR, TIMEOUT, PROCESSING]
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: List all checks for a snapshot
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "snap-123"

- name: Get only failed NQE checks
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "snap-123"
    type: ["NQE"]
    status: ["FAIL"]

- name: Get a specific check result
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "snap-123"
    check_id: "19939965"
  register: single_check
"""

RETURN = r"""
checks:
  description: List of check results (when C(check_id) is not provided).
  type: list
  elements: dict
  returned: when check_id is not provided
check:
  description: Single check result (when C(check_id) is provided).
  type: dict
  returned: when check_id is provided
url:
  description: Request URL that was executed.
  type: str
  returned: always
query_params:
  description: Query parameters sent to the API.
  type: dict
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
            "snapshot_id": {"type": "str", "required": True},
            "check_id": {"type": "str"},
            "type": {"type": "list", "elements": "str", "choices": ["Isolation", "Reachability", "Existential", "QueryStringBased", "Predefined", "NQE"]},
            "priority": {"type": "list", "elements": "str", "choices": ["NOT_SET", "LOW", "MEDIUM", "HIGH"]},
            "status": {"type": "list", "elements": "str", "choices": ["NONE", "PASS", "FAIL", "ERROR", "TIMEOUT", "PROCESSING"]},
        },
        supports_check_mode=True,
    )

    cfg = get_forward_config(module.params)
    client = ForwardClient(
        module,
        base_url=cfg["base_url"],
        token=cfg["token"],
        username=cfg["username"],
        password=cfg["password"],
        validate_certs=cfg["validate_certs"],
        timeout=cfg["timeout"],
    )

    snapshot_id = module.params["snapshot_id"]
    check_id = module.params.get("check_id")

    path = f"/api/snapshots/{snapshot_id}/checks"
    if check_id:
        path = f"{path}/{check_id}"

    query_params = {}
    for key in ("type", "priority", "status"):
        value = module.params.get(key)
        if value:
            query_params[key] = value

    try:
        response = client.request(method="GET", path=path, query_params=query_params)
    except ForwardApiError as exc:
        module.fail_json(msg=str(exc))

    payload = response.get("json")
    if check_id:
        module.exit_json(
            changed=False,
            check=payload,
            url=response.get("url"),
            query_params=query_params,
        )

    module.exit_json(
        changed=False,
        checks=payload or [],
        url=response.get("url"),
        query_params=query_params,
    )


if __name__ == "__main__":
    main()
