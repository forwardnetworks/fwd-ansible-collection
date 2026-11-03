import httpx
import pytest

from ansible_collections.forwardnetworks.forward.plugins.modules import (
    fwd_collection_schedule,
    fwd_location,
    fwd_webhook,
)

pytest.importorskip("forward_sdk")


def json_response(payload, status=200):
    return httpx.Response(status, json=payload)


LOCS = "/api/networks/101/locations"


def loc(id, name, **kw):
    return dict({"id": id, "name": name, "lat": 1.0, "lng": 2.0}, **kw)


def test_location_created_once_and_requires_coordinates(run_module, recorder):
    recorder.add("GET", LOCS, json_response([]))
    out = run_module(fwd_location, network_id="101", name="SJC1")
    assert out["failed"] and "lat and lng" in out["msg"]
    recorder.add("POST", LOCS, json_response(loc("l1", "SJC1")))
    out = run_module(fwd_location, network_id="101", name="SJC1", lat=1.0, lng=2.0, admin_division="CA")
    assert out["changed"] is True and out["location_id"] == "l1"
    assert recorder.body_for(-1)["adminDivision"] == "CA"
    # rerun: it exists with the same values
    recorder.requests.clear()
    recorder.routes[("GET", LOCS)] = [json_response([loc("l1", "SJC1", adminDivision="CA")])]
    out = run_module(fwd_location, network_id="101", name="SJC1", lat=1.0, lng=2.0, admin_division="CA")
    assert out["changed"] is False and recorder.count("POST", LOCS) == 0


def test_location_patches_only_the_differences(run_module, recorder):
    recorder.add("GET", LOCS, json_response([loc("l1", "SJC1", city="Old")]))
    recorder.add("PATCH", LOCS + "/l1", json_response(loc("l1", "SJC1", city="San Jose")))
    out = run_module(fwd_location, network_id="101", name="SJC1", lat=1.0, city="San Jose")
    assert out["changed"] is True
    assert recorder.body_for(-1) == {"city": "San Jose"}


def test_location_absent_and_check_mode(run_module, recorder):
    recorder.add("GET", LOCS, json_response([loc("l1", "SJC1")]))
    recorder.add("DELETE", LOCS + "/l1", json_response({}))
    out = run_module(fwd_location, network_id="101", name="SJC1", state="absent", _ansible_check_mode=True)
    assert out["changed"] is True and recorder.count("DELETE", LOCS + "/l1") == 0
    assert run_module(fwd_location, network_id="101", name="SJC1", state="absent")["changed"] is True
    recorder.routes[("GET", LOCS)] = [json_response([])]
    assert run_module(fwd_location, network_id="101", name="SJC1", state="absent")["changed"] is False


SCH = "/api/networks/101/collection-schedules"


def sched(id, **kw):
    return dict({"id": id, "enabled": True, "daysOfTheWeek": [1, 2, 3, 4, 5, 6, 7]}, **kw)


def test_schedule_matches_identical_settings_instead_of_duplicating(run_module, recorder):
    recorder.add("GET", SCH, json_response({"schedules": [sched("s1", times=["02:00"], timeZone="UTC")]}))
    out = run_module(fwd_collection_schedule, network_id="101", times=["02:00"], time_zone="UTC")
    assert out["changed"] is False and out["schedule_id"] == "s1"
    assert recorder.count("POST", SCH) == 0


def test_schedule_created_when_nothing_matches(run_module, recorder):
    recorder.add("GET", SCH, json_response({"schedules": [sched("s1", times=["03:00"])]}))
    recorder.add("POST", SCH, json_response(sched("s2", times=["02:00"])))
    out = run_module(fwd_collection_schedule, network_id="101", times=["02:00"])
    assert out["changed"] is True and out["schedule_id"] == "s2"
    assert recorder.body_for(-1)["times"] == ["02:00"]


def test_schedule_by_id_is_replaced_when_different_and_deleted(run_module, recorder):
    recorder.add("GET", SCH, json_response({"schedules": [sched("s1", times=["03:00"])]}))
    recorder.add("PUT", SCH + "/s1", json_response({}))
    recorder.add("GET", SCH + "/s1", json_response(sched("s1", times=["02:00"])))
    out = run_module(fwd_collection_schedule, network_id="101", schedule_id="s1", times=["02:00"])
    assert out["changed"] is True and out["schedule"]["times"] == ["02:00"]
    recorder.add("DELETE", SCH + "/s1", json_response({}))
    assert run_module(fwd_collection_schedule, network_id="101", schedule_id="s1", state="absent")["changed"] is True
    out = run_module(fwd_collection_schedule, network_id="101", schedule_id="zz", state="absent")
    assert out["changed"] is False


def test_schedule_rejects_times_with_period(run_module):
    out = run_module(fwd_collection_schedule, network_id="101", times=["02:00"], period_in_seconds=60)
    assert out["failed"]


HOOKS = "/api/webhooks"


def hook(name="h", **kw):
    return dict(
        {"name": name, "url": "https://x/h", "enabled": True, "eventParams": {"type": "SNAPSHOT_READY"}}, **kw
    )


def test_webhook_create_sends_password_but_never_returns_it(run_module, recorder):
    recorder.add("GET", HOOKS, json_response({"webhooks": []}))
    recorder.add("POST", HOOKS, json_response({}))
    recorder.add("GET", HOOKS, json_response({"webhooks": [hook(credential={"type": "BASIC_AUTH", "username": "u"})]}))
    out = run_module(fwd_webhook, name="h", url="https://x/h", event_type="SNAPSHOT_READY", auth_username="u", auth_password="pw")
    assert out["changed"] is True and out["webhook"]["credential"] == {"type": "BASIC_AUTH", "username": "u"}
    assert recorder.count("POST", HOOKS) == 1
    body = recorder.body_for(1)
    assert body["credential"] == {"type": "BASIC_AUTH", "username": "u", "password": "pw"}
    assert "pw" not in str(out["webhook"])


def test_webhook_needs_url_and_event_to_create(run_module, recorder):
    recorder.add("GET", HOOKS, json_response({"webhooks": []}))
    assert run_module(fwd_webhook, name="h")["failed"]


def test_webhook_idempotent_and_updates_only_when_different(run_module, recorder):
    recorder.add("GET", HOOKS, json_response({"webhooks": [hook(credential={"type": "BASIC_AUTH", "username": "u"})]}))
    out = run_module(fwd_webhook, name="h", url="https://x/h", event_type="SNAPSHOT_READY", auth_username="u", auth_password="pw")
    assert out["changed"] is False and recorder.count("PATCH", HOOKS + "/h") == 0
    recorder.requests.clear()
    recorder.add("PATCH", HOOKS + "/h", json_response({}))
    out = run_module(fwd_webhook, name="h", url="https://x/new", network_ids=["101"], auth_username="u", auth_password="pw")
    assert out["changed"] is True
    body = recorder.body_for(1)
    assert body["url"] == "https://x/new" and body["eventParams"] == {"networkIds": ["101"]}
    assert body["credential"]["password"] == "pw"


def test_webhook_update_password_always_reports_changed(run_module, recorder):
    recorder.add("GET", HOOKS, json_response({"webhooks": [hook()]}))
    recorder.add("PATCH", HOOKS + "/h", json_response({}))
    out = run_module(fwd_webhook, name="h", auth_username="u", auth_password="pw", update_password="always")
    assert out["changed"] is True


def test_webhook_absent_and_check_mode(run_module, recorder):
    recorder.add("GET", HOOKS, json_response({"webhooks": [hook()]}))
    recorder.add("DELETE", HOOKS + "/h", json_response({}))
    out = run_module(fwd_webhook, name="h", state="absent", _ansible_check_mode=True)
    assert out["changed"] is True and recorder.count("DELETE", HOOKS + "/h") == 0
    assert run_module(fwd_webhook, name="h", state="absent")["changed"] is True
