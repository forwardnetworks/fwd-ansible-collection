#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshots
short_description: List Forward Networks snapshots or find the latest processed one
description:
  - Lists a network's snapshots, newest first, optionally filtered by state and collection quality.
  - With O(latest_processed) returns only the most recent fully processed snapshot, using the rule Forward itself applies (newest by creation,
    ignoring drafts and forks).
  - C(latest_processed) ignores O(state), O(limit), O(include_archived) and the collection-quality filters.
  - Predicted snapshots (from Forward Predict) are excluded from O(latest_processed) unless O(include_predicted) is set, so a change is not predicted
    on top of an earlier prediction.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  latest_processed:
    description: Return only the latest processed snapshot, as a one-item list in RV(snapshots) and also as RV(snapshot).
    type: bool
    default: false
  include_predicted:
    description: With O(latest_processed), allow predicted snapshots to be chosen.
    type: bool
    default: false
  state:
    description: Only snapshots in this state.
    type: str
    choices: [UNPACKING, UNPROCESSED, PROCESSING, PROCESSED, FAILED, CANCELED, TIMED_OUT, ARCHIVED, RESTORING, RESTORE_FAILED]
  min_successful_devices:
    description: Only snapshots with at least this many successfully collected devices.
    type: int
  min_successful_device_pct:
    description: Only snapshots with at least this percentage of devices collected successfully.
    type: float
  max_collection_failure_devices:
    description: Only snapshots with at most this many collection failures.
    type: int
  max_collection_failure_device_pct:
    description: Only snapshots with at most this percentage of collection failures.
    type: float
  max_parsing_failure_devices:
    description: Only snapshots with at most this many parsing failures.
    type: int
  max_parsing_failure_device_pct:
    description: Only snapshots with at most this percentage of parsing failures.
    type: float
  limit:
    description: Maximum number of snapshots to return.
    type: int
  include_archived:
    description: Include archived snapshots.
    type: bool
    default: false
  extra_params:
    description: Additional filter parameters passed to the API unchanged.
    type: dict
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Find the baseline snapshot for a change
  forwardnetworks.forward.fwd_snapshots:
    network_id: "101"
    latest_processed: true
  register: baseline

- name: Recent processed snapshots with good collection
  forwardnetworks.forward.fwd_snapshots:
    network_id: "101"
    state: PROCESSED
    max_collection_failure_device_pct: 5
    limit: 10
"""

RETURN = r"""
snapshots:
  description: Snapshots as Forward returns them (camelCase field names), newest first.
  type: list
  elements: dict
  returned: success
snapshot:
  description: The latest processed snapshot, or null if there is none.
  type: dict
  returned: when O(latest_processed=true)
snapshot_id:
  description: ID of the latest processed snapshot, or null if there is none.
  type: str
  returned: when O(latest_processed=true)
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

FILTERS = {
    "min_successful_devices": "minSuccessfulDevices",
    "min_successful_device_pct": "minSuccessfulDevicePct",
    "max_collection_failure_devices": "maxCollectionFailureDevices",
    "max_collection_failure_device_pct": "maxCollectionFailureDevicePct",
    "max_parsing_failure_devices": "maxParsingFailureDevices",
    "max_parsing_failure_device_pct": "maxParsingFailureDevicePct",
}


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "network_id": {"type": "str"},
            "latest_processed": {"type": "bool", "default": False},
            "include_predicted": {"type": "bool", "default": False},
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
        },
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    p = module.params
    try:
        if p["latest_processed"]:
            latest = client.snapshots.latest_processed(p["network_id"], include_predicted=p["include_predicted"])
            snapshot = sdk.to_plain(latest) if latest else None
            module.exit_json(
                changed=False,
                snapshots=[snapshot] if snapshot else [],
                snapshot=snapshot,
                snapshot_id=snapshot.get("id") if snapshot else None,
            )
        filters = {api: p[option] for option, api in FILTERS.items() if p.get(option) is not None}
        filters.update(p.get("extra_params") or {})
        snapshots = client.snapshots.list(
            p["network_id"], state=p["state"], limit=p["limit"], include_archived=p["include_archived"], **filters
        )
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=False, snapshots=sdk.to_plain(snapshots))


if __name__ == "__main__":
    main()
