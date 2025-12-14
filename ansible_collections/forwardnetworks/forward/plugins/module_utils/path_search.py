from __future__ import annotations

PATH_OPTION_TO_QUERY = {
    "from_device": "from",
    "src_ip": "srcIp",
    "dst_ip": "dstIp",
    "intent": "intent",
    "ip_proto": "ipProto",
    "src_port": "srcPort",
    "dst_port": "dstPort",
    "icmp_type": "icmpType",
    "fin": "fin",
    "syn": "syn",
    "rst": "rst",
    "psh": "psh",
    "ack": "ack",
    "urg": "urg",
    "app_id": "appId",
    "user_id": "userId",
    "user_group_id": "userGroupId",
    "url": "url",
    "include_tags": "includeTags",
    "include_network_functions": "includeNetworkFunctions",
    "max_candidates": "maxCandidates",
    "max_results": "maxResults",
    "max_return_path_results": "maxReturnPathResults",
    "max_seconds": "maxSeconds",
}


def build_path_query(params: dict, extra_params: dict | None = None, include_snapshot: bool = True) -> dict:
    """
    Build query parameters for Forward path search endpoints.

    :param params: module params containing snake_case options.
    :param extra_params: dict of additional query parameters to merge (strings only).
    :param include_snapshot: whether to include snapshot_id in the result.
    """
    query = {}

    for option, api_field in PATH_OPTION_TO_QUERY.items():
        value = params.get(option)
        if value is None:
            continue
        query[api_field] = value

    if include_snapshot and params.get("snapshot_id"):
        query["snapshotId"] = params["snapshot_id"]

    extra = extra_params or params.get("extra_params") or {}
    for key, value in extra.items():
        query[key] = value

    return query
