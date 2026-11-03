#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_checks
short_description: Read intent check results for a Forward Networks snapshot
description:
  - Returns the checks defined on a snapshot with their current status, optionally filtered by type, priority and status.
  - With O(check_id) returns a single check including its diagnosis.
  - Use it after a collection or a Predict run to gate a pipeline on check results.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  snapshot_id:
    description: Snapshot ID.
    type: str
    required: true
  check_id:
    description: Return only this check, with diagnosis.
    type: str
  type:
    description: Only checks of these types.
    type: list
    elements: str
    choices: [Isolation, Reachability, Existential, QueryStringBased, Predefined, NQE]
  priority:
    description: Only checks with these priorities.
    type: list
    elements: str
    choices: [NOT_SET, LOW, MEDIUM, HIGH]
  status:
    description: Only checks with these statuses.
    type: list
    elements: str
    choices: [NONE, PASS, FAIL, ERROR, TIMEOUT, PROCESSING]
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Failing high priority checks
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "{{ post.snapshot_id }}"
    priority: [HIGH]
    status: [FAIL, ERROR]
  register: failing

- ansible.builtin.assert:
    that: failing.checks | length == 0
"""

RETURN = r"""
checks:
  description: Check results, as Forward returns them.
  type: list
  elements: dict
  returned: when O(check_id) is not given
check:
  description: A single check result with diagnosis.
  type: dict
  returned: when O(check_id) is given
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
            "snapshot_id": {"type": "str", "required": True},
            "check_id": {"type": "str"},
            "type": {
                "type": "list",
                "elements": "str",
                "choices": ["Isolation", "Reachability", "Existential", "QueryStringBased", "Predefined", "NQE"],
            },
            "priority": {"type": "list", "elements": "str", "choices": ["NOT_SET", "LOW", "MEDIUM", "HIGH"]},
            "status": {
                "type": "list",
                "elements": "str",
                "choices": ["NONE", "PASS", "FAIL", "ERROR", "TIMEOUT", "PROCESSING"],
            },
        },
        mutually_exclusive=[("check_id", "type"), ("check_id", "priority"), ("check_id", "status")],
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    p = module.params
    try:
        if p["check_id"]:
            check = client.checks.get_check(snapshot_id=p["snapshot_id"], check_id=p["check_id"])
            module.exit_json(changed=False, check=sdk.to_plain(check))
        checks = client.checks.get_checks(
            snapshot_id=p["snapshot_id"], type=p["type"], priority=p["priority"], status=p["status"]
        )
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=False, checks=sdk.to_plain(checks))


if __name__ == "__main__":
    main()
