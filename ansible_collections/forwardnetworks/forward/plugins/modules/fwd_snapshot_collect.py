#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_collect
short_description: Trigger a Forward Networks collection, or wait on one, and get its snapshot
description:
  - Starts a network collection (or, with O(start_collection=false), picks up the one already queued or running) and, by default, waits for the
    collection to finish and for the resulting snapshot to be processed.
  - Predictions are ignored when identifying the new snapshot, so running a Predict rehearsal at the same time does not confuse it.
  - Use it in change-control playbooks to get a post-change snapshot ID.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  start_collection:
    description:
      - Start a new collection. Set C(false) to wait on the collection already queued or running on the network instead.
      - With C(false) the module fails if no collection is in progress.
    type: bool
    default: true
  wait:
    description:
      - Wait for the collection to finish and the snapshot to be processed.
      - When C(false) the module returns as soon as the collection is queued, without a snapshot ID.
    type: bool
    default: true
  wait_timeout:
    description: How long to wait for the collection, then separately for processing, in seconds. The collection carries on in Forward if this elapses.
    type: int
    default: 3600
  wait_interval:
    description: Seconds between status checks.
    type: int
    default: 10
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Collect after the change window and wait for the snapshot
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "101"
  register: post

- name: Wait for a collection someone else started
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "101"
    start_collection: false

- name: Queue a collection and carry on
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "101"
    wait: false
"""

RETURN = r"""
task_id:
  description: ID of the collector task Forward created.
  type: str
  returned: success
status:
  description: The task's last known status (C(SUCCEEDED), or C(QUEUED) when not waiting).
  type: str
  returned: success
snapshot_id:
  description: ID of the new snapshot. Absent when O(wait=false).
  type: str
  returned: when waiting
snapshot:
  description: The processed snapshot as Forward returns it.
  type: dict
  returned: when waiting
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
            "start_collection": {"type": "bool", "default": True},
            "wait": {"type": "bool", "default": True},
            "wait_timeout": {"type": "int", "default": 3600},
            "wait_interval": {"type": "int", "default": 10},
        },
        supports_check_mode=True,
    )
    p = module.params
    if module.check_mode:
        module.exit_json(changed=p["start_collection"], msg="check_mode: nothing started")
    client = sdk.get_client(module)
    result = {}
    try:
        run = client.snapshots.collect(
            p["network_id"],
            start=p["start_collection"],
            wait=p["wait"],
            timeout=p["wait_timeout"], poll_interval=p["wait_interval"]
        )
        result = {"task_id": run.task_id, "status": run.status}
        if p["wait"] and run.snapshot_id:
            snapshot = client.snapshots.wait_until_processed(
                run.snapshot_id,
                network_id=p["network_id"],
                poll_interval=p["wait_interval"],
                timeout=p["wait_timeout"],
            )
            result.update(snapshot_id=run.snapshot_id, snapshot=sdk.to_plain(snapshot))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc), **result)
    finally:
        client.close()
    module.exit_json(changed=p["start_collection"], **result)


if __name__ == "__main__":
    main()
