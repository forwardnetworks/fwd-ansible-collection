#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_webhook
short_description: Create, update or delete a Forward Networks webhook
description:
  - Ensures a webhook with the given O(name) exists with the given settings, or is gone.
  - Webhooks are organization-wide, not per network. Only the options you set are compared and corrected.
  - The webhook password is write-only, so it cannot be compared; see O(update_password).
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  state:
    description: Whether the webhook should exist.
    type: str
    choices: [present, absent]
    default: present
  name:
    description: Webhook name, which identifies it.
    type: str
    required: true
  url:
    description: URL Forward calls. Required when creating.
    type: str
  event_type:
    description: Event that triggers the webhook. Required when creating.
    type: str
    choices: [SNAPSHOT_READY, NQE_VERIFICATION_FAILURE, INTENT_VERIFICATION_FAILURE]
  network_ids:
    description: Only fire for these networks. Empty or omitted means all.
    type: list
    elements: str
  enabled:
    description: Whether the webhook fires.
    type: bool
  description:
    description: Free-text description.
    type: str
  disable_ssl_validation:
    description: Skip TLS certificate validation when calling the URL.
    type: bool
  payload_format:
    description: Payload format for a custom template.
    type: str
    choices: [JSON, TEXT]
  payload_template:
    description: Custom payload template text. Omit to use Forward's default for the event.
    type: str
  auth_username:
    description: Username for HTTP basic authentication to the URL.
    type: str
  auth_password:
    description: Password for HTTP basic authentication to the URL.
    type: str
  update_password:
    description:
      - C(on_create) sends O(auth_password) only when the webhook is created or is being changed anyway.
      - C(always) sends it on every run and reports C(changed) each time, because Forward does not return it.
    type: str
    choices: [on_create, always]
    default: on_create
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Notify a chat bridge when a snapshot is ready
  forwardnetworks.forward.fwd_webhook:
    name: snapshot-ready
    url: https://hooks.example.com/forward
    event_type: SNAPSHOT_READY
    network_ids: ["101"]
"""

RETURN = r"""
webhook:
  description: The webhook as Forward returns it. Absent after C(absent).
  type: dict
  returned: when present
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk


def desired(p):
    """The webhook fields the task sets, in API shape, split into comparable and write-only parts."""
    body = {}
    for opt, api in (
        ("url", "url"),
        ("enabled", "enabled"),
        ("description", "description"),
        ("disable_ssl_validation", "disableSslValidation"),
    ):
        if p[opt] is not None:
            body[api] = p[opt]
    if p["event_type"] is not None or p["network_ids"] is not None:
        body["eventParams"] = {}
        if p["event_type"] is not None:
            body["eventParams"]["type"] = p["event_type"]
        if p["network_ids"] is not None:
            body["eventParams"]["networkIds"] = p["network_ids"]
    if p["payload_format"] is not None or p["payload_template"] is not None:
        body["template"] = {}
        if p["payload_format"] is not None:
            body["template"]["payloadFormat"] = p["payload_format"]
        if p["payload_template"] is not None:
            body["template"]["template"] = p["payload_template"]
    if p["auth_username"] is not None:
        body["credential"] = {"type": "BASIC_AUTH", "username": p["auth_username"]}
    return body


def differs(wanted, have):
    """Whether any wanted field (recursively) is not what the webhook already has."""
    for key, value in wanted.items():
        if isinstance(value, dict):
            if differs(value, have.get(key) or {}):
                return True
        elif have.get(key) != value:
            return True
    return False


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "name": {"type": "str", "required": True},
            "url": {"type": "str"},
            "event_type": {"type": "str", "choices": ["SNAPSHOT_READY", "NQE_VERIFICATION_FAILURE", "INTENT_VERIFICATION_FAILURE"]},
            "network_ids": {"type": "list", "elements": "str"},
            "enabled": {"type": "bool"},
            "description": {"type": "str"},
            "disable_ssl_validation": {"type": "bool"},
            "payload_format": {"type": "str", "choices": ["JSON", "TEXT"]},
            "payload_template": {"type": "str"},
            "auth_username": {"type": "str"},
            "auth_password": {"type": "str", "no_log": True},
            "update_password": {"type": "str", "choices": ["on_create", "always"], "default": "on_create", "no_log": False},
        },
        required_by={"auth_password": "auth_username"},
        supports_check_mode=True,
    )
    p = module.params
    client = sdk.get_client(module)
    try:
        webhooks = sdk.to_plain(client.webhooks.list_webhooks()).get("webhooks") or []
        match = next((w for w in webhooks if w.get("name") == p["name"]), None)

        if p["state"] == "absent":
            if match is None:
                module.exit_json(changed=False)
            if not module.check_mode:
                client.webhooks.delete_webhook(webhook_name=p["name"])
            module.exit_json(changed=True)

        wanted = desired(p)
        if match is None:
            if p["url"] is None or p["event_type"] is None:
                module.fail_json(msg="url and event_type are required to create a webhook")
            if module.check_mode:
                module.exit_json(changed=True)
            body = dict(wanted, name=p["name"])
            if p["auth_password"] is not None:
                body["credential"]["password"] = p["auth_password"]
            client.webhooks.create_webhook(body=body)
            module.exit_json(changed=True, webhook=_fetch(client, p["name"]))

        stale = differs(wanted, match)
        send_password = p["auth_password"] is not None and (stale or p["update_password"] == "always")
        if not stale and not send_password:
            module.exit_json(changed=False, webhook=match)
        if module.check_mode:
            module.exit_json(changed=True, webhook=match)
        body = wanted
        if send_password:
            body = dict(wanted, credential=dict(wanted.get("credential", {}), password=p["auth_password"]))
        client.webhooks.update_webhook(webhook_name=p["name"], body=body)
        module.exit_json(changed=True, webhook=_fetch(client, p["name"]))
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()


def _fetch(client, name):
    webhooks = sdk.to_plain(client.webhooks.list_webhooks()).get("webhooks") or []
    return next((w for w in webhooks if w.get("name") == name), None)


if __name__ == "__main__":
    main()
