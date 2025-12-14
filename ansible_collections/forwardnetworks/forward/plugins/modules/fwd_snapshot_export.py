#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_export
short_description: Export Forward Networks snapshots to a ZIP file
description:
  - Downloads a snapshot archive via C(/api/snapshots/{snapshotId}).
  - Supports exporting the full snapshot, configuration-only archives, or filtered/obfuscated subsets using POST.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  snapshot_id:
    description: Forward snapshot identifier to export.
    type: str
    required: true
  dest:
    description: Local path to write the exported ZIP file.
    type: path
    required: true
  only:
    description:
      - Optional filter for GET exports.
      - Use C(CONFIG) to include only device configuration files.
    type: str
    choices: [CONFIG]
  include_devices:
    description:
      - Device names to include when generating a custom export (POST).
      - Mutually exclusive with C(exclude_devices).
    type: list
    elements: str
  exclude_devices:
    description:
      - Device names to exclude when generating a custom export (POST).
      - Mutually exclusive with C(include_devices).
    type: list
    elements: str
  obfuscation_key:
    description:
      - Optional obfuscation key for POST exports.
      - See Forward documentation on snapshot obfuscation.
    type: str
  force:
    description:
      - Overwrite the destination file if it exists.
    type: bool
    default: true
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Download entire snapshot
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "snap-123"
    dest: "/tmp/snap-123.zip"

- name: Download config-only snapshot
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "snap-123"
    dest: "/tmp/snap-123-configs.zip"
    only: CONFIG

- name: Download custom subset (POST)
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "snap-123"
    dest: "/tmp/snap-123-core.zip"
    include_devices:
      - edge-1
      - core-1
    obfuscation_key: secret
"""

RETURN = r"""
dest:
  description: Destination file path containing the ZIP archive.
  type: str
  returned: always
snapshot_id:
  description: Snapshot identifier that was exported.
  type: str
  returned: always
changed:
  description: Whether the destination file was (re)written.
  type: bool
  returned: always
"""

import os
import tempfile

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "token": {"type": "str", "no_log": True},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool", "default": True},
            "timeout": {"type": "int", "default": 30},
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

    dest = module.params["dest"]
    dest_exists = os.path.exists(dest)

    # Determine whether we need to download (skip if file exists and force=False)
    if dest_exists and not module.params["force"]:
        module.exit_json(changed=False, dest=dest, snapshot_id=module.params["snapshot_id"])

    method = "GET"
    query_params = {}
    body = None
    path = f"/api/snapshots/{module.params['snapshot_id']}"

    if module.params.get("include_devices") or module.params.get("exclude_devices") or module.params.get("obfuscation_key"):
        method = "POST"
        body = {}
        if module.params.get("include_devices"):
            body["includeDevices"] = module.params["include_devices"]
        if module.params.get("exclude_devices"):
            body["excludeDevices"] = module.params["exclude_devices"]
        if module.params.get("obfuscation_key"):
            body["obfuscationKey"] = module.params["obfuscation_key"]
    elif module.params.get("only"):
        query_params["only"] = module.params["only"]

    if module.check_mode:
        module.exit_json(changed=not dest_exists, dest=dest, snapshot_id=module.params["snapshot_id"])

    cfg = get_forward_config(module.params)
    client = ForwardClient(
        module,
        base_url=cfg["base_url"],
        token=cfg["token"],
        username=cfg["username"],
        password=cfg["password"],
        validate_certs=cfg["validate_certs"],
        timeout=cfg["timeout"],
    )

    try:
        response = client.request(method=method, path=path, query_params=query_params, body=body)
    except ForwardApiError as exc:
        module.fail_json(msg=str(exc))

    data = response.get("bytes")
    if not data:
        module.fail_json(msg="Snapshot export returned no data")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="fwd_snapshot_", suffix=".zip")
    os.close(tmp_fd)
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(data)
        module.atomic_move(tmp_path, dest)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    module.exit_json(changed=True, dest=dest, snapshot_id=module.params["snapshot_id"])


if __name__ == "__main__":
    main()
