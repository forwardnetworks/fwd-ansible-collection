#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_device_tag
short_description: Manage Forward Networks device tags and which devices carry them
description:
  - Ensures a device tag exists and is applied to the given devices (C(present)), or removes it from them or deletes it (C(absent)).
  - Idempotent. Reports C(changed) only when the tag or its membership actually changes.
  - Device names match exactly (case-sensitive), unlike tag names.
  - With C(present), O(devices) are added to the tag; devices already on it are left alone and others on the tag are not removed unless O(exclusive=true).
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  name:
    description: Tag name (case-insensitive).
    type: str
    required: true
  state:
    description:
      - C(present) creates the tag if needed and adds O(devices).
      - C(absent) removes O(devices) from the tag, or deletes the whole tag when O(devices) is not given.
    type: str
    choices: [present, absent]
    default: present
  devices:
    description: Device names to add to, or remove from, the tag.
    type: list
    elements: str
  exclusive:
    description: With C(present), also remove the tag from devices not in O(devices). Requires O(devices), since an empty list would strip every device.
    type: bool
    default: false
  color:
    description: Tag color as RGB hex, such as C(#0064a0), when creating the tag.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Tag the core routers
  forwardnetworks.forward.fwd_device_tag:
    network_id: "101"
    name: core
    devices: [core-1, core-2]

- name: Delete the tag
  forwardnetworks.forward.fwd_device_tag:
    network_id: "101"
    name: core
    state: absent
"""

RETURN = r"""
added:
  description: Devices the tag was added to.
  type: list
  elements: str
  returned: success
removed:
  description: Devices the tag was removed from.
  type: list
  elements: str
  returned: success
tag:
  description: The tag and its devices after the change. Absent when the tag was deleted.
  type: dict
  returned: when the tag exists
"""

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
            "name": {"type": "str", "required": True},
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "devices": {"type": "list", "elements": "str"},
            "exclusive": {"type": "bool", "default": False},
            "color": {"type": "str"},
        },
        required_if=[("exclusive", True, ("devices",))],
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    nid, name = p["network_id"], p["name"]
    added, removed = [], []
    try:
        existing = None
        for tag in client.device_tags.list(nid, with_devices=True):
            if str(tag.get("name", "")).lower() == name.lower():
                existing = tag
                break
        if existing:
            name = existing["name"]  # Forward's own spelling; matching is case-insensitive
        current = set(existing.get("devices") or []) if existing else set()
        wanted = list(dict.fromkeys(p["devices"] or []))  # drop duplicates, keep order

        if p["state"] == "absent":
            if existing is None:
                module.exit_json(changed=False, added=[], removed=[])
            if p["devices"] is None:
                if not module.check_mode:
                    client.device_tags.delete(name, network_id=nid)
                module.exit_json(changed=True, added=[], removed=sorted(current))
            removed = [d for d in wanted if d in current]
            if removed and not module.check_mode:
                client.device_tags.remove_from_devices(name, removed, network_id=nid)
            module.exit_json(changed=bool(removed), added=[], removed=removed)

        created = existing is None
        if created and not module.check_mode:
            body = {"name": name}
            if p["color"]:
                body["color"] = p["color"]
            client.device_tags.create(body, network_id=nid)
        added = [d for d in wanted if d not in current]
        if p["exclusive"]:
            removed = sorted(current - set(wanted))
        if not module.check_mode:
            if added:
                client.device_tags.add_to_devices(name, added, network_id=nid)
            if removed:
                client.device_tags.remove_from_devices(name, removed, network_id=nid)
        tag = {"name": name, "devices": sorted((current | set(added)) - set(removed))}
        module.exit_json(changed=bool(created or added or removed), added=added, removed=removed, tag=tag)
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()


if __name__ == "__main__":
    main()
