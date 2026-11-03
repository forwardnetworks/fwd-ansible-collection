from ansible_collections.forwardnetworks.forward.plugins.module_utils.path_search import (
    build_bulk_body,
    build_query_entry,
    validate_query,
)


def test_query_entry_uses_api_names():
    entry = build_query_entry({"from_device": "edge1", "dst_ip": "10.0.0.1", "ip_proto": 6, "dst_port": "443"})
    assert entry == {"from": "edge1", "dstIp": "10.0.0.1", "ipProto": 6, "dstPort": "443"}


def test_bulk_body_is_an_object_with_queries_and_shared_settings():
    body = build_bulk_body(
        [{"src_ip": "10.1.1.1", "dst_ip": "10.2.2.2"}],
        {"intent": "PREFER_VIOLATIONS", "max_results": 3, "include_tags": None},
    )
    assert body == {
        "queries": [{"srcIp": "10.1.1.1", "dstIp": "10.2.2.2"}],
        "intent": "PREFER_VIOLATIONS",
        "maxResults": 3,
    }


def test_validate_query():
    assert validate_query({"dst_ip": "1.1.1.1", "src_ip": "2.2.2.2"}, 0) is None
    assert "dst_ip" in validate_query({"src_ip": "2.2.2.2"}, 1)
    assert "from_device or src_ip" in validate_query({"dst_ip": "1.1.1.1"}, 2)
    assert "bogus" in validate_query({"dst_ip": "1.1.1.1", "src_ip": "2.2.2.2", "bogus": 1}, 3)


def test_name_is_an_allowed_label_and_not_sent():
    query = {"name": "dmz", "src_ip": "1.1.1.1", "dst_ip": "2.2.2.2"}
    assert validate_query(query, 0) is None
    assert build_query_entry(query) == {"srcIp": "1.1.1.1", "dstIp": "2.2.2.2"}
