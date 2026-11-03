#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_networks
short_description: List Forward Networks networks
description:
  - Lists the networks the credentials can see, optionally only those with a given name.
  - Use M(forwardnetworks.forward.fwd_network) to create or delete one.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  name:
    description: Only networks with exactly this name.
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Find the production network's ID
  forwardnetworks.forward.fwd_networks:
    name: production
  register: found

- ansible.builtin.set_fact:
    network_id: "{{ found.networks[0].id }}"
"""

RETURN = r"""
networks:
  description: Networks as Forward returns them.
  type: list
  elements: dict
  returned: success
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
            "name": {"type": "str"},
        },
        supports_check_mode=True,
    )
    client = sdk.get_client(module)
    try:
        networks = sdk.to_plain(client.networks.list())
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    if module.params["name"]:
        networks = [n for n in networks if n.get("name") == module.params["name"]]
    module.exit_json(changed=False, networks=networks)


if __name__ == "__main__":
    main()
