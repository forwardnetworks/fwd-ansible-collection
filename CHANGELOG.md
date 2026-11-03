# Changelog

## 0.2.0

Rebuilt on [forward-sdk](https://github.com/forwardnetworks/forward-python-sdk). The collection no longer has its own HTTP client; every module and the inventory plugin call the SDK.

### Added

- `fwd_nqe_diff`, `fwd_nqe_library`, `fwd_networks`, `fwd_network`, `fwd_device_tag`, `fwd_snapshot`, `fwd_snapshot_upload`.
- Forward Predict: `fwd_change_set`, `fwd_predict`, `fwd_predict_diff`, `fwd_change_set_checks`.
- `fwd_api` can run any Forward operation by ID (needs `forward-sdk>=0.1.32`).
- `fwd_snapshots`: `latest_processed` (predictions excluded unless `include_predicted`) and `snapshot_id` in the result.
- `fwd_nqe_query`: `query` (inline), `query_path`, `repository`, `commit_id`, `query_timeout`; results returned as `rows` and `count`.
- `fwd_path_search`: `domain`.
- `FORWARD_NETWORK_ID` is the default for `network_id`; `FORWARD_VERIFY_TLS` may be a CA bundle path; retries and rate limiting come from the SDK.
- `ansible-test units` coverage for the modules (scripted HTTP via the SDK's test recorder) and a documented end-to-end check on ansible-core 2.17 to 2.22.

### Changed (breaking)

- **Requires** `forward-sdk>=0.1.32` (Python 3.10+) on the host that runs the modules, and ansible-core 2.17+.
- Authentication is an API token's access key and secret (`username` / `password`). The `token` option and `FORWARD_TOKEN` are gone. `FORWARD_BASE_URL`, `FWD_HOST`, `FWD_USER`, `FWD_PASS` and `FORWARD_VALIDATE_CERTS` still work as aliases. `FWD_NETWORKID` is read only by the inventory plugin; modules use `FORWARD_NETWORK_ID`.
- `validate_certs` and `timeout` no longer have task-level defaults, so the environment applies. `timeout` is a float and now defaults to the SDK's five minutes.
- `fwd_api` now names a Forward `operation` ID (for example `getChecks`) with `arguments`, run through the SDK's `client.call`, instead of an HTTP method and path.
- `fwd_nqe_query` returns `rows` (a list) instead of `result`; the `path` and `options` options are gone.
- `fwd_devices`, `fwd_snapshots`, `fwd_path_search`, `fwd_path_search_bulk`: the `*_path` / `path` template options, `extra_params` (on path search) and the `url` / `query_params` return values are gone. Without `skip` or `limit`, `fwd_devices` returns every device.
- `fwd_snapshot_collect` waits for the collection and for processing. `start_collection: false` waits on a collection already running (it fails if there is none). `wait_for_new` and `previous_snapshot_id` are gone; use `fwd_snapshots` with `latest_processed` to read the current snapshot.
- Inventory plugin: `devices_path`, `items_key`, `network_id_env` and `token` are gone.

### Fixed

- `fwd_path_search_bulk` posted a bare list; the API takes a `{queries: [...], intent, ...}` object. Shared settings (`intent`, `max_results` and so on) are now options of the module.
- `ansible.cfg` pointed `collections_paths` at the wrong directory, so the local collection was not found.

## 0.1.0 (2024-12-13)

- Initial collection.
