# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Device list filters shared by the ``fwd_devices`` module and the inventory plugin."""
from __future__ import annotations

# snake_case option -> the query parameter Forward's device listing accepts.
DEVICE_FILTER_TO_PARAM = {
    "name": "name",
    "display_name": "displayName",
    "source_name": "sourceName",
    "device_type": "type",
    "vendor": "vendor",
    "model": "model",
    "platform": "platform",
    "os_version": "osVersion",
    "collection_error": "collectionError",
    "processing_error": "processingError",
}


def build_device_filters(params, extra_params=None):
    """Translate filter options into the keyword filters ``client.devices.list`` takes.

    Unset options are dropped. ``extra_params`` are passed through unchanged for
    filters this collection does not name.
    """
    filters = {api: params[option] for option, api in DEVICE_FILTER_TO_PARAM.items() if params.get(option)}
    filters.update(extra_params or {})
    return filters
