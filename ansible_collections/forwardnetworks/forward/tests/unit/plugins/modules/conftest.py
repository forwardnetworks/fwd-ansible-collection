import contextlib
import io
import json

import pytest

forward_sdk = pytest.importorskip("forward_sdk")

try:  # ansible-core 2.19+
    from ansible.module_utils.testing import patch_module_args  # noqa: E402
except ImportError:  # older ansible-core: feed the module its arguments the way ansible-test used to

    @contextlib.contextmanager
    def patch_module_args(args):
        from ansible.module_utils import basic

        saved = getattr(basic, "_ANSIBLE_ARGS", None)
        basic._ANSIBLE_ARGS = json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode("utf-8")
        try:
            yield
        finally:
            basic._ANSIBLE_ARGS = saved

from forward_sdk.testing import ForwardRecorder  # noqa: E402

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk  # noqa: E402


@pytest.fixture
def recorder():
    return ForwardRecorder()


@pytest.fixture
def run_module(monkeypatch, recorder):
    """Run a module's main() against scripted Forward responses and return its JSON result."""

    def build(params, environ=None):
        return forward_sdk.ForwardClient(
            "https://forward.test",
            username="key",
            password="secret",
            network_id=params.get("network_id"),
            snapshot_id=params.get("snapshot_id"),
            rate_limit_rpm=None,
            retries=0,
            transport=recorder.transport,
        )

    monkeypatch.setattr(sdk, "build_client", build)

    def run(module, **args):
        out = io.StringIO()
        with patch_module_args(args), contextlib.redirect_stdout(out):
            with pytest.raises(SystemExit):
                module.main()
        return json.loads(out.getvalue())

    return run
