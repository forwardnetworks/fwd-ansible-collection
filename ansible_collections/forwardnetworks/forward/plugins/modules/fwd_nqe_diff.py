#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_nqe_diff
short_description: Compare an NQE query's results between two Forward snapshots
description:
  - Runs Forward's snapshot diff for a committed NQE query and returns one entry per changed row.
  - Only a committed query can be diffed (by O(query_id) or O(query_path)); Forward cannot diff source it has never seen.
  - For lists you already hold in a playbook, use the C(forwardnetworks.forward.nqe_diff) filter instead.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  query_id:
    description: ID of a committed query.
    type: str
  query_path:
    description: Library path of a committed query.
    type: str
  repository:
    description: Which library O(query_path) refers to.
    type: str
    choices: [org, fwd]
    default: org
  commit_id:
    description: Pin a version of the query (full 40 character hash).
    type: str
  parameters:
    description: Values for the query's declared parameters.
    type: dict
    default: {}
  before:
    description: Snapshot to compare from.
    type: str
    required: true
  after:
    description: Snapshot to compare to.
    type: str
    required: true
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: What changed in BGP sessions across the change?
  forwardnetworks.forward.fwd_nqe_diff:
    query_path: /Audits/BGP
    before: "{{ pre.snapshot_id }}"
    after: "{{ post.snapshot_id }}"
  register: bgp

- ansible.builtin.assert:
    that: bgp.summary.get('ADDED', 0) == 0
"""

RETURN = r"""
entries:
  description: One entry per changed row, with C(before), C(after) and C(type). A row added between the snapshots has no C(before); a removed one has
    no C(after).
  type: list
  elements: dict
  returned: success
summary:
  description: Count of entries per C(type).
  type: dict
  returned: success
count:
  description: Number of changed rows.
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
            "query_id": {"type": "str"},
            "query_path": {"type": "str"},
            "repository": {"type": "str", "choices": ["org", "fwd"], "default": "org"},
            "commit_id": {"type": "str"},
            "parameters": {"type": "dict", "default": {}},
            "before": {"type": "str", "required": True},
            "after": {"type": "str", "required": True},
        },
        mutually_exclusive=[("query_id", "query_path")],
        required_one_of=[("query_id", "query_path")],
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    from forward_sdk import QueryRef

    p = module.params
    try:
        ref = QueryRef(
            query_id=p["query_id"],
            path=p["query_path"],
            repository=p["repository"],
            commit_id=p["commit_id"],
            parameters=p["parameters"] or {},
        )
        entries = sdk.to_plain(client.nqe.diff(ref, before=p["before"], after=p["after"]))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    summary = {}
    for entry in entries:
        kind = str(entry.get("type", "UNKNOWN"))
        summary[kind] = summary.get(kind, 0) + 1
    module.exit_json(changed=False, entries=entries, summary=summary, count=len(entries))


if __name__ == "__main__":
    main()
