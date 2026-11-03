#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_export
short_description: Download a Forward Networks snapshot archive
description:
  - Downloads a snapshot as a ZIP archive to a local file.
  - With no device or obfuscation options this is the whole snapshot; any of them selects Forward's subset export.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  snapshot_id:
    description: Snapshot to export.
    type: str
    required: true
  dest:
    description: Destination file path on the host running the module.
    type: path
    required: true
  only:
    description: Restrict the export, for example to device configurations.
    type: str
    choices: [CONFIG]
  include_devices:
    description: Export only these devices (globs such as C(pa*) are accepted). Exclusive with O(exclude_devices).
    type: list
    elements: str
  exclude_devices:
    description: Export everything except these devices. Exclusive with O(include_devices).
    type: list
    elements: str
  obfuscation_key:
    description: Obfuscate sensitive data, keyed by this value.
    type: str
  force:
    description: Overwrite O(dest) if it exists. When C(false) an existing file is left alone and nothing changes.
    type: bool
    default: true
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Archive a snapshot's configs
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "1234"
    dest: /var/backups/forward/1234.zip
    only: CONFIG
"""

RETURN = r"""
dest:
  description: Path of the archive.
  type: str
  returned: always
snapshot_id:
  description: Snapshot that was exported.
  type: str
  returned: always
"""

import os
import tempfile

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
            "dest": {"type": "path", "required": True},
            "only": {"type": "str", "choices": ["CONFIG"]},
            "include_devices": {"type": "list", "elements": "str"},
            "exclude_devices": {"type": "list", "elements": "str"},
            "obfuscation_key": {"type": "str", "no_log": True},
            "force": {"type": "bool", "default": True},
        },
        mutually_exclusive=[("include_devices", "exclude_devices")],
        supports_check_mode=True,
    )
    p = module.params
    dest = p["dest"]
    exists = os.path.exists(dest)
    if exists and not p["force"]:
        module.exit_json(changed=False, dest=dest, snapshot_id=p["snapshot_id"])
    if module.check_mode:
        module.exit_json(changed=True, dest=dest, snapshot_id=p["snapshot_id"])

    client = sdk.get_client(module)
    dest_dir = os.path.dirname(os.path.abspath(dest))
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".fwd_snapshot_", suffix=".zip", dir=dest_dir)
        os.close(fd)
        client.snapshots.download(
            p["snapshot_id"],
            tmp_path,
            only=p["only"],
            include_devices=p["include_devices"],
            exclude_devices=p["exclude_devices"],
            obfuscation_key=p["obfuscation_key"],
        )
        if os.path.getsize(tmp_path) == 0:
            module.fail_json(msg="Snapshot export returned no data")
        module.atomic_move(tmp_path, dest)
    except OSError as exc:
        module.fail_json(msg="Cannot write %s: %s" % (dest, exc))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    module.exit_json(changed=True, dest=dest, snapshot_id=p["snapshot_id"])


if __name__ == "__main__":
    main()
