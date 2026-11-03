#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_devices
short_description: List devices in a Forward Networks snapshot
description:
  - Lists the devices in a network snapshot, optionally filtered by name, vendor, model, platform and so on.
  - Without O(skip) or O(limit) every matching device is returned, fetched a page at a time.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  snapshot_id:
    description: Snapshot ID. Defaults to the network's latest processed snapshot.
    type: str
  name:
    description: Filter by device name (glob patterns allowed).
    type: str
  display_name:
    description: Filter by display name.
    type: str
  source_name:
    description: Filter by source name.
    type: str
  device_type:
    description: Filter by device type.
    type: str
  vendor:
    description: Filter by vendor.
    type: str
  model:
    description: Filter by model.
    type: str
  platform:
    description: Filter by platform.
    type: str
  os_version:
    description: Filter by OS version.
    type: str
  collection_error:
    description: Filter by collection error.
    type: str
  processing_error:
    description: Filter by processing error.
    type: str
  skip:
    description: Number of devices to skip. Setting this or O(limit) returns a single page instead of every device.
    type: int
  limit:
    description: Maximum number of devices to return.
    type: int
  include_tags:
    description: Include each device's tags. Without it the C(tags) field is absent, which means "not requested".
    type: bool
    default: false
  extra_params:
    description: Additional filter parameters passed to the API unchanged.
    type: dict
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Core routers with their tags
  forwardnetworks.forward.fwd_devices:
    network_id: "101"
    name: "core-*"
    include_tags: true
  register: core
"""

RETURN = r"""
devices:
  description: Device objects as Forward returns them (camelCase field names).
  type: list
  elements: dict
  returned: success
count:
  description: Number of devices returned.
  type: int
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk
from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import build_device_filters


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "network_id": {"type": "str"},
            "snapshot_id": {"type": "str"},
            "name": {"type": "str"},
            "display_name": {"type": "str"},
            "source_name": {"type": "str"},
            "device_type": {"type": "str"},
            "vendor": {"type": "str"},
            "model": {"type": "str"},
            "platform": {"type": "str"},
            "os_version": {"type": "str"},
            "collection_error": {"type": "str"},
            "processing_error": {"type": "str"},
            "skip": {"type": "int"},
            "limit": {"type": "int"},
            "include_tags": {"type": "bool", "default": False},
            "extra_params": {"type": "dict"},
        },
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    p = module.params
    filters = build_device_filters(p, p.get("extra_params"))
    with_ = ["tags"] if p["include_tags"] else None
    try:
        if p["skip"] is not None or p["limit"] is not None:
            devices = client.devices.list(
                p["network_id"], snapshot_id=p["snapshot_id"], skip=p["skip"], limit=p["limit"], with_=with_, **filters
            )
        else:
            devices = list(client.devices.iter(p["network_id"], snapshot_id=p["snapshot_id"], with_=with_, **filters))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    devices = sdk.to_plain(devices)
    module.exit_json(changed=False, devices=devices, count=len(devices))


if __name__ == "__main__":
    main()
