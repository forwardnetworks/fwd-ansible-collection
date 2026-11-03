from ansible_collections.forwardnetworks.forward.plugins.module_utils.device_filters import build_device_filters


def test_filters_use_api_names_and_drop_unset():
    filters = build_device_filters({"name": "core-*", "os_version": "17.3", "vendor": None, "device_type": ""})
    assert filters == {"name": "core-*", "osVersion": "17.3"}


def test_extra_params_pass_through():
    assert build_device_filters({"name": "core-*"}, {"custom": "x"}) == {"name": "core-*", "custom": "x"}
