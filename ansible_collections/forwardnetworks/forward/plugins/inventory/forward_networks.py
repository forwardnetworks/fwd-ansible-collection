# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: forward_networks
short_description: Forward Networks dynamic inventory (scaffold)
description:
  - Build Ansible inventory from the Forward Networks device inventory API.
  - This is a scaffold; set C(devices_path) and optionally C(items_key) to match your Forward API response.
author:
  - Forward Networks (@forwardnetworks)
options:
  plugin:
    description: Token that ensures this is a source file for the plugin.
    required: true
    choices: ['forwardnetworks.forward.forward_networks']
    type: str
  base_url:
    description:
      - Base URL for the Forward Networks instance.
      - Can also be set via C(FORWARD_BASE_URL).
    type: str
  token:
    description:
      - API token for Forward Networks.
      - Can also be set via C(FORWARD_TOKEN).
    type: str
  username:
    description:
      - Forward username (HTTP Basic).
      - Can also be set via C(FWD_USER) or C(FORWARD_USERNAME).
      - If C(token) is set, token auth is used instead.
    type: str
  password:
    description:
      - Forward password (HTTP Basic).
      - Can also be set via C(FWD_PASS) or C(FORWARD_PASSWORD).
    type: str
  validate_certs:
    description:
      - Whether to validate TLS certificates.
      - Can also be set via C(FORWARD_VALIDATE_CERTS).
    type: bool
    default: true
  timeout:
    description:
      - HTTP timeout (seconds).
      - Can also be set via C(FORWARD_TIMEOUT).
    type: int
    default: 30
  network_id:
    description: Forward network identifier.
    type: str
  network_id_env:
    description:
      - Environment variable name to read network id from if C(network_id) is not set.
    type: str
    default: FWD_NETWORKID
  snapshot_id:
    description: Optional snapshot identifier.
    type: str
  devices_path:
    description:
      - API path used to retrieve devices. You can use placeholders like C({network_id}) and C({snapshot_id}).
      - If placeholders are not used, C(network_id) and C(snapshot_id) are added as query parameters.
    type: str
    default: /api/networks/{network_id}/devices
  items_key:
    description:
      - If set, extract the device list from this key in the JSON response (e.g. C(devices)).
      - If unset, the response must be a JSON list.
    type: str
  host_key:
    description:
      - Key in each device object used as the inventory hostname.
    type: str
    default: name
  include_tags:
    description:
      - Include device tags in hostvars (uses the Forward C(with=tags) query parameter).
    type: bool
    default: false
  filters:
    description:
      - Device attribute filters (keys follow module option names, e.g. C(name), C(vendor), C(device_type)).
    type: dict
  extra_params:
    description:
      - Additional query parameters for GET /devices.
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
"""

import json
import os
from urllib.parse import urlencode

from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.forwardnetworks.forward.plugins.module_utils.client import (
    _join_url,
    build_auth_header,
    build_basic_auth_header,
)
from ansible_collections.forwardnetworks.forward.plugins.module_utils.config import get_forward_config
from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import build_device_query


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "forwardnetworks.forward.forward_networks"

    def verify_file(self, path):
        valid = super(InventoryModule, self).verify_file(path)
        if not valid:
            return False
        return path.endswith((".forward.yml", ".forward.yaml", "forward.yml", "forward.yaml"))

    def _http_get_json(self, url: str, token: str, timeout: int, validate_certs: bool):
        headers = {"Authorization": build_auth_header(token)}
        try:
            resp = open_url(url, method="GET", headers=headers, timeout=timeout, validate_certs=validate_certs)
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as e:
            raise AnsibleError(f"Forward API GET failed for {url}: {to_native(e)}")

    def _http_get_json_basic(self, url: str, username: str, password: str, timeout: int, validate_certs: bool):
        headers = {"Authorization": build_basic_auth_header(username, password)}
        try:
            resp = open_url(url, method="GET", headers=headers, timeout=timeout, validate_certs=validate_certs)
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as e:
            raise AnsibleError(f"Forward API GET failed for {url}: {to_native(e)}")

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache=cache)
        self._read_config_data(path)

        opts = {
            "base_url": self.get_option("base_url"),
            "token": self.get_option("token"),
            "username": self.get_option("username"),
            "password": self.get_option("password"),
            "validate_certs": self.get_option("validate_certs"),
            "timeout": self.get_option("timeout"),
        }
        cfg = get_forward_config(opts)
        if not (cfg["token"] or cfg["username"]):
            raise AnsibleError("token or username is required (set FORWARD_TOKEN or FWD_USER/FORWARD_USERNAME)")

        network_id = self.get_option("network_id")
        if not network_id:
            env_name = self.get_option("network_id_env")
            network_id = (env_name and os.environ.get(env_name)) or None
        snapshot_id = self.get_option("snapshot_id")
        devices_path = self.get_option("devices_path")
        host_key = self.get_option("host_key")
        items_key = self.get_option("items_key")
        include_tags = self.get_option("include_tags")

        # Cache key is the config path; allow Ansible inventory cache to work.
        cache_key = self.get_cache_key(path)
        if cache and self.get_option("cache") and (cached := self._cache.get(cache_key)) is not None:
            data = cached
        else:
            templated_path = devices_path.format(
                network_id=network_id,
                networkId=network_id,
                snapshot_id=snapshot_id or "",
                snapshotId=snapshot_id or "",
            )
            url = _join_url(cfg["base_url"], templated_path)

            filter_params = self.get_option("filters") or {}
            filter_params["snapshot_id"] = snapshot_id
            filter_params["include_tags"] = include_tags
            query_params = build_device_query(filter_params, extra_params=self.get_option("extra_params"))

            if "{network_id}" not in devices_path and "{networkId}" not in devices_path and network_id:
                query_params.setdefault("networkId", network_id)

            if query_params:
                url = f"{url}?{urlencode(query_params, doseq=True)}"

            if cfg["token"]:
                data = self._http_get_json(url, cfg["token"], cfg["timeout"], cfg["validate_certs"])
            else:
                data = self._http_get_json_basic(
                    url,
                    cfg["username"],
                    cfg["password"] or "",
                    cfg["timeout"],
                    cfg["validate_certs"],
                )
            if cache and self.get_option("cache"):
                self._cache.set(cache_key, data)

        if items_key:
            if not isinstance(data, dict) or items_key not in data:
                raise AnsibleError(f"items_key={items_key!r} not present in response")
            devices = data[items_key]
        else:
            devices = data

        if not isinstance(devices, list):
            raise AnsibleError("Device response must be a JSON list (or set items_key)")

        hostvars_by_host = {}
        for device in devices:
            if not isinstance(device, dict):
                continue
            name = device.get(host_key)
            if not name:
                continue
            self.inventory.add_host(name)
            for k, v in device.items():
                self.inventory.set_variable(name, k, v)
            hostvars_by_host[name] = device

        # Constructed inventory features (compose/groups/keyed_groups).
        compose = self.get_option("compose")
        groups = self.get_option("groups")
        keyed_groups = self.get_option("keyed_groups")
        for host, hostvars in hostvars_by_host.items():
            self._set_composite_vars(compose, hostvars, host)
            self._add_host_to_composed_groups(groups, hostvars, host)
            self._add_host_to_keyed_groups(keyed_groups, hostvars, host)
