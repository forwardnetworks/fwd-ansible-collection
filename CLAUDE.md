# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Ansible collection, `forwardnetworks.forward`, for the Forward Networks API, built entirely on the `forward-sdk` Python package (`~/src/forward-python-sdk`, on PyPI). The collection has no HTTP client of its own: modules and the inventory plugin call SDK services. Main use cases are pre/post-change intent checks (NQE, snapshots, checks, path search) and Forward Predict change rehearsal.

The repo root is a dev harness; the collection is `ansible_collections/forwardnetworks/forward/`. `ansible.cfg` sets `collections_path = .` (the directory *containing* `ansible_collections/`), so playbooks run from the repo root use the local collection without installing it.

## Commands

```bash
make venv      # .venv with ansible-core, pytest, forward-sdk (uv)
make units     # ansible-test units --venv (installs tests/unit/requirements.txt)
make sanity    # ansible-test sanity --venv (no Docker needed)
make test      # both
# Quick loop without ansible-test, from the repo root:
PYTHONPATH=. .venv/bin/python -m pytest ansible_collections/forwardnetworks/forward/tests/unit -q
# One test:  ... -k test_bulk_posts
```

Put `.venv/bin` on `PATH` for ad hoc `ansible` / `ansible-doc` runs. `tests/output/` is generated and gitignored. `tests/integration/test_change_control.yml` and the playbooks in `examples/` need a live Forward instance. Supported ansible-core is 2.17+; unit tests and an end-to-end module and inventory run were checked on 2.17 to 2.22, sanity on the latest only.

## Architecture

Everything under `ansible_collections/forwardnetworks/forward/plugins/`:

- `module_utils/sdk.py` owns the client and error handling (modules import `forward_sdk` directly only for lazy names like `QueryRef`, after `get_client`). It does a guarded import (`HAS_SDK`), resolves settings in the order task param, `FORWARD_*` env var, legacy alias (`LEGACY_ENV`: `FWD_HOST`, `FWD_USER`, `FORWARD_BASE_URL`, ...), builds the client (`get_client` for modules, `build_client` for the inventory plugin), and converts SDK models to plain camelCase data (`to_plain`). Modules must go through it so a missing SDK yields the install hint.
- `module_utils/device_filters.py` and `path_search.py`: pure helpers (snake_case options to API names; the bulk path search request body). These and the `nqe_diff` filter are the only code testable without the SDK.
- `modules/fwd_*.py`: one module per task. Each lists the connection options explicitly in `argument_spec` (validate-modules cannot follow a shared dict) and extends the `forwardnetworks.forward.auth` doc fragment. `fwd_api` is the escape hatch: it names a Forward operation ID and runs it with `client.call` rather than taking an HTTP path.
- Predict modules: `fwd_change_set` (create/stage/commit/delete), `fwd_predict`, `fwd_predict_diff`, `fwd_change_set_checks`. They use `client.change_sets`, `client.snapshot_diffs`; the endpoints are unpublished and org-gated, so failures can be gating, not bugs.
- `inventory/forward_networks.py`: dynamic inventory over `client.devices.iter`, with constructed/cache support.

## Testing approach

`tests/unit/plugins/modules/conftest.py` provides `run_module`: it patches `sdk.build_client` to return a real `ForwardClient` on `forward_sdk.testing.ForwardRecorder`, then runs a module's `main()` and returns its JSON. So tests script HTTP responses and assert on the request the SDK actually sent, instead of mocking the SDK. Response shapes (for example `taskId`, `orgId` on networks) come from the SDK's models; if a fixture fails validation, check the SDK model. `conftest.py` falls back to a manual argument patch on ansible-core older than 2.19, where `patch_module_args` does not exist. Tests need `forward-sdk>=0.1.32`; without it they skip.

## Gotchas

- Credentials come from the environment (`.env`, gitignored; template `.env.example`). Token-only auth is gone: the SDK uses an API token's access key and secret as username and password.
- `latest_processed` excludes predicted snapshots on purpose. Basing a baseline or change set on a prediction predicts a change against a change.
- `fwd_path_search_bulk` posts a `PathSearchBulkRequest` object (`queries` plus shared `intent` and limits), not a bare list. `intent` is per request, never per query.
- Settled-zero subnet connectivity with `totalSubnetPairs: 0` means nothing was compared, not that nothing changed.
- `openapi.json` at the repo root is the old spec and is not used by any code; the SDK carries its own.
- Module GPL headers and `galaxy.yml`'s `Apache-2.0` license disagree; unresolved.
- The pin is `forward-sdk>=0.1.32` (adds `client.call` and `collect(start=False)`). Check the SDK's changelog and PyPI before using anything newer from `~/src/forward-python-sdk`, which can be ahead of the release.
