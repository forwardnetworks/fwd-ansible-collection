#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot
short_description: Delete, reprocess or annotate a Forward Networks snapshot
description:
  - Manages an existing snapshot. C(absent) deletes it, C(reprocessed) rebuilds its model in place from the collected data, C(present) only applies
    O(note).
  - Reprocessing keeps the snapshot ID. Until it finishes the snapshot cannot answer queries, and if it is the network's only processed snapshot the
    network has none meanwhile.
  - Deleting a snapshot that is already gone is not a change. In check mode every requested action is reported as a change, since the snapshot is not read.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  snapshot_id:
    description: Snapshot ID.
    type: str
    required: true
  state:
    description: What to do with the snapshot.
    type: str
    choices: [present, absent, reprocessed]
    default: present
  note:
    description: Replace the snapshot's note. Always reported as a change, since Forward has no cheap read of the current note.
    type: str
  network_id:
    description: Network the snapshot belongs to. Needed with O(wait) after C(reprocessed). Falls back to E(FORWARD_NETWORK_ID).
    type: str
  wait:
    description: With C(reprocessed), wait until the snapshot is processed again.
    type: bool
    default: true
  wait_timeout:
    description: How long to wait for reprocessing, in seconds.
    type: int
    default: 3600
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Rebuild a snapshot under current parser settings
  forwardnetworks.forward.fwd_snapshot:
    network_id: "101"
    snapshot_id: "1234"
    state: reprocessed

- name: Delete a snapshot
  forwardnetworks.forward.fwd_snapshot:
    snapshot_id: "1234"
    state: absent
"""

RETURN = r"""
snapshot:
  description: The snapshot after reprocessing finished.
  type: dict
  returned: when reprocessed and waited for
"""

import time

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
            "state": {"type": "str", "choices": ["present", "absent", "reprocessed"], "default": "present"},
            "note": {"type": "str"},
            "network_id": {"type": "str"},
            "wait": {"type": "bool", "default": True},
            "wait_timeout": {"type": "int", "default": 3600},
        },
        supports_check_mode=True,
    )
    p = module.params
    sid = p["snapshot_id"]
    if module.check_mode:
        module.exit_json(changed=p["state"] != "present" or p["note"] is not None, msg="check_mode: nothing changed")
    client = sdk.get_client(module)
    from forward_sdk import ForwardNotFoundError

    result = {}
    try:
        if p["state"] == "absent":
            try:
                client.snapshots.delete(sid)
            except ForwardNotFoundError:
                module.exit_json(changed=False)
            module.exit_json(changed=True)
        if p["note"] is not None:
            client.snapshots.set_note(sid, p["note"])
        if p["state"] == "reprocessed":
            change = client.snapshots.reprocess(sid)
            if p["wait"]:
                # The listing can still show PROCESSED just after the request; let it leave that state first.
                deadline = time.monotonic() + 15
                if change.state in (None, "PROCESSED") and p["network_id"]:
                    while time.monotonic() < deadline:
                        current = [s for s in client.snapshots.list(p["network_id"]) if str(s.id) == sid]
                        if not current or str(current[0].state) != "PROCESSED":
                            break
                        time.sleep(2)
                snapshot = client.snapshots.wait_until_processed(sid, network_id=p["network_id"], timeout=p["wait_timeout"])
                result["snapshot"] = sdk.to_plain(snapshot)
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=p["state"] == "reprocessed" or p["note"] is not None, **result)


if __name__ == "__main__":
    main()
