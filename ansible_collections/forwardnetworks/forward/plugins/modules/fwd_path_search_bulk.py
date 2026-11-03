#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_path_search_bulk
short_description: Run several Forward Networks path searches in one request
description:
  - Runs a list of path searches against one snapshot in a single call.
  - Useful for pre and post change checks where a set of flows should all be delivered or all be blocked.
  - The settings O(intent), O(include_tags), O(include_network_functions), O(max_candidates), O(max_results), O(max_return_path_results) and
    O(max_seconds) apply to every query.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  snapshot_id:
    description: Snapshot ID. Defaults to the network's latest processed snapshot.
    type: str
  queries:
    description:
      - List of queries. Each entry needs C(dst_ip) and either C(from_device) or C(src_ip).
      - Other keys per entry are C(ip_proto), C(src_port), C(dst_port), C(icmp_type), C(fin), C(syn), C(rst), C(psh), C(ack), C(urg), C(app_id),
        C(user_id), C(user_group_id) and C(url).
      - A C(name) key is allowed as a label and is not sent to Forward.
    type: list
    elements: dict
    required: true
  intent:
    description: Which paths to prefer, for all queries.
    type: str
    choices: [PREFER_VIOLATIONS, PREFER_DELIVERED, VIOLATIONS_ONLY]
  include_tags:
    description: Include tags in the responses.
    type: bool
  include_network_functions:
    description: Include detailed forwarding info for each hop (slower).
    type: bool
  max_candidates:
    description: Limit on results computed per query before ranking.
    type: int
  max_results:
    description: Limit on results returned per query.
    type: int
  max_return_path_results:
    description: Limit on return path results per query.
    type: int
  max_seconds:
    description: Time limit for the whole request, in seconds.
    type: int
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Check the critical flows
  forwardnetworks.forward.fwd_path_search_bulk:
    network_id: "101"
    intent: PREFER_VIOLATIONS
    queries:
      - {src_ip: 10.1.1.10, dst_ip: 10.2.2.20, ip_proto: 6, dst_port: "443"}
      - {from_device: edge1, dst_ip: 8.8.8.8}
  register: flows
"""

RETURN = r"""
results:
  description: One path search response per query, in order.
  type: list
  elements: dict
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk
from ansible_collections.forwardnetworks.forward.plugins.module_utils.path_search import (
    SHARED_FIELDS,
    build_bulk_body,
    validate_query,
)


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
            "queries": {"type": "list", "elements": "dict", "required": True},
            "intent": {"type": "str", "choices": ["PREFER_VIOLATIONS", "PREFER_DELIVERED", "VIOLATIONS_ONLY"]},
            "include_tags": {"type": "bool"},
            "include_network_functions": {"type": "bool"},
            "max_candidates": {"type": "int"},
            "max_results": {"type": "int"},
            "max_return_path_results": {"type": "int"},
            "max_seconds": {"type": "int"},
        },
        supports_check_mode=True,
    )
    p = module.params
    queries = p["queries"] or []
    if not queries:
        module.fail_json(msg="At least one query must be provided")
    for index, query in enumerate(queries):
        error = validate_query(query, index)
        if error:
            module.fail_json(msg=error)
    body = build_bulk_body(queries, {name: p[name] for name in SHARED_FIELDS})

    client = sdk.get_client(module)
    try:
        results = client.path_search.get_paths_bulk(body=body, network_id=p["network_id"], snapshot_id=p["snapshot_id"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=False, results=sdk.to_plain(results))


if __name__ == "__main__":
    main()
