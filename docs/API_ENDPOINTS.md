# API endpoints to confirm

This repo includes `openapi.json` (Forward Networks: Complete API). The scaffold defaults align with that spec, but keep overrides for compatibility across deployments.

## Needed for inventory

- List devices for a network (and optionally a snapshot)
  - Default path: `/api/networks/{networkId}/devices`
  - Inputs: `network_id`, optional `snapshot_id` (query param `snapshotId`)
  - Output: JSON list of devices
  - Fields used: `name` (or configurable `host_key`)

## Needed for `fwd_devices`

- Same as inventory (GET `/api/networks/{networkId}/devices`) plus optional filters:
  - `name`, `displayName`, `sourceName`, `type`, `vendor`, `model`, `platform`, `osVersion`
  - `collectionError`, `processingError`
  - `skip`, `limit`, `with=tags`

## Needed for `fwd_snapshots`

- List snapshots for a network
  - Default path: `/api/networks/{networkId}/snapshots`
  - Filters: `state`, `minSuccessfulDevices`, `minSuccessfulDevicePct`, `maxCollectionFailureDevices`, etc.
  - Response: `NetworkSnapshots` object containing `snapshots` array.

## Needed for `fwd_snapshot_collect`

- Trigger collections and wait for processed snapshots
  - `POST /api/networks/{networkId}/startcollection`
  - `GET /api/networks/{networkId}/snapshots/latestProcessed` (handle 404 when no snapshots yet)

## Needed for `fwd_path_search`

- Single path search
  - Default path: `GET /api/networks/{networkId}/paths`
  - Required query params: `dstIp`, plus either `from` or `srcIp`
  - Optional: `intent`, protocol headers, Layer-7 selectors, tuning knobs.
  - Response: `PathSearchResponse`

## Needed for NQE query module

- Run a query by `query_id`
  - Default path: `/api/nqe` (POST)
  - Inputs:
    - query params: `networkId`, optional `snapshotId`
    - JSON body: `queryId`, optional `parameters`, optional `queryOptions`
  - Output: `NqeRunResult` payload (JSON)
- `POST /api/networks/{networkId}/startcollection`
- `GET /api/networks/{networkId}/snapshots/latestProcessed` (handle 404 when no snapshots yet)

## Needed for `fwd_snapshot_export`

- `GET /api/snapshots/{snapshotId}` (optional `only=CONFIG`)
- `POST /api/snapshots/{snapshotId}` with `includeDevices`, `excludeDevices`, `obfuscationKey` for custom exports

## Needed for `fwd_snapshot_checks`

- `GET /api/snapshots/{snapshotId}/checks` (+ query params `type`, `priority`, `status`)
- `GET /api/snapshots/{snapshotId}/checks/{checkId}`
