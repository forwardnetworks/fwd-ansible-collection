#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_location
short_description: Create, update or delete a Forward Networks location
description:
  - Ensures a location (a named place on the map that devices can be assigned to) exists with the given coordinates, or is gone.
  - Idempotent by O(name), or by O(location_id) when given. Only the options you set are compared and corrected.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  network_id:
    description: Network ID. Falls back to C(FORWARD_NETWORK_ID).
    type: str
  state:
    description: Whether the location should exist.
    type: str
    choices: [present, absent]
    default: present
  name:
    description: Location name. Required for C(present).
    type: str
  location_id:
    description: Location ID, to select an existing location by ID (for example to rename it).
    type: str
  lat:
    description: Latitude. Required when creating.
    type: float
  lng:
    description: Longitude. Required when creating.
    type: float
  city:
    description: City.
    type: str
  country:
    description: Country.
    type: str
  admin_division:
    description: State, province or similar.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Add a data center location
  forwardnetworks.forward.fwd_location:
    network_id: "101"
    name: SJC1
    lat: 37.3382
    lng: -121.8863
    city: San Jose
    country: US
"""

RETURN = r"""
location:
  description: The location as Forward returns it. Absent after C(absent).
  type: dict
  returned: when present
location_id:
  description: ID of the location.
  type: str
  returned: when a location exists or was deleted
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

FIELDS = {"lat": "lat", "lng": "lng", "city": "city", "country": "country", "admin_division": "adminDivision"}


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
            "name": {"type": "str"},
            "location_id": {"type": "str"},
            "lat": {"type": "float"},
            "lng": {"type": "float"},
            "city": {"type": "str"},
            "country": {"type": "str"},
            "admin_division": {"type": "str"},
        },
        required_if=[("state", "present", ("name",))],
        required_one_of=[("name", "location_id")],
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    nid = p["network_id"]
    try:
        locations = sdk.to_plain(client.network_locations.get_locations(network_id=nid))
        if p["location_id"]:
            match = next((x for x in locations if x.get("id") == p["location_id"]), None)
        else:
            match = next((x for x in locations if x.get("name") == p["name"]), None)

        if p["state"] == "absent":
            if match is None:
                module.exit_json(changed=False)
            if not module.check_mode:
                client.network_locations.delete_location(location_id=match["id"], network_id=nid)
            module.exit_json(changed=True, location_id=match["id"])

        wanted = {api: p[opt] for opt, api in FIELDS.items() if p[opt] is not None}
        if match is None:
            if p["location_id"]:
                module.fail_json(msg="no location with id %s; omit location_id to create one by name" % p["location_id"])
            if p["lat"] is None or p["lng"] is None:
                module.fail_json(msg="lat and lng are required to create a location")
            if module.check_mode:
                module.exit_json(changed=True)
            created = client.network_locations.add_location(body=dict(wanted, name=p["name"]), network_id=nid)
            module.exit_json(changed=True, location=sdk.to_plain(created), location_id=created.id)
        if p["name"] is not None:
            wanted["name"] = p["name"]
        diff = {k: v for k, v in wanted.items() if match.get(k) != v}
        if not diff:
            module.exit_json(changed=False, location=match, location_id=match["id"])
        if module.check_mode:
            module.exit_json(changed=True, location=match, location_id=match["id"])
        updated = client.network_locations.patch_location(location_id=match["id"], body=diff, network_id=nid)
        module.exit_json(changed=True, location=sdk.to_plain(updated), location_id=match["id"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()


if __name__ == "__main__":
    main()
