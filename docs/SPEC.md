# Forward Networks ↔ Ansible Integration Spec

## Goals

- Provide an Ansible Collection (`forwardnetworks.forward`) that:
  - Authenticates to Forward Networks with an API token.
  - Executes read-only API workflows (intent verification, inventory, query, snapshot export) safely and idempotently.
  - Fits Ansible norms: no extra runtime deps, supports `check_mode`, clear docs, predictable return values.

## Non-goals (initial scaffold)

- Managing network device configuration changes.
- Implementing every Forward API endpoint.
- Opinionated “one true” data model for all Forward artifacts.

## Authentication and configuration

**Preferred**: environment variables (works for modules + inventory plugin):

- `FORWARD_BASE_URL`: Base URL for the Forward API UI domain (alias: `FWD_HOST`).
- `FORWARD_TOKEN`: Token-only auth (sent as HTTP Basic username with empty password).
- `FORWARD_USERNAME` / `FORWARD_PASSWORD`: HTTP Basic (aliases: `FWD_USER` / `FWD_PASS`).
- `FORWARD_VALIDATE_CERTS`: `true|false` (default: `true`).
- `FORWARD_TIMEOUT`: seconds (default: `30`).

**Override**: per-task/module parameters.

## Collection components

### 1) Module: `fwd_api` (generic REST wrapper)

Purpose: unblock users immediately and act as the foundation for higher-level modules.

Inputs:
- `base_url`, `token`, `validate_certs`, `timeout`
- `method`: `GET|POST|PUT|PATCH|DELETE`
- `path`: `/api/...` path (no hostname)
- `query_params`: dict
- `body`: dict/list/string
- `headers`: dict

Outputs:
- `status_code`: int
- `json`: parsed JSON when possible
- `text`: raw response body (string)
- `response_headers`: dict

Behavior:
- `check_mode`: do not send non-GET requests.
- Any non-2xx response fails with a helpful message (include status + body).

### 2) Module: `fwd_nqe_query` (NQE query runner)

Purpose: normalized interface to run an NQE query and retrieve results.

Defaults are based on the included `openapi.json`:
- `POST /api/nqe` with query params `networkId` and optional `snapshotId`.

The module still supports `path` overrides.

Inputs:
- `network_id`, `snapshot_id` (optional), `query_id`
- `parameters` (dict), `options` (dict)
- plus auth inputs

Outputs:
- `result`: API response payload (JSON)
- `raw`: full payload (future enhancement)

Future enhancements:
- Support streaming/pagination (once API docs confirm).
- Provide helper filters to compare results (pre/post change).

### 3) Module: `fwd_devices` (device inventory)

Purpose: fetch devices for a network or snapshot via `GET /api/networks/{networkId}/devices`.

Inputs:
- `network_id` (required), `snapshot_id` optional
- Common filters (`name`, `vendor`, `device_type`, `collection_error`, etc.)
- `skip`, `limit`, `include_tags`
- `extra_params` for passthrough additions

Outputs:
- `devices` list (raw API payload)
- `query_params`, `url`

### 4) Module: `fwd_snapshots`

Purpose: fetch snapshot metadata via `GET /api/networks/{networkId}/snapshots`.

Inputs:
- `network_id` (required)
- Filter knobs (state, minimum success %, etc.)
- `include_archived`, `limit`
- `extra_params` for passthrough additions

Outputs:
- `snapshots` list (plus `raw` object)
- `query_params`, `url`

### 5) Module: `fwd_snapshot_collect`

Purpose: trigger a collection and wait for the next processed snapshot.

Inputs:
- `network_id`
- `start_collection` (bool)
- `wait`, `wait_for_new`, `previous_snapshot_id`, `wait_timeout`, `wait_interval`

Behavior:
- POST `/api/networks/{networkId}/startcollection`
- Poll GET `/api/networks/{networkId}/snapshots/latestProcessed` (honoring allow_status=404 for first snapshot)
- Supports workflows needing explicit pre/post change snapshots.

Outputs:
- `snapshot`: snapshot info
- `snapshot_id`
- `changed`: indicates whether a collection was triggered

### 6) Module: `fwd_path_search`

Purpose: run Forward path searches (Single Path Search API) with GET `/api/networks/{networkId}/paths`.

Inputs:
- `network_id`
- `from_device` or `src_ip` (one required), plus `dst_ip`
- Protocol headers: `ip_proto`, `src_port`, `dst_port`, `icmp_type`, TCP flags
- Layer-7: `app_id`, `user_id`, `user_group_id`, `url`
- Tuning: `intent`, `include_network_functions`, `include_tags`, `max_candidates`, `max_results`, `max_return_path_results`, `max_seconds`
- Snapshot override + `extra_params`

Outputs:
- `paths`: list of hop-by-hop results
- `response`: raw payload (includes return paths, `snapshotId`, `unrecognizedValues`, etc.)
- `query_params`, `url`

Notes:
- Provide filters/helpers for summarizing path info (e.g., list of devices, first violation reason).

### 6) Module: `fwd_snapshot_export`

Purpose: download snapshot archives (full, config-only, or custom subsets).

Inputs:
- `snapshot_id`, `dest`
- Optional GET param `only=CONFIG`
- Optional POST payload: `include_devices`, `exclude_devices`, `obfuscation_key`
- `force` controls overwriting existing files

Behavior:
- GET `/api/snapshots/{snapshotId}` for default exports
- POST `/api/snapshots/{snapshotId}` when subset or obfuscation is requested
- Outputs: destination path, snapshot ID, changed flag

### 7) Module: `fwd_snapshot_checks`

Purpose: retrieve existing Forward intent checks for a snapshot.

Inputs:
- `snapshot_id` (required)
- Filters: `type`, `priority`, `status`
- Optional `check_id` to fetch a single check

Behavior:
- GET `/api/snapshots/{snapshotId}/checks` or `/checks/{checkId}`
- Returns list (`checks`) or single (`check`) result(s)

### 8) Module: `fwd_path_search`

Purpose: run multiple path searches in a single POST to `/api/networks/{networkId}/paths-bulk`.

Inputs:
- Same per-query fields as `fwd_path_search`, wrapped inside a `queries` list.
- Optional `snapshot_id` query param for the entire batch.

Outputs:
- `results`: list of `PathSearchResponse` (or error objects) corresponding to each query.

Behavior:
- Validate each query has `dst_ip` and either `from_device` or `src_ip`.
- Provide human-friendly `query_index` when returning validation failures.

### 9) Module: `fwd_path_search_bulk`

### 10) Inventory plugin: `forward_networks`

Purpose: generate inventory from Forward’s device inventory API.

Defaults are based on the included `openapi.json`:
- `GET /api/networks/{networkId}/devices` with optional query param `snapshotId`.

The plugin still supports `devices_path` overrides.

Inventory behavior:
- Hosts named by `name` or configurable `host_key`.
- `compose`, `groups`, `keyed_groups` support.
- Device filters identical to `fwd_devices` (`filters` option).
- Optional `include_tags`, `extra_params`, `network_id_env` fallback.

## Roadmap (suggested)

1) Confirm Forward API endpoints for:
   - listing networks
   - listing devices in a network/snapshot
   - running NQE queries + paginating results
### Filters

- `nqe_diff`: compares two result sets (lists) and returns `added`, `removed`, `unchanged` sections with counts.
  - Intended for pre/post change analysis with `fwd_nqe_query`.
  - Implementation relies on deterministic JSON serialization for comparison.

## Roadmap (suggested)

1) Confirm Forward API endpoints for:
   - listing networks
   - listing devices in a network/snapshot
   - running NQE queries + paginating results
2) Implement additional high-level modules:
   - `fwd_snapshot_export` (download snapshot artifacts)
   - `fwd_device_facts` (normalized device/interface facts)
   - `fwd_path_search_bulk` enhancements (named queries, severity metadata)
   - `fwd_networks` / `fwd_locations` as needed
3) Add comparison helpers / filters for pre/post intent workflows (e.g., diff NQE results, summarize path outputs, exit criteria).
4) Add integration tests using `ansible-test integration` with recorded HTTP fixtures (VCR) or mocked `fetch_url`.
