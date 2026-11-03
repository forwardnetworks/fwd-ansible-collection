#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_change_set
short_description: Create, stage and commit a Forward Predict change set
description:
  - Manages a Forward Predict change set, the staged device changes you rehearse before touching the network.
  - Creates a change set against a base snapshot, stages CLI commands per device, and optionally commits them, ready for
    M(forwardnetworks.forward.fwd_predict).
  - The base defaults to the latest processed snapshot excluding predictions, because basing a change set on a prediction predicts a change against a
    change.
  - Forward Predict endpoints are unpublished and gated by the organization; a missing licence or role arrives as an HTTP error.
  - PAN-OS firewalls cannot be changed with CLI commands (Predict fails at processing time); use structured rule edits through
    M(forwardnetworks.forward.fwd_api) and the SDK's firewall Predict operations.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  state:
    description:
      - C(present) creates the change set (or reuses O(change_set_id)), stages O(commands) and commits if asked.
      - C(absent) deletes the change set, and any predicted snapshots it produced.
    type: str
    choices: [present, absent]
    default: present
  change_set_id:
    description: Existing change set to stage into or delete. Without it, C(present) creates a new one, so a rerun makes another.
    type: str
  name:
    description: Name for a new change set. Required when creating.
    type: str
  base_snapshot_id:
    description: Snapshot the change set starts from. Defaults to the latest processed, non-predicted snapshot.
    type: str
  description:
    description: Description for a new change set.
    type: str
  tags:
    description: Tags for a new change set.
    type: list
    elements: str
  commands:
    description:
      - Map of device name to the CLI text to stage on it. Replaces whatever was staged for that device.
    type: dict
  commit:
    description: Commit the staged changes. Needs O(commit_note).
    type: bool
    default: false
  commit_note:
    description: Note for the commit.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Stage and commit a change
  forwardnetworks.forward.fwd_change_set:
    network_id: "101"
    name: Core uplink shutdown
    commands:
      dc-core: |
        interface Ethernet1
         shutdown
    commit: true
    commit_note: staged for review
  register: change

- name: Clean up
  forwardnetworks.forward.fwd_change_set:
    network_id: "101"
    change_set_id: "{{ change.change_set_id }}"
    state: absent
"""

RETURN = r"""
change_set_id:
  description: ID of the change set.
  type: str
  returned: success
base_snapshot_id:
  description: Snapshot the new change set was created from.
  type: str
  returned: when a change set was created
commit:
  description: The commit, as Forward returns it.
  type: dict
  returned: when O(commit=true)
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
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "change_set_id": {"type": "str"},
            "name": {"type": "str"},
            "base_snapshot_id": {"type": "str"},
            "description": {"type": "str"},
            "tags": {"type": "list", "elements": "str"},
            "commands": {"type": "dict"},
            "commit": {"type": "bool", "default": False},
            "commit_note": {"type": "str"},
        },
        required_if=[
            ("state", "absent", ("change_set_id",)),
            ("commit", True, ("commit_note",)),
        ],
        supports_check_mode=True,
    )
    p = module.params
    if p["state"] == "present" and not p["change_set_id"] and not p["name"]:
        module.fail_json(msg="name is required to create a change set")
    if module.check_mode:
        changes = p["state"] == "absent" or not p["change_set_id"] or bool(p["commands"]) or p["commit"]
        module.exit_json(changed=bool(changes), change_set_id=p["change_set_id"], msg="check_mode: nothing changed")

    client = sdk.get_client(module)
    result = {}
    try:
        if p["state"] == "absent":
            client.change_sets.delete([p["change_set_id"]], network_id=p["network_id"])
            module.exit_json(changed=True, change_set_id=p["change_set_id"])

        if p["change_set_id"]:
            handle = client.change_sets.handle(p["change_set_id"], network_id=p["network_id"])
        else:
            base = p["base_snapshot_id"]
            if not base:
                latest = client.snapshots.latest_processed(p["network_id"])
                if latest is None:
                    module.fail_json(msg="no processed snapshot to base the change set on; pass base_snapshot_id")
                base = str(latest.id)
            handle = client.change_sets.create(
                p["name"],
                snapshot_id=base,
                network_id=p["network_id"],
                description=p["description"],
                tags=p["tags"] or (),
            )
            result["base_snapshot_id"] = base
        result["change_set_id"] = handle.id
        for device, text in (p["commands"] or {}).items():
            handle.set_commands(device, str(text))
        if p["commit"]:
            result["commit"] = sdk.to_plain(handle.commit(p["commit_note"]))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc), **result)
    finally:
        client.close()
    module.exit_json(changed=True, **result)


if __name__ == "__main__":
    main()
