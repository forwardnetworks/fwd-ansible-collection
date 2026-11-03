#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_predict_diff
short_description: Summarize what changed between a baseline and a predicted snapshot
description:
  - Reads Forward's snapshot diffs to state the blast radius of a change, typically between a base snapshot and a Predict snapshot.
  - Returns a per-area count of differences and, optionally, how subnet-to-subnet connectivity changed.
  - Subnet connectivity is computed after the snapshot is ready, so the module polls until it settles. Zeros while it is still computing mean "not
    finished", not "nothing changed".
  - A settled zero is still ambiguous. If C(totalSubnetPairs) in C(subnet_connectivity) is zero, the network has no locations defined and nothing
    was compared, which is not an all-clear.
  - Connectivity diffs need the C(LOCATION_CONNECTIVITY_DIFFS) organization property. An area Forward refuses to compute is reported in C(errors)
    rather than failing the module; authentication, rate limit and server errors still fail it.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  before:
    description: Baseline snapshot ID.
    type: str
    required: true
  after:
    description: Snapshot ID to compare to it, usually the predicted snapshot.
    type: str
    required: true
  include:
    description: Which comparisons to run.
    type: list
    elements: str
    choices: [counts, subnet_connectivity]
    default: [counts, subnet_connectivity]
  connectivity_timeout:
    description: How long to wait for the connectivity comparison to settle, in seconds.
    type: int
    default: 300
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: What would the change touch?
  forwardnetworks.forward.fwd_predict_diff:
    before: "{{ baseline.snapshot_id }}"
    after: "{{ predicted.snapshot_id }}"
  register: blast

- name: Stop if sites would lose connectivity
  ansible.builtin.assert:
    that:
      - blast.subnet_connectivity.totalSubnetPairs > 0
      - blast.subnet_connectivity.newlyIsolatedSubnetPairs | default(0) == 0
"""

RETURN = r"""
counts:
  description: Per-area difference counts keyed by area (devices, interfaces, topology, l2, acl, nat, arp, mac). Each has C(count) and C(complete);
    C(complete) false means the count is a lower bound so far.
  type: dict
  returned: when counts are included
subnet_connectivity:
  description: How connectivity between subnets changed, once Forward finished computing it.
  type: dict
  returned: when subnet_connectivity is included and available
errors:
  description: Areas Forward refused or failed to compute, keyed by area, with the reason.
  type: dict
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

AREAS = ("devices", "interfaces", "topology", "l2", "acl", "nat", "arp", "mac")


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "before": {"type": "str", "required": True},
            "after": {"type": "str", "required": True},
            "include": {
                "type": "list",
                "elements": "str",
                "choices": ["counts", "subnet_connectivity"],
                "default": ["counts", "subnet_connectivity"],
            },
            "connectivity_timeout": {"type": "int", "default": 300},
        },
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    from forward_sdk import ForwardBadRequestError, ForwardNotFoundError, ForwardPermissionError

    # Only a refusal (gating, role, absent feature) is reported per area. Bad credentials, rate limits and
    # server errors fail the task, so they are never mistaken for an empty result.
    refused = (ForwardPermissionError, ForwardNotFoundError, ForwardBadRequestError)

    result = {"errors": {}}
    diffs = client.snapshot_diffs
    try:
        if "counts" in p["include"]:
            counts = {}
            for area in AREAS:
                try:
                    counts[area] = sdk.to_plain(diffs.count(area, p["before"], p["after"]))
                except refused as exc:
                    result["errors"][area] = sdk.error_message(exc)
            result["counts"] = counts
        if "subnet_connectivity" in p["include"]:
            try:
                result["subnet_connectivity"] = sdk.to_plain(
                    diffs.wait_for_subnet_connectivity(p["before"], p["after"], timeout=p["connectivity_timeout"])
                )
            except refused as exc:
                result["errors"]["subnet_connectivity"] = sdk.error_message(exc)
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc), **result)
    finally:
        client.close()
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
