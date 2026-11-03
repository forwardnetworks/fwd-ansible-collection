#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_api
short_description: Call any Forward Networks API operation by its operation ID
description:
  - A generic escape hatch for operations that have no dedicated module, using C(forward-sdk)'s C(client.call).
  - Name an operation by its Forward operation ID (for example C(getNetworks), C(getChecks), C(getLocations)) and pass its arguments in the SDK's
    snake_case names, plus C(body) for a request body.
  - O(network_id) and O(snapshot_id) fill in the operation's network and snapshot arguments when not given in O(arguments).
  - An unknown operation ID fails with the nearest names. Streaming operations (downloads) are refused; use M(forwardnetworks.forward.fwd_snapshot_export).
  - In check mode only read operations (IDs starting with C(get), C(list), C(find) or C(search)) run.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  operation:
    description: Forward operation ID, such as C(getNetworks).
    type: str
    required: true
  arguments:
    description: Keyword arguments for the operation, using snake_case names (C(snapshot_id), C(check_id)), and C(body) for a request body.
    type: dict
    default: {}
  network_id:
    description: Default network for the operation. Falls back to E(FORWARD_NETWORK_ID).
    type: str
  snapshot_id:
    description: Default snapshot for the operation. Falls back to E(FORWARD_SNAPSHOT_ID).
    type: str
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: List networks
  forwardnetworks.forward.fwd_api:
    operation: getNetworks
  register: networks

- name: Read a snapshot's failing checks
  forwardnetworks.forward.fwd_api:
    operation: getChecks
    arguments:
      snapshot_id: "1234"
      status: [FAIL]
"""

RETURN = r"""
result:
  description: Whatever the operation returned, as decoded JSON, text, or null.
  type: raw
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk

READ_PREFIXES = ("get", "list", "find", "search")


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "operation": {"type": "str", "required": True},
            "arguments": {"type": "dict", "default": {}},
            "network_id": {"type": "str"},
            "snapshot_id": {"type": "str"},
        },
        supports_check_mode=True,
    )
    p = module.params
    is_read = p["operation"].startswith(READ_PREFIXES)
    if module.check_mode and not is_read:
        module.exit_json(changed=True, msg="check_mode: %s not run" % p["operation"])

    client = sdk.get_client(module)
    try:
        result = client.call(p["operation"], **p["arguments"])
    except TypeError as exc:
        module.fail_json(msg="Bad arguments for %s: %s" % (p["operation"], exc))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    module.exit_json(changed=not is_read, result=sdk.to_plain(result))


if __name__ == "__main__":
    main()
