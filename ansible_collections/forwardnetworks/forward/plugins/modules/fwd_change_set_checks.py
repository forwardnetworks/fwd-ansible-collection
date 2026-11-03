#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_change_set_checks
short_description: Read intent check results for a Forward Predict change set
description:
  - Returns the intent checks attached to a change set with their results, against the base snapshot or against a predicted snapshot.
  - Use it after M(forwardnetworks.forward.fwd_predict) to see whether the change breaks an intent, before making it.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  change_set_id:
    description: Change set whose checks to read.
    type: str
    required: true
  snapshot_id:
    description: Predicted snapshot to evaluate against. Without it, results are for the change set's base.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Checks on the predicted snapshot
  forwardnetworks.forward.fwd_change_set_checks:
    network_id: "101"
    change_set_id: "{{ change.change_set_id }}"
    snapshot_id: "{{ predicted.snapshot_id }}"
  register: verdict

- ansible.builtin.assert:
    that: verdict.checks | selectattr('status', 'equalto', 'FAIL') | list | length == 0
"""

RETURN = r"""
checks:
  description: Check results as Forward returns them (C(id), C(name), C(status), C(numViolations), C(definition) and so on).
  type: list
  elements: dict
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
            "change_set_id": {"type": "str", "required": True},
            "snapshot_id": {"type": "str"},
        },
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    try:
        handle = client.change_sets.handle(p["change_set_id"], network_id=p["network_id"])
        checks = handle.checks(snapshot_id=p["snapshot_id"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=False, checks=sdk.to_plain(checks))


if __name__ == "__main__":
    main()
