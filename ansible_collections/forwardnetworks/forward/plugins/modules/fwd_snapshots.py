#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshots
short_description: Retrieve Forward Networks snapshots
description:
  - Lists snapshots for a Forward Network using GET /api/networks/{networkId}/snapshots.
  - Supports filters for state and quality metrics, plus passthrough extra params for future API fields.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network identifier.
    type: str
    required: true
  state:
    description: Filter snapshots by a specific state.
    type: str
    choices:
      - UNPACKING
      - UNPROCESSED
      - PROCESSING
      - PROCESSED
      - FAILED
      - CANCELED
      - TIMED_OUT
      - ARCHIVED
      - RESTORING
      - RESTORE_FAILED
  min_successful_devices:
    description: Minimum number of successfully modeled devices.
    type: int
  min_successful_device_pct:
    description: Minimum percentage of devices successfully modeled.
    type: float
  max_collection_failure_devices:
    description: Maximum number of devices that failed collection.
    type: int
  max_collection_failure_device_pct:
    description: Maximum percent of devices that failed collection.
    type: float
  max_parsing_failure_devices:
    description: Maximum number of devices that failed parsing.
    type: int
  max_parsing_failure_device_pct:
    description: Maximum percent of devices that failed parsing.
    type: float
  limit:
    description: Limit number of snapshots returned.
    type: int
  include_archived:
    description: Include archived snapshots.
    type: bool
    default: false
  extra_params:
    description:
      - Additional query parameters to pass through (strings only).
    type: dict
  snapshots_path:
    description:
      - Override API path. Defaults to C(/api/networks/{network_id}/snapshots).
    type: str
    default: /api/networks/{network_id}/snapshots
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: List latest snapshots
  forwardnetworks.forward.fwd_snapshots:
    network_id: "205507"
    limit: 5
  register: snaps

- name: Include archived snapshots with quality filters
  forwardnetworks.forward.fwd_snapshots:
    network_id: "205507"
    include_archived: true
    min_successful_devices: 1000
"""

RETURN = r"""
snapshots:
  description: Snapshot list returned by the API.
  type: list
  elements: dict
  returned: always
url:
  description: Final request URL.
  type: str
  returned: always
query_params:
  description: Query parameters sent to the API.
  type: dict
  returned: always
raw:
  description: Raw response payload as returned by the API.
  type: raw
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config


def build_snapshot_query(params: dict) -> dict:
    mapping = {
        "state": "state",
        "min_successful_devices": "minSuccessfulDevices",
        "min_successful_device_pct": "minSuccessfulDevicePct",
        "max_collection_failure_devices": "maxCollectionFailureDevices",
        "max_collection_failure_device_pct": "maxCollectionFailureDevicePct",
        "max_parsing_failure_devices": "maxParsingFailureDevices",
        "max_parsing_failure_device_pct": "maxParsingFailureDevicePct",
        "limit": "limit",
    }

    query = {}
    for option, api_field in mapping.items():
        value = params.get(option)
        if value is not None:
            query[api_field] = value

    if params.get("include_archived"):
        query["includeArchived"] = True

    extra = params.get("extra_params") or {}
    for key, value in extra.items():
        query[key] = value
    return query


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
            "state": {
                "type": "str",
                "choices": [
                    "UNPACKING",
                    "UNPROCESSED",
                    "PROCESSING",
                    "PROCESSED",
                    "FAILED",
                    "CANCELED",
                    "TIMED_OUT",
                    "ARCHIVED",
                    "RESTORING",
                    "RESTORE_FAILED",
                ],
            },
            "min_successful_devices": {"type": "int"},
            "min_successful_device_pct": {"type": "float"},
            "max_collection_failure_devices": {"type": "int"},
            "max_collection_failure_device_pct": {"type": "float"},
            "max_parsing_failure_devices": {"type": "int"},
            "max_parsing_failure_device_pct": {"type": "float"},
            "limit": {"type": "int"},
            "include_archived": {"type": "bool", "default": False},
            "extra_params": {"type": "dict"},
            "snapshots_path": {"type": "str", "default": "/api/networks/{network_id}/snapshots"},
        },
        supports_check_mode=True,
    )

    query = build_snapshot_query(module.params)
    path_template = module.params.get("snapshots_path") or "/api/networks/{network_id}/snapshots"
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
        payload = out.get("json") or {}
        snapshots = payload.get("snapshots") if isinstance(payload, dict) else payload
        module.exit_json(changed=False, snapshots=snapshots, url=out.get("url"), query_params=query, raw=payload)
    except ForwardApiError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
