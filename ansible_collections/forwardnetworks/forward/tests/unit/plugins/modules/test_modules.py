import httpx
import pytest

from ansible_collections.forwardnetworks.forward.plugins.modules import (
    fwd_api,
    fwd_devices,
    fwd_nqe_query,
    fwd_path_search,
    fwd_path_search_bulk,
    fwd_snapshot_checks,
    fwd_snapshot_collect,
    fwd_snapshot_export,
    fwd_snapshots,
)

pytest.importorskip("forward_sdk")


def json_response(payload, status=200):
    return httpx.Response(status, json=payload)


def device(name, **extra):
    return {"name": name, "vendor": "CISCO", **extra}


def test_devices_pages_through_every_device_with_api_filter_names(run_module, recorder):
    recorder.add("GET", "/api/networks/101/devices", json_response([device("a"), device("b")]))
    out = run_module(fwd_devices, network_id="101", os_version="17.3", include_tags=True)
    assert not out.get("failed"), out
    assert [d["name"] for d in out["devices"]] == ["a", "b"]
    assert out["count"] == 2
    query = recorder.query_for(0)
    assert query["osVersion"] == ["17.3"]
    assert query["with"] == ["tags"]


def test_devices_with_limit_returns_one_page(run_module, recorder):
    recorder.add("GET", "/api/networks/101/devices", json_response([device("a")]))
    out = run_module(fwd_devices, network_id="101", limit=1)
    assert out["count"] == 1
    assert recorder.query_for(0)["limit"] == ["1"]
    assert len(recorder.requests) == 1


def snapshot(snapshot_id, created, trigger=None, **extra):
    row = {"id": snapshot_id, "state": "PROCESSED", "createdAt": created, "processedAt": created, **extra}
    if trigger:
        row["processingTrigger"] = trigger
    return row


def test_snapshots_latest_processed_skips_predictions(run_module, recorder):
    recorder.add(
        "GET",
        "/api/networks/101/snapshots",
        json_response(
            {
                "snapshots": [
                    snapshot("pred", "2026-01-03T00:00:00Z", trigger="PREDICT"),
                    snapshot("real", "2026-01-02T00:00:00Z", trigger="COLLECTION"),
                ]
            }
        ),
    )
    out = run_module(fwd_snapshots, network_id="101", latest_processed=True)
    assert out["snapshot_id"] == "real"
    assert [s["id"] for s in out["snapshots"]] == ["real"]


def test_snapshots_latest_processed_none(run_module, recorder):
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": []}))
    out = run_module(fwd_snapshots, network_id="101", latest_processed=True)
    assert out["snapshot"] is None and out["snapshots"] == []


def test_snapshots_list_sends_camel_case_filters(run_module, recorder):
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": [snapshot("s1", "2026-01-01T00:00:00Z")]}))
    out = run_module(fwd_snapshots, network_id="101", max_collection_failure_device_pct=5.0, limit=3)
    assert [s["id"] for s in out["snapshots"]] == ["s1"]
    query = recorder.query_for(0)
    assert query["maxCollectionFailureDevicePct"] == ["5.0"]
    assert query["limit"] == ["3"]


def test_path_search_requires_a_source(run_module):
    out = run_module(fwd_path_search, network_id="101", dst_ip="10.0.0.1")
    assert out["failed"] and "from_device" in out["msg"]


def test_path_search_maps_options(run_module, recorder):
    recorder.add("GET", "/api/networks/101/paths", json_response({"paths": [{"forwardingOutcome": "DELIVERED"}]}))
    out = run_module(fwd_path_search, network_id="101", src_ip="10.1.1.1", dst_ip="10.2.2.2", ip_proto=6, dst_port="443")
    assert out["paths"] == [{"forwardingOutcome": "DELIVERED"}]
    query = recorder.query_for(0)
    assert query["srcIp"] == ["10.1.1.1"] and query["dstIp"] == ["10.2.2.2"]
    assert query["ipProto"] == ["6"] and query["dstPort"] == ["443"]


def test_bulk_posts_a_request_object_not_a_bare_list(run_module, recorder):
    recorder.add("POST", "/api/networks/101/paths-bulk", json_response([{"paths": []}, {"paths": []}]))
    out = run_module(
        fwd_path_search_bulk,
        network_id="101",
        intent="PREFER_VIOLATIONS",
        queries=[{"src_ip": "10.1.1.1", "dst_ip": "10.2.2.2"}, {"from_device": "edge1", "dst_ip": "8.8.8.8"}],
    )
    assert len(out["results"]) == 2
    assert recorder.body_for(0) == {
        "queries": [{"srcIp": "10.1.1.1", "dstIp": "10.2.2.2"}, {"from": "edge1", "dstIp": "8.8.8.8"}],
        "intent": "PREFER_VIOLATIONS",
    }


def test_bulk_rejects_a_bad_query_before_calling_forward(run_module, recorder):
    out = run_module(fwd_path_search_bulk, network_id="101", queries=[{"dst_ip": "8.8.8.8"}])
    assert out["failed"] and "queries[0]" in out["msg"]
    assert recorder.requests == []


NQE = "/api/networks/101/nqe-executions"
NQE_DONE = {"status": "COMPLETED", "outcome": "OK", "rowsProduced": 2}


def script_nqe(recorder, rows):
    recorder.add("POST", NQE, json_response({"executionKey": "e1"}))
    recorder.add("GET", NQE + "/e1", json_response(NQE_DONE))
    recorder.add("GET", NQE + "/e1/result", json_response({"items": rows}))


def test_nqe_inline_query_returns_every_row(run_module, recorder):
    script_nqe(recorder, [{"name": "a"}, {"name": "b"}])
    out = run_module(fwd_nqe_query, network_id="101", snapshot_id="9", query="foreach d in network.devices select {name: d.name}")
    assert not out.get("failed"), out
    assert out["rows"] == [{"name": "a"}, {"name": "b"}] and out["count"] == 2
    submitted = recorder.body_for(0)
    assert "foreach d in network.devices" in submitted["query"]
    assert recorder.query_for(0)["snapshotId"] == ["9"]


def test_nqe_committed_query_sends_id_and_parameters(run_module, recorder):
    script_nqe(recorder, [])
    out = run_module(fwd_nqe_query, network_id="101", query_id="FQ_abc", parameters={"min_speed": 10})
    assert not out.get("failed"), out
    submitted = recorder.body_for(0)
    assert submitted["queryId"] == "FQ_abc"
    assert submitted["parameters"] == {"min_speed": 10}


def test_nqe_requires_exactly_one_query_form(run_module):
    out = run_module(fwd_nqe_query, network_id="101")
    assert out["failed"] and "one of" in out["msg"]
    out = run_module(fwd_nqe_query, network_id="101", query="q", query_id="FQ_abc")
    assert out["failed"] and "mutually exclusive" in out["msg"]


def test_nqe_failed_execution_fails_the_task_with_the_outcome(run_module, recorder):
    recorder.add("POST", NQE, json_response({"executionKey": "e1"}))
    recorder.add("GET", NQE + "/e1", json_response({"status": "COMPLETED", "outcome": "TIMED_OUT", "error": {"message": "too slow"}}))
    out = run_module(fwd_nqe_query, network_id="101", query="q")
    assert out["failed"]
    assert "TIMED_OUT" in out["msg"] and "too slow" in out["msg"]


def test_checks_filters_and_returns_results(run_module, recorder):
    recorder.add("GET", "/api/snapshots/9/checks", json_response([{"id": "c1", "status": "FAIL"}]))
    out = run_module(fwd_snapshot_checks, snapshot_id="9", priority=["HIGH"], status=["FAIL", "ERROR"])
    assert out["checks"] == [{"id": "c1", "status": "FAIL"}]
    query = recorder.query_for(0)
    assert query["priority"] == ["HIGH"] and query["status"] == ["FAIL", "ERROR"]


def test_checks_by_id_cannot_combine_with_filters(run_module):
    out = run_module(fwd_snapshot_checks, snapshot_id="9", check_id="c1", status=["FAIL"])
    assert out["failed"] and "mutually exclusive" in out["msg"]


def test_export_writes_the_archive_atomically(run_module, recorder, tmp_path):
    recorder.add("GET", "/api/snapshots/9", httpx.Response(200, content=b"PK-archive"))
    dest = tmp_path / "snap.zip"
    out = run_module(fwd_snapshot_export, snapshot_id="9", dest=str(dest))
    assert not out.get("failed"), out
    assert out["changed"] is True and dest.read_bytes() == b"PK-archive"
    assert [p.name for p in tmp_path.iterdir()] == ["snap.zip"]  # no temp file left behind


def test_export_leaves_an_existing_file_when_not_forced(run_module, recorder, tmp_path):
    dest = tmp_path / "snap.zip"
    dest.write_bytes(b"old")
    out = run_module(fwd_snapshot_export, snapshot_id="9", dest=str(dest), force=False)
    assert out["changed"] is False and dest.read_bytes() == b"old"
    assert recorder.requests == []


def test_export_failure_leaves_no_partial_file(run_module, recorder, tmp_path):
    recorder.add("GET", "/api/snapshots/9", json_response({"message": "no such snapshot"}, status=404))
    out = run_module(fwd_snapshot_export, snapshot_id="9", dest=str(tmp_path / "snap.zip"))
    assert out["failed"]
    assert list(tmp_path.iterdir()) == []


def test_collect_waits_for_the_snapshot_to_process(run_module, recorder):
    recorder.add("POST", "/api/collector-tasks", json_response({"taskId": "t1"}))
    recorder.add("GET", "/api/collector-tasks/t1", json_response({"taskId": "t1", "status": "SUCCEEDED"}))
    recorder.add(
        "GET",
        "/api/networks/101/snapshots",
        json_response({"snapshots": [snapshot("s1", "2026-01-01T00:00:00Z", trigger="COLLECTION")]}),  # before
        json_response(
            {
                "snapshots": [
                    snapshot("s2", "2026-02-01T00:00:00Z", trigger="COLLECTION"),
                    snapshot("s1", "2026-01-01T00:00:00Z", trigger="COLLECTION"),
                ]
            }
        ),
    )
    out = run_module(fwd_snapshot_collect, network_id="101", wait_interval=1)
    assert not out.get("failed"), out
    assert out["changed"] is True and out["task_id"] == "t1" and out["snapshot_id"] == "s2"
    assert out["snapshot"]["state"] == "PROCESSED"


def test_collect_without_wait_returns_after_queueing(run_module, recorder):
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": []}))
    recorder.add("POST", "/api/collector-tasks", json_response({"taskId": "t1"}))
    out = run_module(fwd_snapshot_collect, network_id="101", wait=False)
    assert out["status"] == "QUEUED" and "snapshot_id" not in out
    assert recorder.count("POST", "/api/collector-tasks") == 1


def test_collect_check_mode_does_nothing(run_module, recorder):
    out = run_module(fwd_snapshot_collect, network_id="101", _ansible_check_mode=True)
    assert out["changed"] is True and recorder.requests == []


def test_api_runs_an_operation_by_id(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([{"id": "101", "name": "prod", "orgId": "o1"}]))
    out = run_module(fwd_api, operation="getNetworks")
    assert not out.get("failed"), out
    assert out["changed"] is False
    assert out["result"][0]["id"] == "101"


def test_api_fills_in_the_network_and_passes_arguments(run_module, recorder):
    recorder.add("GET", "/api/snapshots/9/checks", json_response([{"id": "c1"}]))
    out = run_module(fwd_api, operation="getChecks", arguments={"snapshot_id": "9", "status": ["FAIL"]})
    assert out["result"] == [{"id": "c1"}]
    assert recorder.query_for(0)["status"] == ["FAIL"]


def test_api_unknown_operation_and_bad_arguments_fail_cleanly(run_module):
    out = run_module(fwd_api, operation="getNetwrks")
    assert out["failed"] and "getNetworks" in out["msg"]  # the SDK suggests the nearest name
    out = run_module(fwd_api, operation="getNetworks", arguments={"bogus": 1})
    assert out["failed"] and "Bad arguments" in out["msg"]


def test_api_check_mode_skips_writes_but_runs_reads(run_module, recorder):
    out = run_module(fwd_api, operation="deleteChangeSet", arguments={"change_set_id": "x"}, _ansible_check_mode=True)
    assert out["changed"] is True and recorder.requests == []
    recorder.add("GET", "/api/networks", json_response([]))
    out = run_module(fwd_api, operation="getNetworks", _ansible_check_mode=True)
    assert out["changed"] is False and out["result"] == []


def test_collect_can_wait_on_a_collection_already_running(run_module, recorder):
    recorder.add(
        "GET",
        "/api/networks/101/snapshots",
        json_response({"snapshots": []}),
        json_response({"snapshots": [snapshot("s2", "2026-02-01T00:00:00Z", trigger="COLLECTION")]}),
    )
    recorder.add("GET", "/api/collector-tasks", json_response({"tasks": [{"id": "t9", "status": "RUNNING", "networkId": "101"}]}))
    recorder.add("GET", "/api/collector-tasks/t9", json_response({"id": "t9", "status": "SUCCEEDED"}))
    out = run_module(fwd_snapshot_collect, network_id="101", start_collection=False, wait_interval=1)
    assert not out.get("failed"), out
    assert out["changed"] is False and out["task_id"] == "t9" and out["snapshot_id"] == "s2"
    assert recorder.count("POST", "/api/collector-tasks") == 0


def test_collect_with_nothing_running_fails_when_not_starting(run_module, recorder):
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": []}))
    recorder.add("GET", "/api/collector-tasks", json_response({"tasks": []}))
    out = run_module(fwd_snapshot_collect, network_id="101", start_collection=False)
    assert out["failed"] and "NO_COLLECTION" in out["msg"] or "no collection" in out["msg"].lower()


# --- networks, tags, snapshots, uploads, NQE diff and library

from ansible_collections.forwardnetworks.forward.plugins.modules import (  # noqa: E402
    fwd_device_tag,
    fwd_network,
    fwd_networks,
    fwd_nqe_diff,
    fwd_nqe_library,
    fwd_snapshot,
    fwd_snapshot_upload,
)


def network(network_id, name, note=None):
    row = {"id": network_id, "name": name, "orgId": "o1"}
    if note is not None:
        row["note"] = note
    return row


def test_networks_filters_by_name(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([network("1", "prod"), network("2", "lab")]))
    out = run_module(fwd_networks, name="lab")
    assert [n["id"] for n in out["networks"]] == ["2"]


def test_network_present_creates_once(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([network("1", "prod")]))
    recorder.add("POST", "/api/networks", json_response(network("7", "lab")))
    out = run_module(fwd_network, name="lab")
    assert out["changed"] is True and out["network_id"] == "7"
    assert recorder.query_for(-1)["name"] == ["lab"]
    # a rerun finds it and changes nothing
    recorder.requests.clear()
    recorder.routes[("GET", "/api/networks")] = [json_response([network("7", "lab")])]
    out = run_module(fwd_network, name="lab")
    assert out["changed"] is False and recorder.count("POST", "/api/networks") == 0


def test_network_note_is_corrected_only_when_different(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([network("7", "lab", note="old")]))
    recorder.add("PATCH", "/api/networks/7", json_response(network("7", "lab", note="new")))
    out = run_module(fwd_network, name="lab", note="new")
    assert out["changed"] is True and out["network"]["note"] == "new"
    recorder.routes[("GET", "/api/networks")] = [json_response([network("7", "lab", note="new")])]
    assert run_module(fwd_network, name="lab", note="new")["changed"] is False


def test_network_absent_deletes_by_name_and_is_idempotent(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([network("7", "lab")]))
    recorder.add("DELETE", "/api/networks/7", json_response({}))
    assert run_module(fwd_network, name="lab", state="absent")["changed"] is True
    recorder.routes[("GET", "/api/networks")] = [json_response([])]
    assert run_module(fwd_network, name="lab", state="absent")["changed"] is False


TAGS = "/api/networks/101/device-tags"


def test_tag_present_creates_and_adds_only_missing_devices(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": [{"name": "core", "devices": ["core-1"]}]}))
    recorder.add("POST", TAGS + "/core", json_response({}))
    out = run_module(fwd_device_tag, network_id="101", name="Core", devices=["core-1", "core-2"])
    assert out["changed"] is True and out["added"] == ["core-2"] and out["removed"] == []
    assert recorder.body_for(-1) == {"devices": ["core-2"]}


def test_tag_present_is_a_noop_when_membership_matches(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": [{"name": "core", "devices": ["core-1"]}]}))
    out = run_module(fwd_device_tag, network_id="101", name="core", devices=["core-1"])
    assert out["changed"] is False
    assert [r.method for r in recorder.requests] == ["GET"]


def test_tag_created_when_missing(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": []}))
    recorder.add("POST", TAGS, json_response({"name": "core"}))
    recorder.add("POST", TAGS + "/core", json_response({}))
    out = run_module(fwd_device_tag, network_id="101", name="core", devices=["a"], color="#0064a0")
    assert out["changed"] is True
    assert recorder.body_for(1) == {"name": "core", "color": "#0064a0"}


def test_tag_exclusive_removes_other_devices(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": [{"name": "core", "devices": ["a", "b"]}]}))
    recorder.add("POST", TAGS + "/core", json_response({}))
    out = run_module(fwd_device_tag, network_id="101", name="core", devices=["a"], exclusive=True)
    assert out["changed"] is True and out["removed"] == ["b"]


def test_tag_absent_without_devices_deletes_it(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": [{"name": "core", "devices": ["a"]}]}))
    recorder.add("DELETE", TAGS + "/core", json_response({}))
    assert run_module(fwd_device_tag, network_id="101", name="core", state="absent")["changed"] is True
    assert recorder.count("DELETE", TAGS + "/core") == 1


def test_tag_absent_when_missing_is_unchanged(run_module, recorder):
    recorder.add("GET", TAGS, json_response({"tags": []}))
    assert run_module(fwd_device_tag, network_id="101", name="core", state="absent")["changed"] is False


def test_snapshot_absent_deletes_and_tolerates_missing(run_module, recorder):
    recorder.add("DELETE", "/api/snapshots/9", json_response({}))
    assert run_module(fwd_snapshot, snapshot_id="9", state="absent")["changed"] is True
    recorder.routes[("DELETE", "/api/snapshots/9")] = [json_response({"message": "gone"}, status=404)]
    assert run_module(fwd_snapshot, snapshot_id="9", state="absent")["changed"] is False


def test_snapshot_note_is_sent(run_module, recorder):
    recorder.add("PATCH", "/api/snapshots/9", json_response({"id": "9"}))
    out = run_module(fwd_snapshot, snapshot_id="9", note="after change")
    assert out["changed"] is True
    assert recorder.body_for(0) == {"note": "after change"}


def test_snapshot_reprocess_waits_until_processed(run_module, recorder):
    recorder.add("POST", "/api/snapshots/9", json_response({"previousState": "PROCESSED", "state": "PROCESSING"}))
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": [snapshot("9", "2026-01-01T00:00:00Z")]}))
    out = run_module(fwd_snapshot, snapshot_id="9", state="reprocessed", network_id="101")
    assert not out.get("failed"), out
    assert out["changed"] is True and out["snapshot"]["state"] == "PROCESSED"
    assert recorder.query_for(0)["reprocess"] == ["true"]


def test_upload_requires_files_to_exist(run_module, tmp_path):
    out = run_module(fwd_snapshot_upload, network_id="101", files=[str(tmp_path / "nope.zip")])
    assert out["failed"] and "not found" in out["msg"]


def test_upload_returns_the_new_snapshot(run_module, recorder, tmp_path):
    archive = tmp_path / "lab.zip"
    archive.write_bytes(b"PK")
    recorder.add("POST", "/api/networks/101/snapshots", json_response(snapshot("12", "2026-03-01T00:00:00Z")))
    recorder.add("GET", "/api/networks/101/snapshots", json_response({"snapshots": [snapshot("12", "2026-03-01T00:00:00Z")]}))
    out = run_module(fwd_snapshot_upload, network_id="101", files=[str(archive)], note="lab")
    assert not out.get("failed"), out
    assert out["snapshot_id"] == "12" and out["changed"] is True


def test_nqe_diff_summarizes_changes_by_type(run_module, recorder):
    recorder.add(
        "POST",
        "/api/nqe-diffs/b/a",
        json_response(
            {
                "rows": [
                    {"type": "ADDED", "after": {"x": 1}},
                    {"type": "DELETED", "before": {"x": 2}},
                    {"type": "ADDED", "after": {"x": 3}},
                ],
                "totalNumRows": 3,
            }
        ),
    )
    out = run_module(fwd_nqe_diff, query_id="FQ_abc", before="b", after="a")
    assert not out.get("failed"), out
    assert out["count"] == 3 and out["summary"] == {"ADDED": 2, "DELETED": 1}
    assert recorder.body_for(0)["queryId"] == "FQ_abc"


def test_nqe_diff_needs_one_query_reference(run_module):
    out = run_module(fwd_nqe_diff, before="b", after="a")
    assert out["failed"]


def test_library_directory_loading_builds_paths_and_inlines_imports(tmp_path):
    (tmp_path / "helpers.nqe").write_text("helper = 1;\n")
    (tmp_path / "bgp.nqe").write_text('import "helpers.nqe";\nforeach d in network.devices select {n: d.name}')
    (tmp_path / "notes.txt").write_text("ignored")
    files = fwd_nqe_library.load_directory(str(tmp_path), "/MyOrg")
    assert sorted(files) == ["/MyOrg/bgp", "/MyOrg/helpers"]
    assert "import" not in files["/MyOrg/bgp"] and "helper = 1;" in files["/MyOrg/bgp"]


def test_library_needs_something_to_publish(run_module, tmp_path):
    out = run_module(fwd_nqe_library, src=str(tmp_path), title="t")
    assert out["failed"] and "no queries" in out["msg"]


def test_library_check_mode_publishes_nothing(run_module, recorder):
    out = run_module(fwd_nqe_library, queries={"/A/b": "q"}, title="t", _ansible_check_mode=True)
    assert out["changed"] is True and recorder.requests == []


def test_tag_exclusive_needs_devices_and_duplicates_are_ignored(run_module, recorder):
    out = run_module(fwd_device_tag, network_id="101", name="core", exclusive=True)
    assert out["failed"] and "devices" in out["msg"]
    recorder.add("GET", TAGS, json_response({"tags": [{"name": "core", "devices": []}]}))
    recorder.add("POST", TAGS + "/core", json_response({}))
    out = run_module(fwd_device_tag, network_id="101", name="core", devices=["a", "a"])
    assert out["added"] == ["a"]


def test_network_present_with_unknown_id_fails_instead_of_creating(run_module, recorder):
    recorder.add("GET", "/api/networks", json_response([network("1", "prod")]))
    out = run_module(fwd_network, name="lab", network_id="999")
    assert out["failed"] and "999" in out["msg"]
    assert recorder.count("POST", "/api/networks") == 0


def test_predict_diff_fails_on_auth_and_server_errors_instead_of_reporting_empty(run_module, recorder):
    from ansible_collections.forwardnetworks.forward.plugins.modules import fwd_predict_diff

    recorder.default = lambda request: json_response({"message": "bad credentials"}, status=401)
    out = run_module(fwd_predict_diff, before="b", after="a")
    assert out["failed"]
    recorder.default = lambda request: json_response({"message": "boom"}, status=500)
    assert run_module(fwd_predict_diff, before="b", after="a")["failed"]


def test_export_into_a_missing_directory_fails_cleanly(run_module, recorder, tmp_path):
    out = run_module(fwd_snapshot_export, snapshot_id="9", dest=str(tmp_path / "nope" / "snap.zip"))
    assert out["failed"] and "Cannot write" in out["msg"]
