# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Helpers for building the body of Forward's bulk path search (``PathSearchBulkRequest``)."""
from __future__ import annotations

# Fields of a single query inside ``queries`` (``PathSearchQuery``): snake_case option -> API name.
QUERY_FIELDS = {
    "from_device": "from",
    "src_ip": "srcIp",
    "dst_ip": "dstIp",
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
}

# Settings that apply to the whole request and sit beside ``queries``.
SHARED_FIELDS = {
    "intent": "intent",
    "include_tags": "includeTags",
    "include_network_functions": "includeNetworkFunctions",
    "max_candidates": "maxCandidates",
    "max_results": "maxResults",
    "max_return_path_results": "maxReturnPathResults",
    "max_seconds": "maxSeconds",
}


def build_query_entry(query):
    """Convert one query's snake_case options into a ``PathSearchQuery`` dict."""
    return {api: query[option] for option, api in QUERY_FIELDS.items() if query.get(option) is not None}


def validate_query(query, index):
    """Return an error message for an unusable query entry, or ``None``.

    A ``name`` key is allowed as a label for the caller and is not sent to Forward.
    """
    if not query.get("dst_ip"):
        return "queries[%d]: dst_ip is required" % index
    if not (query.get("from_device") or query.get("src_ip")):
        return "queries[%d]: either from_device or src_ip is required" % index
    unknown = sorted(set(query) - set(QUERY_FIELDS) - {"name"})
    if unknown:
        return "queries[%d]: unknown option(s): %s" % (index, ", ".join(unknown))
    return None


def build_bulk_body(queries, shared):
    """Build a ``PathSearchBulkRequest`` from per-query options and shared settings."""
    body = {"queries": [build_query_entry(q) for q in queries]}
    for option, api in SHARED_FIELDS.items():
        value = shared.get(option)
        if value is not None:
            body[api] = value
    return body
