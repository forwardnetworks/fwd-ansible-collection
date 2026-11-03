#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_collection_schedule
short_description: Manage a Forward Networks collection schedule
description:
  - Ensures a scheduled collection exists with the given settings, or is gone.
  - Schedules have no name, so they are identified by O(schedule_id).
  - Without O(schedule_id), C(present) looks for a schedule with identical settings and creates one only if none matches, which keeps reruns idempotent.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Network ID. Falls back to C(FORWARD_NETWORK_ID).
    type: str
  state:
    description: Whether the schedule should exist.
    type: str
    choices: [present, absent]
    default: present
  schedule_id:
    description: Schedule ID. Required for C(absent); with C(present) it selects the schedule to correct.
    type: str
  enabled:
    description: Whether the schedule runs.
    type: bool
    default: true
  days_of_the_week:
    description: Days to collect on, as numbers (1 is Monday through 7 is Sunday). Used with O(times).
    type: list
    elements: int
    default: [1, 2, 3, 4, 5, 6, 7]
  times:
    description: Times of day to collect, as C(HH:MM) strings in O(time_zone).
    type: list
    elements: str
  period_in_seconds:
    description: Collect every this many seconds, as an alternative to O(times).
    type: int
  time_zone:
    description: IANA time zone for O(times), for example C(America/Los_Angeles).
    type: str
  start_at:
    description: Earliest time the schedule applies, as an ISO 8601 string.
    type: str
  end_at:
    description: Latest time the schedule applies, as an ISO 8601 string.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Collect nightly at 02:00 Pacific
  forwardnetworks.forward.fwd_collection_schedule:
    network_id: "101"
    times: ["02:00"]
    time_zone: America/Los_Angeles
"""

RETURN = r"""
schedule:
  description: The schedule as Forward returns it. Absent after C(absent).
  type: dict
  returned: when present
schedule_id:
  description: ID of the schedule.
  type: str
  returned: when a schedule exists or was deleted
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

FIELDS = {
    "enabled": "enabled",
    "days_of_the_week": "daysOfTheWeek",
    "times": "times",
    "period_in_seconds": "periodInSeconds",
    "time_zone": "timeZone",
    "start_at": "startAt",
    "end_at": "endAt",
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
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "schedule_id": {"type": "str"},
            "enabled": {"type": "bool", "default": True},
            "days_of_the_week": {"type": "list", "elements": "int", "default": [1, 2, 3, 4, 5, 6, 7]},
            "times": {"type": "list", "elements": "str"},
            "period_in_seconds": {"type": "int"},
            "time_zone": {"type": "str"},
            "start_at": {"type": "str"},
            "end_at": {"type": "str"},
        },
        required_if=[("state", "absent", ("schedule_id",))],
        mutually_exclusive=[("times", "period_in_seconds")],
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    nid = p["network_id"]
    try:
        existing = sdk.to_plain(client.collection_schedules.get_collection_schedules(network_id=nid)).get("schedules") or []
        match = None
        if p["schedule_id"]:
            match = next((s for s in existing if s.get("id") == p["schedule_id"]), None)

        if p["state"] == "absent":
            if match is None:
                module.exit_json(changed=False)
            if not module.check_mode:
                client.collection_schedules.delete_collection_schedule(schedule_id=match["id"], network_id=nid)
            module.exit_json(changed=True, schedule_id=match["id"])

        wanted = {api: p[opt] for opt, api in FIELDS.items() if p[opt] is not None}
        if p["schedule_id"] and match is None:
            module.fail_json(msg="no schedule with id %s; omit schedule_id to create one" % p["schedule_id"])

        def same(schedule):
            return all(schedule.get(k) == v for k, v in wanted.items())

        if match is None:
            match = next((s for s in existing if same(s)), None)
            if match is not None:
                module.exit_json(changed=False, schedule=match, schedule_id=match["id"])
            if module.check_mode:
                module.exit_json(changed=True)
            created = client.collection_schedules.add_collection_schedule(body=wanted, network_id=nid)
            module.exit_json(changed=True, schedule=sdk.to_plain(created), schedule_id=created.id)
        if same(match):
            module.exit_json(changed=False, schedule=match, schedule_id=match["id"])
        if module.check_mode:
            module.exit_json(changed=True, schedule=match, schedule_id=match["id"])
        client.collection_schedules.replace_collection_schedule(schedule_id=match["id"], body=wanted, network_id=nid)
        fresh = sdk.to_plain(client.collection_schedules.get_collection_schedule(schedule_id=match["id"], network_id=nid))
        module.exit_json(changed=True, schedule=fresh, schedule_id=match["id"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()


if __name__ == "__main__":
    main()
