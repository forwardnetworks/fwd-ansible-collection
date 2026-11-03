# Usage

Option-level documentation lives with each plugin: `ansible-doc forwardnetworks.forward.fwd_devices`, and `ansible-doc -t inventory forwardnetworks.forward.forward_networks`. This page covers what the docs do not: how the pieces fit and what to watch for.

## Connection

All modules share `base_url`, `username`, `password`, `validate_certs` and `timeout`, each falling back to the `FORWARD_*` environment variables (see the README). `network_id` falls back to `FORWARD_NETWORK_ID`. A missing `forward-sdk` fails the task with an install hint naming the Python interpreter Ansible used; if the SDK is installed in a virtualenv, set `ansible_python_interpreter` to it.

## Snapshots and baselines

- `fwd_snapshots` with `latest_processed: true` returns the newest processed snapshot **excluding predictions**. Once Predict is in use, the newest processed snapshot is often a prediction, and using one as a baseline compares a change against a change.
- `fwd_snapshot_collect` waits for the collection and for the snapshot to process, ignoring predictions, and returns `snapshot_id`. `start_collection: false` waits on a collection already queued or running instead (and fails if there is none). `wait: false` returns right after queueing, with no snapshot ID.
- Omit `snapshot_id` on NQE, devices and path search to use the network's latest processed snapshot. Pin it in change-control playbooks so a later collection cannot change what you compare.

## NQE

`fwd_nqe_query` takes exactly one of `query` (inline source), `query_id` or `query_path`, and returns all rows in `rows`. `parameters` fills a query's declared parameters; `commit_id` pins a query version (full 40 character hash). Paging is handled by the SDK, which fails loudly on a result set that ends early rather than returning a partial answer.

Compare two result lists with the filter:

```yaml
diff: "{{ baseline.rows | forwardnetworks.forward.nqe_diff(post.rows) }}"
# diff.added, diff.removed, diff.unchanged and the matching *_count fields
```

## Path search

`fwd_path_search` needs `dst_ip` and one of `from_device` or `src_ip`. In `fwd_path_search_bulk`, `intent`, `max_results` and the other limits apply to the whole request; per-query keys are the flow fields (`from_device`, `src_ip`, `dst_ip`, ports, protocol and so on), plus an optional `name` label that is not sent. Flows needing different intents are separate calls.

## Forward Predict

Predict rehearses a change without touching a device:

1. `fwd_change_set` creates a change set from a baseline snapshot, stages CLI `commands` per device and commits. Reusing `change_set_id` stages into an existing one; omitting it creates a new one each run.
2. `fwd_predict` runs Predict and returns the predicted `snapshot_id`.
3. `fwd_predict_diff` compares baseline and prediction: per-area counts, and subnet connectivity (polled until Forward finishes computing it).
4. `fwd_snapshot_checks` or `fwd_change_set_checks` read intent results against the prediction.
5. `fwd_change_set` with `state: absent` cleans up, which also deletes the predicted snapshots.

Things to know, from the SDK's Predict notes:

- The Predict endpoints are unpublished and gated by organization properties and roles. A missing licence or permission arrives as an HTTP error; `fwd_predict_diff` reports a gated area in `errors` instead of failing.
- Connectivity zeros while Forward is still computing mean "not finished". `fwd_predict_diff` waits, but a settled zero with `totalSubnetPairs: 0` means no locations are defined and nothing was compared. That is not an all-clear.
- PAN-OS firewalls cannot be changed with CLI commands (prediction fails at processing). Use the SDK's firewall Predict operations through `fwd_api`.
- A prediction over a stale base can fail with no reason; reprocess the base and predict again.

See the SDK's [Predict guide](https://forwardnetworks.github.io/forward-python-sdk/predict/) for gating properties and caveats.

## Generic calls with `fwd_api`

Any Forward operation without a dedicated module: name it by operation ID and pass `arguments` in the SDK's snake_case names (plus `body` for a request body).

```yaml
- forwardnetworks.forward.fwd_api:
    operation: getChecks
    arguments: {snapshot_id: "1234", status: [FAIL]}
```

`network_id` and `snapshot_id` default from the module options or environment. An unknown ID fails with the nearest names; streaming downloads are refused. In check mode only `get*`, `list*`, `find*` and `search*` operations run.

## Inventory

```yaml
plugin: forwardnetworks.forward.forward_networks
network_id: "101"
include_tags: true
filters: {vendor: CISCO}
keyed_groups:
  - key: vendor
    prefix: vendor
```

Every device field becomes a host variable. Enable the plugin in `ansible.cfg` if it is not picked up (`enable_plugins = ..., forwardnetworks.forward.forward_networks`); the source file name must end in `forward.yml` or `forward.yaml`.

## Managing Forward objects

- `fwd_network` ensures a network exists by name (or deletes one); `fwd_networks` lists and filters. Deleting a network deletes its snapshots.
- `fwd_device_tag` is idempotent: it creates the tag, adds only devices that lack it, and with `exclusive: true` removes it from others. Without `devices`, `state: absent` deletes the tag.
- `fwd_snapshot_upload` pushes ZIP archives into a network and waits for processing; `fwd_snapshot` deletes, reprocesses or annotates an existing one.
- `fwd_nqe_library` publishes queries to the library in one commit, skipping unchanged ones. Validate with `dry_run_snapshot_id`. `fwd_nqe_diff` compares a *committed* query across two snapshots.

Other Forward operations (locations, collection schedules, webhooks, credentials and the rest) are reachable with `fwd_api` until they get a dedicated module.

## Check mode

Read-only modules run in check mode. Modules that change something (`fwd_snapshot_collect`, `fwd_snapshot_export`, `fwd_snapshot_upload`, `fwd_snapshot`, `fwd_network`, `fwd_device_tag`, `fwd_nqe_library`, `fwd_change_set`, `fwd_predict`) report `changed` and do nothing.
