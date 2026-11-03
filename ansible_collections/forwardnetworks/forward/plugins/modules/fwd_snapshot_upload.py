#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_upload
short_description: Upload snapshot archives into a Forward Networks network
description:
  - Uploads one or more snapshot ZIP archives (configs and command output) into a network, creating a snapshot.
  - Several archives are merged into one snapshot, so they must not describe the same device.
  - Archives are streamed from disk, so size does not matter to memory.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  files:
    description: Paths of the ZIP archives on the host running the module.
    type: list
    elements: path
    required: true
  note:
    description: Note for the new snapshot.
    type: str
  process:
    description: Build the network model after importing.
    type: bool
    default: true
  wait:
    description: Wait until the snapshot is processed.
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
- name: Upload a collected snapshot and wait for it
  forwardnetworks.forward.fwd_snapshot_upload:
    network_id: "101"
    files: [/srv/collections/lab.zip]
    note: lab, from ansible
  register: uploaded
"""

RETURN = r"""
snapshot_id:
  description: ID of the new snapshot.
  type: str
  returned: success
snapshot:
  description: The snapshot as Forward returns it (processed, when waited for).
  type: dict
  returned: success
"""

import os

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
            "files": {"type": "list", "elements": "path", "required": True},
            "note": {"type": "str"},
            "process": {"type": "bool", "default": True},
            "wait": {"type": "bool", "default": True},
            "wait_timeout": {"type": "int", "default": 3600},
        },
        supports_check_mode=True,
    )
    p = module.params
    missing = [f for f in p["files"] if not os.path.isfile(f)]
    if missing:
        module.fail_json(msg="snapshot archive(s) not found: %s" % ", ".join(missing))
    if module.check_mode:
        module.exit_json(changed=True, msg="check_mode: nothing uploaded")
    client = sdk.get_client(module)
    try:
        snapshot = client.snapshots.upload(p["files"], network_id=p["network_id"], note=p["note"], process=p["process"])
        if p["wait"] and p["process"] and snapshot.id:
            snapshot = client.snapshots.wait_until_processed(
                str(snapshot.id), network_id=p["network_id"], timeout=p["wait_timeout"]
            )
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    snapshot = sdk.to_plain(snapshot)
    module.exit_json(changed=True, snapshot_id=snapshot.get("id"), snapshot=snapshot)


if __name__ == "__main__":
    main()
