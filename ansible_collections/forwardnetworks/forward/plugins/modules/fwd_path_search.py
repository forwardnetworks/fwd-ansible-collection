#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_path_search
short_description: Run Forward Networks path searches (single query)
description:
  - Executes a single Forward Networks path search using GET /api/networks/{networkId}/paths.
  - Supports the majority of query parameters from the OpenAPI specification (intent, protocol headers, limits, snapshot, etc.).
  - Ideal for pre/post intent verification workflows (reachability, segmentation, validation of blocks).
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
      - Defaults to C(/api/networks/{network_id}/paths).
    type: str
    default: /api/networks/{network_id}/paths
  snapshot_id:
    description: Optional snapshot identifier (query param C(snapshotId)).
    type: str
  from_device:
    description:
      - Device name from which the traffic originates (maps to query param C(from)).
      - Either C(from_device) or C(src_ip) must be supplied.
    type: str
  src_ip:
    description: Source IP address or subnet (maps to query param C(srcIp)).
    type: str
  dst_ip:
    description: Destination IP address or subnet (maps to query param C(dstIp)).
    type: str
    required: true
  intent:
    description: Search intent preference.
    type: str
    choices: [PREFER_VIOLATIONS, PREFER_DELIVERED, VIOLATIONS_ONLY]
    default: PREFER_DELIVERED
  ip_proto:
    description: IP protocol number.
    type: int
  src_port:
    description: L4 source port or range (string, e.g., C(8080-8088)).
    type: str
  dst_port:
    description: L4 destination port or range.
    type: str
  icmp_type:
    description: ICMP type (implies IP protocol 1).
    type: int
  fin:
    description: TCP FIN flag (0 or 1, implies IP protocol 6).
    type: int
  syn:
    description: TCP SYN flag (0 or 1).
    type: int
  rst:
    description: TCP RST flag (0 or 1).
    type: int
  psh:
    description: TCP PSH flag (0 or 1).
    type: int
  ack:
    description: TCP ACK flag (0 or 1).
    type: int
  urg:
    description: TCP URG flag (0 or 1).
    type: int
  app_id:
    description: Layer-7 application identifier (maps to query param C(appId)).
    type: str
  user_id:
    description: Layer-7 user-id (maps to query param C(userId)).
    type: str
  user_group_id:
    description: Layer-7 user-group-id (maps to query param C(userGroupId)).
    type: str
  url:
    description: Layer-7 URL (maps directly to query param C(url)).
    type: str
  include_tags:
    description: Include device tags for each hop.
    type: bool
    default: false
  include_network_functions:
    description: Include detailed network function info for each hop.
    type: bool
    default: false
  max_candidates:
    description: Upper bound on computed candidates (1-10000, default 5000).
    type: int
  max_results:
    description: Upper bound on returned results (<= max_candidates, default 1).
    type: int
  max_return_path_results:
    description: Upper bound on return path results.
    type: int
  max_seconds:
    description: Timeout for the search (seconds, default 30).
    type: int
  extra_params:
    description: Additional query parameters (string key/value) for forward compatibility.
    type: dict
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Ensure DMZ server is reachable from edge router
  forwardnetworks.forward.fwd_path_search:
    network_id: "{{ lookup('env', 'FWD_NETWORKID') }}"
    from_device: edge-router-1
    dst_ip: 10.0.50.10
    intent: PREFER_DELIVERED
  register: path

- name: Validate that traffic is blocked (violations only)
  forwardnetworks.forward.fwd_path_search:
    network_id: "{{ lookup('env', 'FWD_NETWORKID') }}"
    src_ip: 10.10.10.0/24
    dst_ip: 192.0.2.10
    intent: VIOLATIONS_ONLY
  register: block_check

- name: Path search using explicit snapshot and protocol headers
  forwardnetworks.forward.fwd_path_search:
    network_id: "205507"
    snapshot_id: "snap-123"
    from_device: app-fw-1
    dst_ip: 203.0.113.5
    ip_proto: 6
    dst_port: "443"
    include_network_functions: true
  register: https_path
"""

RETURN = r"""
paths:
  description: List of path objects returned by the API (`response["paths"]` when present).
  type: list
  returned: when supported
response:
  description: Full JSON payload returned by the API.
  type: dict
  returned: always
url:
  description: Final request URL (including rendered query parameters).
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
from ansible_collections.forwardnetworks.forward.plugins.module_utils.path_search import build_path_query


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
            "path": {"type": "str", "default": "/api/networks/{network_id}/paths"},
            "snapshot_id": {"type": "str"},
            "from_device": {"type": "str"},
            "src_ip": {"type": "str"},
            "dst_ip": {"type": "str", "required": True},
            "intent": {
                "type": "str",
                "choices": ["PREFER_VIOLATIONS", "PREFER_DELIVERED", "VIOLATIONS_ONLY"],
                "default": "PREFER_DELIVERED",
            },
            "ip_proto": {"type": "int"},
            "src_port": {"type": "str"},
            "dst_port": {"type": "str"},
            "icmp_type": {"type": "int"},
            "fin": {"type": "int"},
            "syn": {"type": "int"},
            "rst": {"type": "int"},
            "psh": {"type": "int"},
            "ack": {"type": "int"},
            "urg": {"type": "int"},
            "app_id": {"type": "str"},
            "user_id": {"type": "str"},
            "user_group_id": {"type": "str"},
            "url": {"type": "str"},
            "include_tags": {"type": "bool", "default": False},
            "include_network_functions": {"type": "bool", "default": False},
            "max_candidates": {"type": "int"},
            "max_results": {"type": "int"},
            "max_return_path_results": {"type": "int"},
            "max_seconds": {"type": "int"},
            "extra_params": {"type": "dict"},
        },
        supports_check_mode=True,
    )

    if not module.params.get("from_device") and not module.params.get("src_ip"):
        module.fail_json(msg="Either from_device or src_ip must be provided for path search")

    query = build_path_query(module.params)
    path_template = module.params.get("path") or "/api/networks/{network_id}/paths"
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
        out = client.request(method="GET", path=path, query_params=query)
        payload = out.get("json") or {}
        module.exit_json(
            changed=False,
            response=payload,
            paths=payload.get("paths"),
            url=out.get("url"),
            query_params=query,
        )
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
