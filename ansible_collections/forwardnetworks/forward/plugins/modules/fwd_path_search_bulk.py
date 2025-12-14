#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_path_search_bulk
short_description: Run multiple Forward Networks path searches in one request
description:
  - Executes C(/api/networks/{networkId}/paths-bulk) with a list of query definitions.
  - Each query supports the same fields as M(forwardnetworks.forward.fwd_path_search) (from device/src IP, headers, intent, etc.).
  - Useful for pre/post intent testing where several flows should succeed/fail atomically.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network identifier.
    type: str
    required: true
  path:
    description:
      - API path template.
      - Defaults to C(/api/networks/{network_id}/paths-bulk).
    type: str
    default: /api/networks/{network_id}/paths-bulk
  snapshot_id:
    description: Optional snapshot identifier (applies to all queries).
    type: str
  queries:
    description:
      - List of query definitions. Each dict accepts the same keys as M(forwardnetworks.forward.fwd_path_search).
      - 'Required keys per entry: C(dst_ip), plus C(from_device) or C(src_ip).'
    type: list
    elements: dict
    required: true
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Evaluate multiple flows
  forwardnetworks.forward.fwd_path_search_bulk:
    network_id: "{{ lookup('env', 'FWD_NETWORKID') }}"
    queries:
      - name: "Edge to DMZ web"
        from_device: edge-router-1
        dst_ip: 10.0.50.10
        intent: PREFER_DELIVERED
      - name: "App server blocked from DB"
        src_ip: 10.20.40.0/24
        dst_ip: 172.16.5.10
        intent: VIOLATIONS_ONLY
  register: bulk_paths

- name: Assert DMZ path exists
  ansible.builtin.assert:
    that:
      - (bulk_paths.results[0].paths | length) > 0
"""

RETURN = r"""
results:
  description: List with one entry per query. Each entry is either a C(PathSearchResponse) dict or an error dict.
  type: list
  returned: always
url:
  description: Final request URL (query params include network/snapshot).
  type: str
  returned: always
query_params:
  description: Query parameters sent alongside the POST request (currently only snapshotId when set).
  type: dict
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config
from ansible_collections.forwardnetworks.forward.plugins.module_utils.path_search import build_path_query


REQUIRED_PER_QUERY = ("dst_ip",)


def validate_query(module: AnsibleModule, query: dict, index: int):
    if not query:
        module.fail_json(msg=f"Query at index {index} is empty", query_index=index)
    if not (query.get("from_device") or query.get("src_ip")):
        module.fail_json(msg="Each query needs from_device or src_ip", query_index=index)
    for key in REQUIRED_PER_QUERY:
        if not query.get(key):
            module.fail_json(msg=f"Query at index {index} missing required field: {key}", query_index=index)


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "token": {"type": "str", "no_log": True},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool", "default": True},
            "timeout": {"type": "int", "default": 30},
            "network_id": {"type": "str", "required": True},
            "path": {"type": "str", "default": "/api/networks/{network_id}/paths-bulk"},
            "snapshot_id": {"type": "str"},
            "queries": {"type": "list", "elements": "dict", "required": True},
        },
        supports_check_mode=True,
    )

    queries = module.params["queries"] or []
    if not queries:
        module.fail_json(msg="At least one query must be provided")

    built_queries = []
    for idx, query in enumerate(queries):
        validate_query(module, query, idx)
        built_queries.append(build_path_query(query, include_snapshot=False))

    query_params = {}
    if module.params.get("snapshot_id"):
        query_params["snapshotId"] = module.params["snapshot_id"]

    path_template = module.params.get("path") or "/api/networks/{network_id}/paths-bulk"
    path = path_template.format(network_id=module.params["network_id"], networkId=module.params["network_id"])

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
        out = client.request(method="POST", path=path, query_params=query_params, body=built_queries)
        module.exit_json(changed=False, results=out.get("json"), url=out.get("url"), query_params=query_params)
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
