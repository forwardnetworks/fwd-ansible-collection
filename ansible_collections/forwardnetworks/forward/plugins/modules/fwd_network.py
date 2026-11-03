#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_network
short_description: Create or delete a Forward Networks network
description:
  - Ensures a network with the given O(name) exists (C(present)), or that the network is gone (C(absent)).
  - Idempotent by name for C(present); a note is applied or corrected when given.
  - Deleting a network deletes everything in it, including its snapshots.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  state:
    description: Whether the network should exist.
    type: str
    choices: [present, absent]
    default: present
  name:
    description: Network name. Required for C(present); with C(absent) selects the network when O(network_id) is not given.
    type: str
  network_id:
    description: Network ID, to delete a network by ID.
    type: str
  note:
    description: Note to set on the network.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Make sure a lab network exists
  forwardnetworks.forward.fwd_network:
    name: lab
    note: created by ansible
  register: lab

- name: Remove it
  forwardnetworks.forward.fwd_network:
    name: lab
    state: absent
"""

RETURN = r"""
network:
  description: The network as Forward returns it. Absent after C(absent).
  type: dict
  returned: when present
network_id:
  description: ID of the network.
  type: str
  returned: when a network exists or was deleted
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
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "name": {"type": "str"},
            "network_id": {"type": "str"},
            "note": {"type": "str"},
        },
        required_if=[("state", "present", ("name",))],
        required_one_of=[("name", "network_id")],
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    try:
        networks = sdk.to_plain(client.networks.list())
        if p["network_id"]:
            match = next((n for n in networks if n.get("id") == p["network_id"]), None)
        else:
            match = next((n for n in networks if n.get("name") == p["name"]), None)

        if p["state"] == "absent":
            if match is None:
                module.exit_json(changed=False)
            if not module.check_mode:
                client.networks.delete(match["id"])
            module.exit_json(changed=True, network_id=match["id"])

        if match is None and p["network_id"]:
            module.fail_json(msg="no network with id %s; omit network_id to create one by name" % p["network_id"])
        if match is None:
            if module.check_mode:
                module.exit_json(changed=True)
            created = client.networks.create(p["name"], note=p["note"])
            module.exit_json(changed=True, network=sdk.to_plain(created), network_id=created.id)
        if p["note"] is not None and match.get("note") != p["note"]:
            if module.check_mode:
                module.exit_json(changed=True, network=match, network_id=match["id"])
            updated = client.networks.update(match["id"], note=p["note"])
            module.exit_json(changed=True, network=sdk.to_plain(updated), network_id=match["id"])
        module.exit_json(changed=False, network=match, network_id=match["id"])
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()


if __name__ == "__main__":
    main()
