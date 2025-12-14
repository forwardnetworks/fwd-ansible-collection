from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import (
    build_device_query,
)


def test_build_device_query_basic():
    params = {
        "name": "core-*",
        "vendor": "cisco",
        "skip": 5,
        "limit": 10,
        "snapshot_id": "snap-1",
        "include_tags": True,
    }
    query = build_device_query(params)
    assert query["name"] == "core-*"
    assert query["vendor"] == "cisco"
    assert query["skip"] == 5
    assert query["limit"] == 10
    assert query["snapshotId"] == "snap-1"
    assert query["with"] == "tags"


def test_build_device_query_extra_params():
    params = {"name": "core-*"}
    query = build_device_query(params, extra_params={"custom": "value"})
    assert query["custom"] == "value"
