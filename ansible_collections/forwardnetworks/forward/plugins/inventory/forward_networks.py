# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: forward_networks
short_description: Forward Networks dynamic inventory
description:
  - Builds inventory from the devices Forward Networks has collected for a network snapshot, using C(forward-sdk).
  - Every device field Forward returns becomes a host variable.
  - Needs the C(forward-sdk) Python package on the Ansible controller.
author:
  - Forward Networks (@forwardnetworks)
requirements:
  - forward-sdk (Python 3.10 or newer)
options:
  plugin:
    description: Token that ensures this is a source file for the plugin.
    required: true
    choices: ['forwardnetworks.forward.forward_networks']
    type: str
  base_url:
    description: Base URL of the Forward instance. Falls back to E(FORWARD_URL) (aliases E(FORWARD_BASE_URL), E(FWD_HOST)).
    type: str
  username:
    description: API token access key. Falls back to E(FORWARD_USERNAME) (alias E(FWD_USER)).
    type: str
  password:
    description: API token secret. Falls back to E(FORWARD_PASSWORD) (alias E(FWD_PASS)).
    type: str
  validate_certs:
    description: Whether to validate TLS certificates. Falls back to E(FORWARD_VERIFY_TLS), then C(true).
    type: bool
  timeout:
    description: Read timeout in seconds. Falls back to E(FORWARD_TIMEOUT).
    type: float
  network_id:
    description: Forward network ID. Falls back to E(FORWARD_NETWORK_ID) (alias E(FWD_NETWORKID)).
    type: str
  snapshot_id:
    description: Snapshot ID. Defaults to the network's latest processed snapshot.
    type: str
  host_key:
    description: Key in each device used as the inventory hostname.
    type: str
    default: name
  include_tags:
    description: Include each device's tags in its host variables.
    type: bool
    default: false
  filters:
    description:
      - Device filters, keyed by the same names as M(forwardnetworks.forward.fwd_devices) (C(name), C(vendor), C(device_type), C(platform),
        C(os_version) and so on).
    type: dict
  extra_params:
    description: Additional device filter parameters passed to the API unchanged.
    type: dict
extends_documentation_fragment:
  - constructed
  - inventory_cache
"""

EXAMPLES = r"""
plugin: forwardnetworks.forward.forward_networks
network_id: "205507"
filters:
  name: "core-*"
include_tags: true
keyed_groups:
  - key: vendor
    prefix: vendor
"""

import os

from ansible.errors import AnsibleError
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk
from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import build_device_filters


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "forwardnetworks.forward.forward_networks"

    def verify_file(self, path):
        valid = super(InventoryModule, self).verify_file(path)
        if not valid:
            return False
        return path.endswith((".forward.yml", ".forward.yaml", "forward.yml", "forward.yaml"))

    def _fetch_devices(self):
        if not sdk.HAS_SDK:
            raise AnsibleError("The forward_networks inventory plugin needs the forward-sdk Python package: pip install forward-sdk")
        params = {name: self.get_option(name) for name in ("base_url", "username", "password", "validate_certs", "timeout", "network_id", "snapshot_id")}
        if not params["network_id"]:
            params["network_id"] = os.environ.get("FWD_NETWORKID")  # legacy name; FORWARD_NETWORK_ID is read by the SDK
        try:
            client = sdk.build_client(params)
        except sdk.ForwardError as exc:
            raise AnsibleError(sdk.error_message(exc))
        filters = build_device_filters(self.get_option("filters") or {}, self.get_option("extra_params"))
        with_ = ["tags"] if self.get_option("include_tags") else None
        try:
            devices = list(client.devices.iter(snapshot_id=params["snapshot_id"], with_=with_, **filters))
        except sdk.ForwardError as exc:
            raise AnsibleError(sdk.error_message(exc))
        finally:
            client.close()
        return sdk.to_plain(devices)

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache=cache)
        self._read_config_data(path)

        cache_key = self.get_cache_key(path)
        use_cache = cache and self.get_option("cache")
        devices = self._cache.get(cache_key) if use_cache else None
        if devices is None:
            devices = self._fetch_devices()
            if use_cache:
                self._cache[cache_key] = devices

        host_key = self.get_option("host_key")
        hostvars_by_host = {}
        for device in devices:
            name = device.get(host_key)
            if not name:
                continue
            self.inventory.add_host(name)
            for key, value in device.items():
                self.inventory.set_variable(name, key, value)
            hostvars_by_host[name] = device

        compose = self.get_option("compose")
        groups = self.get_option("groups")
        keyed_groups = self.get_option("keyed_groups")
        strict = self.get_option("strict")
        for host, hostvars in hostvars_by_host.items():
            self._set_composite_vars(compose, hostvars, host, strict)
            self._add_host_to_composed_groups(groups, hostvars, host, strict)
            self._add_host_to_keyed_groups(keyed_groups, hostvars, host, strict)
