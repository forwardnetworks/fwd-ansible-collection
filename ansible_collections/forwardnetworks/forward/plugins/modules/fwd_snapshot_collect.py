#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_snapshot_collect
short_description: Trigger and wait for Forward Networks snapshots
description:
  - Triggers a network collection via C(POST /api/networks/{networkId}/startcollection).
  - Optionally waits for the latest processed snapshot via C(GET /api/networks/{networkId}/snapshots/latestProcessed).
  - Supports change-control workflows by detecting when a new snapshot becomes available.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network identifier.
    type: str
    required: true
  start_collection:
    description:
      - Whether to trigger a new collection before waiting.
      - Set to C(false) to only wait for an existing in-progress collection to finish.
    type: bool
    default: true
  wait:
    description: Wait for a processed snapshot before returning.
    type: bool
    default: true
  wait_for_new:
    description:
      - When C(true), waits until the processed snapshot differs from the baseline snapshot.
      - Set to C(false) to simply wait for any processed snapshot (useful when a collection is already running).
    type: bool
    default: true
  previous_snapshot_id:
    description:
      - Baseline snapshot ID to compare against when C(wait_for_new=true).
      - If omitted, the module fetches the current latest processed snapshot before triggering a new collection.
    type: str
  wait_timeout:
    description: How long to wait for snapshot processing (seconds).
    type: int
    default: 900
  wait_interval:
    description: Poll interval while waiting (seconds).
    type: int
    default: 10
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Trigger snapshot and wait for completion
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "{{ lookup('env', 'FWD_NETWORKID') }}"

- name: Wait for a collection already in progress
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "205507"
    start_collection: false
    wait_for_new: false
"""

RETURN = r"""
snapshot:
  description: Snapshot info returned by the API (if available).
  type: dict
  returned: when supported
snapshot_id:
  description: ID of the processed snapshot.
  type: str
  returned: when supported
changed:
  description: Indicates whether a collection was triggered.
  type: bool
  returned: always
"""

import time

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import ForwardApiError, ForwardClient
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config


def fetch_latest_snapshot(client: ForwardClient, network_id: str):
    try:
        out = client.request(
            method="GET",
            path=f"/api/networks/{network_id}/snapshots/latestProcessed",
            allow_status={404},
        )
        if out["status_code"] == 404:
            return None
        return out.get("json")
    except ForwardApiError as exc:
        raise exc


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
            "start_collection": {"type": "bool", "default": True},
            "wait": {"type": "bool", "default": True},
            "wait_for_new": {"type": "bool", "default": True},
            "previous_snapshot_id": {"type": "str"},
            "wait_timeout": {"type": "int", "default": 900},
            "wait_interval": {"type": "int", "default": 10},
        },
        supports_check_mode=True,
    )

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

    network_id = module.params["network_id"]
    wait_for_new = module.params["wait_for_new"]
    wait_enabled = module.params["wait"]
    previous_snapshot_id = module.params.get("previous_snapshot_id")

    baseline_snapshot = None
    if wait_for_new and not previous_snapshot_id:
        baseline_snapshot = fetch_latest_snapshot(client, network_id)
        if baseline_snapshot:
            previous_snapshot_id = baseline_snapshot.get("id")

    changed = False
    if module.params["start_collection"] and not module.check_mode:
        client.request(method="POST", path=f"/api/networks/{network_id}/startcollection")
        changed = True

    final_snapshot = baseline_snapshot
    end_time = time.time() + module.params["wait_timeout"]

    if wait_enabled:
        while time.time() < end_time:
            candidate = fetch_latest_snapshot(client, network_id)
            if not candidate:
                time.sleep(module.params["wait_interval"])
                continue

            candidate_id = candidate.get("id")
            if not wait_for_new or (candidate_id and candidate_id != previous_snapshot_id):
                final_snapshot = candidate
                break

            time.sleep(module.params["wait_interval"])
        else:
            module.fail_json(msg="Timed out waiting for processed snapshot", changed=changed)
    else:
        final_snapshot = final_snapshot or fetch_latest_snapshot(client, network_id)

    module.exit_json(
        changed=changed,
        snapshot=final_snapshot,
        snapshot_id=(final_snapshot or {}).get("id"),
    )


if __name__ == "__main__":
    main()
