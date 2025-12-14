from ansible_collections.forwardnetworks.forward.plugins.module_utils.path_search import (
    build_path_query,
)


def test_build_path_query_basic():
    params = {
        "from_device": "edge-1",
        "dst_ip": "10.0.0.1",
        "intent": "PREFER_DELIVERED",
        "snapshot_id": "snap-1",
        "max_results": 5,
    }
    query = build_path_query(params)
    assert query["from"] == "edge-1"
    assert query["dstIp"] == "10.0.0.1"
    assert query["intent"] == "PREFER_DELIVERED"
    assert query["snapshotId"] == "snap-1"
    assert query["maxResults"] == 5


def test_build_path_query_extra_params():
    params = {"dst_ip": "10.0.0.1"}
    query = build_path_query(params, extra_params={"custom": "value"})
    assert query["custom"] == "value"
