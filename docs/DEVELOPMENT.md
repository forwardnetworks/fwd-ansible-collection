# Development

## Environment

```bash
make venv     # .venv with ansible-core, pytest and forward-sdk
```

`ansible.cfg` sets `collections_path = .`, so running playbooks from the repo root uses the local collection without installing it. To work against a local SDK checkout instead of PyPI: `uv pip install --python .venv/bin/python -e ~/src/forward-python-sdk`.

Credentials: copy `.env.example` to `.env` (gitignored) and `set -a; . ./.env; set +a`.

## Checks

```bash
make compile   # byte-compile plugins
make units     # ansible-test units (installs tests/unit/requirements.txt in a venv)
make sanity    # ansible-test sanity in a venv; use --docker default for the container images
make test      # units + sanity
```

Plain pytest also works from the repo root: `PYTHONPATH=. .venv/bin/python -m pytest ansible_collections/forwardnetworks/forward/tests/unit`.

Module tests run each module's `main()` against `forward_sdk.testing.ForwardRecorder`, which scripts the HTTP responses under the real SDK transport, so they fail if the SDK changes how it talks to Forward. `tests/integration/test_change_control.yml` needs a live Forward instance. `tests/output/` is generated and gitignored.

Supported ansible-core: 2.17 and newer. The unit tests and an end-to-end module and inventory run were checked on 2.17 to 2.22; `ansible-test sanity` was run on the latest.

## Adding a module

- Build the client and handle errors through `module_utils/sdk.py` (`get_client`, `to_plain`, `error_message`), so a missing package produces the install hint. Import other SDK names (such as `QueryRef`) lazily inside `main()`, after `get_client`.
- Write the connection options explicitly in `argument_spec` (validate-modules cannot follow a shared dict) and extend the `forwardnetworks.forward.auth` fragment in the docs.
- Return plain data with `sdk.to_plain`, which keeps Forward's camelCase field names.
- Add a test beside the existing ones that scripts the responses and asserts on the request the SDK sent.

## Intent baselines

Baselines from `examples/nqe_intent.yml` are written under `./baselines/` (gitignored).
