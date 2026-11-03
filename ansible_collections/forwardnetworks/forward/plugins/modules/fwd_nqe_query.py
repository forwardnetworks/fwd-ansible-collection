#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_nqe_query
short_description: Run a Forward Networks NQE query and return every row
description:
  - Runs a Network Query Engine (NQE) query against a snapshot and returns all result rows.
  - The query is given as inline source (O(query)), a committed query ID (O(query_id)) or a path in the query library (O(query_path)).
  - Results are paged with the SDK's guard rails, so a result set that ends early or a server that stops advancing fails loudly instead of returning
    a partial answer.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description:
      - Forward network ID.
      - Falls back to E(FORWARD_NETWORK_ID).
    type: str
  snapshot_id:
    description:
      - Snapshot to query.
      - Defaults to the network's latest processed snapshot.
    type: str
  query:
    description: Inline NQE source to run without saving it.
    type: str
  query_id:
    description: ID of a committed query (for example C(FQ_...)).
    type: str
  query_path:
    description: Path of a query in the query library, such as C(/Audits/Interfaces).
    type: str
  repository:
    description: Which library O(query_path) refers to. C(org) is your organization's library, C(fwd) is Forward's.
    type: str
    choices: [org, fwd]
    default: org
  commit_id:
    description:
      - Pin a specific version of a committed query (full 40 character hash).
      - Valid with O(query_id) or O(query_path).
    type: str
  parameters:
    description: Values for the query's declared parameters.
    type: dict
    default: {}
  query_timeout:
    description: How long to wait for the query to finish, in seconds.
    type: float
    default: 1800
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Run a library query against the latest snapshot
  forwardnetworks.forward.fwd_nqe_query:
    network_id: "101"
    query_path: /Audits/Interfaces
    parameters:
      min_speed: 10000
  register: out

- name: Run inline NQE against a specific snapshot
  forwardnetworks.forward.fwd_nqe_query:
    network_id: "101"
    snapshot_id: "1234"
    query: |
      foreach device in network.devices
      select {name: device.name, platform: device.platform}
  register: devices
"""

RETURN = r"""
rows:
  description: Result rows. Columns are defined by the query.
  type: list
  elements: dict
  returned: success
count:
  description: Number of rows returned.
  type: int
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk


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
            "query": {"type": "str"},
            "query_id": {"type": "str"},
            "query_path": {"type": "str"},
            "repository": {"type": "str", "choices": ["org", "fwd"], "default": "org"},
            "commit_id": {"type": "str"},
            "parameters": {"type": "dict", "default": {}},
            "query_timeout": {"type": "float", "default": 1800},
        },
        mutually_exclusive=[("query", "query_id", "query_path")],
        required_one_of=[("query", "query_id", "query_path")],
        supports_check_mode=True,  # read-only, so it runs in check mode too
    )
    client = sdk.get_client(module)
    from forward_sdk import QueryRef

    p = module.params
    try:
        ref = QueryRef(
            text=p["query"],
            query_id=p["query_id"],
            path=p["query_path"],
            repository=p["repository"],
            commit_id=p["commit_id"],
            parameters=p["parameters"] or {},
        )
        rows = client.nqe.query(ref, network_id=p["network_id"], snapshot_id=p["snapshot_id"], timeout=p["query_timeout"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=False, rows=rows, count=len(rows))


if __name__ == "__main__":
    main()
