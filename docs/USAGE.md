# Usage

## Module: `forwardnetworks.forward.fwd_api`

Example:

```yaml
- name: Call Forward API
  forwardnetworks.forward.fwd_api:
    path: /api/example
    method: GET
  register: out

- debug:
    var: out.json
```

Auth via env vars:

```bash
export FORWARD_BASE_URL="https://app.forwardnetworks.com"
export FORWARD_TOKEN="..."   # or set FORWARD_USERNAME/FORWARD_PASSWORD
```

## Inventory plugin: `forwardnetworks.forward.forward_networks`

Create `inventory.forward.yml`:

```yaml
plugin: forwardnetworks.forward.forward_networks
network_id: "<your network id>"
host_key: "name"
# Optional filters (same keys as the fwd_devices module):
filters:
  name: "core-*"
include_tags: true
```

Then:

```bash
ansible-inventory -i inventory.forward.yml --graph
```

## Module: `forwardnetworks.forward.fwd_nqe_query`

```yaml
- name: Run an NQE query (endpoint is an example)
  forwardnetworks.forward.fwd_nqe_query:
    network_id: "123"
    query_id: "abcd"
    parameters: {}
    options: {}
  register: out

- debug:
    var: out.result
```

## Module: `forwardnetworks.forward.fwd_devices`

```yaml
- name: Fetch devices with tags for a snapshot
  forwardnetworks.forward.fwd_devices:
    network_id: "205507"
    snapshot_id: "snap-123"
    name: "core-*"
    include_tags: true
  register: devices

- debug:
    msg: "Found {{ devices.devices | length }} devices"
```

## Module: `forwardnetworks.forward.fwd_snapshots`

```yaml
- name: List snapshots (latest five, include archived)
  forwardnetworks.forward.fwd_snapshots:
    network_id: "205507"
    limit: 5
    include_archived: true
    min_successful_devices: 500
  register: snaps

- debug:
    var: snaps.snapshots
```

## Module: `forwardnetworks.forward.fwd_snapshot_collect`

```yaml
- name: Trigger snapshot and wait for completion
  forwardnetworks.forward.fwd_snapshot_collect:
    network_id: "205507"
    wait_timeout: 1200
  register: snap_run

- debug:
    msg: "Snapshot {{ snap_run.snapshot_id }} is ready"
```

- debug:
    msg: "Snapshot {{ snap_run.snapshot_id }} is ready"
```

## Module: `forwardnetworks.forward.fwd_snapshot_export`

```yaml
- name: Download snapshot archive
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "snap-123"
    dest: "/tmp/snap-123.zip"

- name: Download config-only archive
  forwardnetworks.forward.fwd_snapshot_export:
    snapshot_id: "snap-123"
    dest: "/tmp/snap-config.zip"
    only: CONFIG
```

## Module: `forwardnetworks.forward.fwd_snapshot_checks`

```yaml
- name: List failed checks for a snapshot
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "snap-123"
    status: ["FAIL"]
  register: failed_checks

- name: Fetch a specific check
  forwardnetworks.forward.fwd_snapshot_checks:
    snapshot_id: "snap-123"
    check_id: "19939965"
  register: single_check
```

## Module: `forwardnetworks.forward.fwd_path_search`

```yaml
- name: Path search example
  forwardnetworks.forward.fwd_path_search:
    network_id: "205507"
    from_device: "edge-router-1"
    dst_ip: "10.0.50.10"
    intent: PREFER_DELIVERED
  register: path_result

- debug:
    var: path_result.paths
```

## Module: `forwardnetworks.forward.fwd_path_search_bulk`

```yaml
- name: Evaluate flows
  forwardnetworks.forward.fwd_path_search_bulk:
    network_id: "205507"
    queries:
      - name: dmz_reachability
        from_device: edge-router-1
        dst_ip: 10.0.50.10
      - name: db_block
        src_ip: 10.20.30.0/24
        dst_ip: 172.16.5.10
        intent: VIOLATIONS_ONLY
  register: bulk_paths

- debug:
    var: bulk_paths.results
```

## Filter: `nqe_diff`

```yaml
- name: Compare NQE results
  vars:
    baseline: "{{ baseline_results.results[0].result.items }}"
    post: "{{ post_results.results[0].result.items }}"
    diff: "{{ baseline | nqe_diff(post) }}"
  ansible.builtin.debug:
    msg: >
      Added={{ diff.added_count }} Removed={{ diff.removed_count }}
      Unchanged={{ diff.unchanged_count }}
```
