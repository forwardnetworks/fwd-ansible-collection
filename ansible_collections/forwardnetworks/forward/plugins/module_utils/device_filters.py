from __future__ import annotations

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


def build_device_query(params: dict, extra_params: dict | None = None) -> dict:
    """
    Build query parameters for /api/networks/{networkId}/devices.
    `params` should use snake_case option names (name, display_name, etc).
    """
    query = {}

    for option, api_field in DEVICE_FILTER_TO_PARAM.items():
        value = params.get(option)
        if value:
            query[api_field] = value

    # Common pagination / extras.
    for key in ("skip", "limit"):
        if params.get(key) is not None:
            query[key] = params[key]

    snapshot_id = params.get("snapshot_id") or params.get("snapshotId")
    if snapshot_id:
        query["snapshotId"] = snapshot_id

    if params.get("include_tags"):
        query["with"] = "tags"

    # Additional passthrough parameters.
    extra = extra_params or params.get("extra_params") or {}
    for key, value in extra.items():
        query[key] = value

    return query
