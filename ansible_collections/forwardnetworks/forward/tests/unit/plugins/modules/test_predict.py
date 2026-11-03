import httpx
import pytest

from ansible_collections.forwardnetworks.forward.plugins.modules import (
    fwd_change_set,
    fwd_change_set_checks,
    fwd_predict,
    fwd_predict_diff,
)

pytest.importorskip("forward_sdk")


def json_response(payload, status=200):
    return httpx.Response(status, json=payload)


CS = "/api/networks/101/change-sets"


def snap(snapshot_id, created, trigger, state="PROCESSED"):
    return {"id": snapshot_id, "state": state, "createdAt": created, "processedAt": created, "processingTrigger": trigger}


def test_change_set_is_based_on_latest_real_snapshot_and_commits(run_module, recorder):
    recorder.add(
        "GET",
        "/api/networks/101/snapshots",
        json_response({"snapshots": [snap("pred", "2026-01-03T00:00:00Z", "PREDICT"), snap("real", "2026-01-02T00:00:00Z", "COLLECTION")]}),
    )
    recorder.add("POST", CS, json_response({"id": "CS1", "name": "uplink"}))
    recorder.add("PUT", CS + "/CS1/draft/devices/dc-core/commands", json_response({}))
    recorder.add("POST", CS + "/CS1/commits", json_response({"commitId": "c1", "note": "go"}))
    out = run_module(
        fwd_change_set,
        network_id="101",
        name="uplink",
        commands={"dc-core": "interface Ethernet1\n shutdown"},
        commit=True,
        commit_note="go",
    )
    assert not out.get("failed"), out
    assert out["change_set_id"] == "CS1"
    assert out["base_snapshot_id"] == "real"
    assert out["commit"]["commitId"] == "c1"
    create = next(r for r in recorder.requests if r.method == "POST" and r.url.path == CS)
    assert b'"snapshotId":"real"' in create.content.replace(b" ", b"")
    staged = next(r for r in recorder.requests if r.method == "PUT")
    assert staged.content == b"interface Ethernet1\n shutdown"


def test_change_set_commit_needs_a_note(run_module):
    out = run_module(fwd_change_set, network_id="101", name="x", commit=True)
    assert out["failed"] and "commit_note" in out["msg"]


def test_change_set_absent_deletes(run_module, recorder):
    recorder.add("DELETE", CS + "/CS1", json_response({}))
    out = run_module(fwd_change_set, network_id="101", change_set_id="CS1", state="absent")
    assert out["changed"] is True
    assert recorder.count("DELETE", CS + "/CS1") == 1


def test_predict_waits_for_the_predicted_snapshot(run_module, recorder):
    recorder.add("POST", CS + "/CS1", json_response({"id": "P1", "note": "r1"}))
    recorder.add(
        "GET",
        "/api/networks/101/snapshots",
        json_response({"snapshots": [snap("P1", "2026-01-04T00:00:00Z", "PREDICT", state="PROCESSING")]}),
        json_response({"snapshots": [snap("P1", "2026-01-04T00:00:00Z", "PREDICT")]}),
    )
    out = run_module(fwd_predict, network_id="101", change_set_id="CS1", note="r1", wait_timeout=30)
    assert not out.get("failed"), out
    assert out["snapshot_id"] == "P1"
    assert out["snapshot"]["state"] == "PROCESSED"
    assert recorder.query_for(0)["note"] == ["r1"]


def test_predict_without_wait_returns_immediately(run_module, recorder):
    recorder.add("POST", CS + "/CS1", json_response({"id": "P1"}))
    out = run_module(fwd_predict, network_id="101", change_set_id="CS1", note="r1", wait=False)
    assert out["snapshot_id"] == "P1"
    assert len(recorder.requests) == 1


def test_predict_diff_reports_counts_and_settled_connectivity(run_module, recorder):
    for area in ("devices", "interfaces", "topology", "l2", "acl", "nat", "arp", "mac"):
        recorder.add("GET", "/api/diffs/b/a/" + area, json_response({"count": 2, "complete": True}))
    recorder.add(
        "GET",
        "/api/diffs/b/a/subnet-connectivity",
        json_response({"isPartialResult": True, "totalSubnetPairs": 10, "evaluatedSubnetPairs": 0}),
        json_response({"isPartialResult": False, "totalSubnetPairs": 10, "evaluatedSubnetPairs": 10}),
    )
    out = run_module(fwd_predict_diff, before="b", after="a", connectivity_timeout=30)
    assert not out.get("failed"), out
    assert out["counts"]["acl"] == {"count": 2, "complete": True}
    assert out["subnet_connectivity"]["isPartialResult"] is False
    assert out["errors"] == {}


def test_predict_diff_reports_a_gated_area_instead_of_failing(run_module, recorder):
    recorder.add("GET", "/api/diffs/b/a/devices", json_response({"count": 1, "complete": True}))
    recorder.default = lambda request: json_response({"message": "feature not enabled"}, status=403)
    out = run_module(fwd_predict_diff, before="b", after="a", include=["counts", "subnet_connectivity"])
    assert not out.get("failed"), out
    assert out["counts"]["devices"]["count"] == 1
    assert "interfaces" in out["errors"] and "subnet_connectivity" in out["errors"]


def test_change_set_checks_passes_the_predicted_snapshot(run_module, recorder):
    recorder.add("GET", CS + "/CS1/checks", json_response({"checks": [{"id": "k1", "status": "FAIL", "numViolations": 3}]}))
    out = run_module(fwd_change_set_checks, network_id="101", change_set_id="CS1", snapshot_id="P1")
    assert not out.get("failed"), out
    assert out["checks"] == [{"id": "k1", "status": "FAIL", "numViolations": 3}]
    assert recorder.query_for(0)["snapshotId"] == ["P1"]
