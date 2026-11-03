#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_path_search
short_description: Trace a packet through a Forward Networks snapshot
description:
  - "Runs a single path search: where would traffic from a source to a destination go in this snapshot?"
  - Either O(from_device) or O(src_ip) is required.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  snapshot_id:
    description: Snapshot ID. Defaults to the network's latest processed snapshot.
    type: str
  from_device:
    description: Device (or device interface) the traffic starts from.
    type: str
  src_ip:
    description: Source IP address or subnet.
    type: str
  dst_ip:
    description: Destination IP address or subnet.
    type: str
    required: true
  intent:
    description: Which paths to prefer. C(PREFER_VIOLATIONS) finds drops, loops and blackholes; C(PREFER_DELIVERED) finds paths that deliver;
      C(VIOLATIONS_ONLY) returns only non-delivered paths.
    type: str
    choices: [PREFER_VIOLATIONS, PREFER_DELIVERED, VIOLATIONS_ONLY]
    default: PREFER_DELIVERED
  ip_proto:
    description: IP protocol number.
    type: int
  src_port:
    description: Source port or range.
    type: str
  dst_port:
    description: Destination port or range.
    type: str
  icmp_type:
    description: ICMP type.
    type: int
  fin:
    description: TCP FIN flag (0 or 1).
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
    description: Application ID.
    type: str
  user_id:
    description: User ID.
    type: str
  user_group_id:
    description: User group ID.
    type: str
  url:
    description: URL.
    type: str
  domain:
    description: Domain name.
    type: str
  include_tags:
    description: Include tags in the response.
    type: bool
    default: false
  include_network_functions:
    description: Include detailed forwarding info for each hop (slower).
    type: bool
    default: false
  max_candidates:
    description: Limit on results computed before ranking (1 to 10000).
    type: int
  max_results:
    description: Limit on results returned.
    type: int
  max_return_path_results:
    description: Limit on return path results.
    type: int
  max_seconds:
    description: Time limit for the search, in seconds.
    type: int
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Can the web tier reach the database?
  forwardnetworks.forward.fwd_path_search:
    network_id: "101"
    src_ip: 10.1.1.10
    dst_ip: 10.2.2.20
    ip_proto: 6
    dst_port: "5432"
    intent: PREFER_VIOLATIONS
  register: path
"""

RETURN = r"""
response:
  description: The full path search response.
  type: dict
  returned: success
paths:
  description: The paths found (the C(paths) key of RV(response)).
  type: list
  elements: dict
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

PASS_THROUGH = (
    "src_ip", "intent", "ip_proto", "src_port", "dst_port", "icmp_type", "fin", "syn", "rst", "psh", "ack", "urg",
    "app_id", "user_id", "user_group_id", "url", "domain", "max_candidates", "max_results", "max_return_path_results",
    "max_seconds",
)  # fmt: skip


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "network_id": {"type": "str"},
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
            "domain": {"type": "str"},
            "include_tags": {"type": "bool", "default": False},
            "include_network_functions": {"type": "bool", "default": False},
            "max_candidates": {"type": "int"},
            "max_results": {"type": "int"},
            "max_return_path_results": {"type": "int"},
            "max_seconds": {"type": "int"},
        },
        required_one_of=[("from_device", "src_ip")],
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    p = module.params
    kwargs = {name: p[name] for name in PASS_THROUGH if p.get(name) is not None}
    if p["include_tags"]:
        kwargs["include_tags"] = True
    if p["include_network_functions"]:
        kwargs["include_network_functions"] = True
    try:
        response = client.path_search.get_paths(
            dst_ip=p["dst_ip"],
            network_id=p["network_id"],
            snapshot_id=p["snapshot_id"],
            from_=p["from_device"],
            **kwargs
        )
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    response = sdk.to_plain(response)
    module.exit_json(changed=False, response=response, paths=response.get("paths"))


if __name__ == "__main__":
    main()
