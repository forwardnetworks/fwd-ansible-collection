#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_devices
short_description: Retrieve Forward Networks device inventory
description:
  - Fetches device inventory for a Forward Network (optionally a specific Snapshot) using GET /api/networks/{networkId}/devices.
  - Supports common filters and query parameters, plus passthrough extra params for new API fields.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network identifier.
    type: str
    required: true
  snapshot_id:
    description: Optional Snapshot identifier.
    type: str
  name:
    description: Glob filter for the C(name) field.
    type: str
  display_name:
    description: Glob filter for the C(displayName) field.
    type: str
  source_name:
    description: Glob filter for the C(sourceName) field.
    type: str
  device_type:
    description: Glob filter for the C(type) field.
    type: str
  vendor:
    description: Glob filter for the C(vendor) field.
    type: str
  model:
    description: Glob filter for the C(model) field.
    type: str
  platform:
    description: Glob filter for the C(platform) field.
    type: str
  os_version:
    description: Glob filter for the C(osVersion) field.
    type: str
  collection_error:
    description: Glob filter for the C(collectionError) field.
    type: str
  processing_error:
    description: Glob filter for the C(processingError) field.
    type: str
  skip:
    description: Number of devices to skip (pagination).
    type: int
  limit:
    description: Maximum number of devices to return.
    type: int
  include_tags:
    description: Include device tags in the response.
    type: bool
    default: false
  extra_params:
    description:
      - Additional query parameters to pass through to the API.
      - Keys/values must be strings (lists are converted to repeated params).
    type: dict
  devices_path:
    description:
      - Override API path. Defaults to C(/api/networks/{network_id}/devices).
    type: str
    default: /api/networks/{network_id}/devices
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Fetch all devices (latest Snapshot)
  forwardnetworks.forward.fwd_devices:
    network_id: "205507"
  register: devices

- name: Fetch devices with tags for a Snapshot
  forwardnetworks.forward.fwd_devices:
    network_id: "205507"
    snapshot_id: "snap-123"
    include_tags: true
    name: "core-*"
  register: tagged_devices
"""

RETURN = r"""
devices:
  description: List of device objects returned by the API.
  type: list
  elements: dict
  returned: always
url:
  description: Final request URL (including query params).
  type: str
  returned: always
query_params:
  description: Query parameters that were sent.
  type: dict
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config
from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import build_device_query


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "token": {"type": "str", "no_log": True},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool", "default": True},
            "timeout": {"type": "int", "default": 30},
            "network_id": {"type": "str", "required": True},
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
            "devices_path": {"type": "str", "default": "/api/networks/{network_id}/devices"},
        },
        supports_check_mode=True,
    )

    query = build_device_query(module.params)
    path_template = module.params.get("devices_path") or "/api/networks/{network_id}/devices"
    path = path_template.format(network_id=module.params["network_id"], networkId=module.params["network_id"])

    cfg = get_forward_config(module.params)

    try:
        client = ForwardClient(
            module,
            base_url=cfg["base_url"],
            token=cfg["token"],
            username=cfg["username"],
            password=cfg["password"],
            validate_certs=cfg["validate_certs"],
            timeout=cfg["timeout"],
        )
        out = client.request(method="GET", path=path, query_params=query)
        module.exit_json(changed=False, devices=out.get("json") or [], url=out.get("url"), query_params=query)
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
