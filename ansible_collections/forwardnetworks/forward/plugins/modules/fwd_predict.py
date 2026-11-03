#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_predict
short_description: Run Forward Predict on a committed change set
description:
  - Runs Predict on a change set to produce a snapshot of the network as it would be after the change, without touching a device.
  - By default waits for the predicted snapshot to finish processing and returns it. Its ID is the C(after) side of
    M(forwardnetworks.forward.fwd_predict_diff) and of snapshot checks.
  - The change set must already have a commit; see M(forwardnetworks.forward.fwd_change_set).
  - A prediction over a stale base can fail with no reason; reprocess the base snapshot and predict again.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  change_set_id:
    description: Change set to predict.
    type: str
    required: true
  note:
    description: Note recorded on the prediction. Forward requires one.
    type: str
    required: true
  wait:
    description: Wait for the predicted snapshot to finish processing.
    type: bool
    default: true
  wait_timeout:
    description: How long to wait for processing, in seconds.
    type: int
    default: 3600
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Rehearse the change
  forwardnetworks.forward.fwd_predict:
    network_id: "101"
    change_set_id: "{{ change.change_set_id }}"
    note: rehearsal 1
  register: predicted
"""

RETURN = r"""
snapshot_id:
  description: ID of the predicted snapshot.
  type: str
  returned: success
snapshot:
  description: The processed predicted snapshot. For a prediction not waited for, the snapshot as created but not yet processed.
  type: dict
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
            "note": {"type": "str", "required": True},
            "wait": {"type": "bool", "default": True},
            "wait_timeout": {"type": "int", "default": 3600},
        },
        supports_check_mode=True,
    )
    p = module.params
    if module.check_mode:
        module.exit_json(changed=True, msg="check_mode: prediction not started")
    client = sdk.get_client(module)
    try:
        handle = client.change_sets.handle(p["change_set_id"], network_id=p["network_id"])
        if p["wait"]:
            snapshot = handle.predict_and_wait(p["note"], timeout=p["wait_timeout"])
        else:
            snapshot = handle.predict(p["note"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    snapshot = sdk.to_plain(snapshot)
    module.exit_json(changed=True, snapshot_id=snapshot.get("id"), snapshot=snapshot)


if __name__ == "__main__":
    main()
