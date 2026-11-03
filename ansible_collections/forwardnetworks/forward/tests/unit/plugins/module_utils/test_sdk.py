import pytest

pytest.importorskip("forward_sdk")

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk  # noqa: E402


def test_sdk_names_win_over_legacy_aliases():
    env = sdk.resolved_environ({"FORWARD_URL": "https://new", "FORWARD_BASE_URL": "https://old", "FWD_USER": "u"})
    assert env["FORWARD_URL"] == "https://new"
    assert env["FORWARD_USERNAME"] == "u"


def test_legacy_names_still_configure_the_client():
    settings = sdk.client_settings(
        {}, {"FWD_HOST": "https://fwd.test", "FWD_USER": "key", "FWD_PASS": "secret", "FORWARD_VALIDATE_CERTS": "false"}
    )
    assert settings["base_url"] == "https://fwd.test"
    assert (settings["username"], settings["password"]) == ("key", "secret")
    assert settings["verify"] is False


def test_task_params_override_environment():
    settings = sdk.client_settings(
        {"base_url": "https://task", "validate_certs": True, "timeout": 12, "network_id": "9"},
        {"FORWARD_URL": "https://env", "FORWARD_VERIFY_TLS": "false", "FORWARD_NETWORK_ID": "1"},
    )
    assert settings["base_url"] == "https://task"
    assert settings["verify"] is True
    assert settings["timeout"] == 12.0
    assert settings["network_id"] == "9"


def test_missing_url_is_a_configuration_error():
    with pytest.raises(sdk.ForwardError):
        sdk.client_settings({}, {})


def test_to_plain_uses_api_field_names_and_drops_unset_fields():
    from forward_sdk._generated.models import PredictedSnapshotMeta

    meta = PredictedSnapshotMeta.model_validate({"id": "7", "processingTrigger": "PREDICT"})
    assert sdk.to_plain(meta) == {"id": "7", "processingTrigger": "PREDICT"}
    assert sdk.to_plain([meta, {"k": meta}]) == [
        {"id": "7", "processingTrigger": "PREDICT"},
        {"k": {"id": "7", "processingTrigger": "PREDICT"}},
    ]


def test_explicit_validate_certs_true_keeps_a_private_ca_bundle(tmp_path):
    bundle = tmp_path / "private-ca.pem"
    bundle.write_text("")
    settings = sdk.client_settings(
        {"base_url": "https://x", "validate_certs": True}, {"FORWARD_VERIFY_TLS": str(bundle)}
    )
    assert settings["verify"] == str(bundle)
    settings = sdk.client_settings(
        {"base_url": "https://x", "validate_certs": False}, {"FORWARD_VERIFY_TLS": str(bundle)}
    )
    assert settings["verify"] is False
