# Forward Networks Ansible Collection

Ansible collection `forwardnetworks.forward` for the [Forward Networks](https://www.forwardnetworks.com/) API, built on [forward-sdk](https://github.com/forwardnetworks/forward-python-sdk). The collection holds no HTTP client of its own: every module and the inventory plugin call the SDK, so retries, rate limiting, paging guard rails and snapshot waiting come from there.

> A Forward Networks field integration, not a supported Forward Networks product. See the SDK README for what that means.

## Install

```bash
pip install "forward-sdk>=0.1.32"      # in the Python environment Ansible uses (Python 3.10+)
ansible-galaxy collection install forwardnetworks.forward
```

The modules call the Forward API, not your devices, so run them on a host that can reach Forward, normally `localhost` with `connection: local`. Needs ansible-core 2.17 or newer (tested on 2.17 to 2.22).

## What is in it

| Plugin | What it does |
| --- | --- |
| `fwd_nqe_query` | Run an NQE query (inline, by ID, or by library path) and return every row |
| `fwd_devices` | List devices in a snapshot, with filters and tags |
| `fwd_snapshots` | List snapshots, or find the latest processed one (predictions excluded) |
| `fwd_snapshot_collect` | Start a collection and wait for the processed snapshot |
| `fwd_snapshot_export` | Download a snapshot archive |
| `fwd_snapshot_upload` | Upload snapshot archives into a network, and wait for processing |
| `fwd_snapshot` | Delete, reprocess or annotate a snapshot |
| `fwd_snapshot_checks` | Read intent check results for a snapshot |
| `fwd_nqe_diff` | Diff a committed NQE query's results between two snapshots |
| `fwd_nqe_library` | Publish NQE queries (inline or from `.nqe` files) to the query library |
| `fwd_networks` / `fwd_network` | List networks; create or delete one (idempotent by name) |
| `fwd_device_tag` | Manage device tags and their membership (idempotent) |
| `fwd_location` | Create, correct or delete a map location (idempotent by name) |
| `fwd_collection_schedule` | Manage scheduled collections (matches identical settings, or an ID) |
| `fwd_webhook` | Manage webhooks (idempotent by name; the password is write-only, see `update_password`) |
| `fwd_path_search` / `fwd_path_search_bulk` | Trace one packet, or many flows in one call |
| `fwd_change_set` | Create, stage and commit a Forward Predict change set |
| `fwd_predict` | Run Predict and get the predicted snapshot |
| `fwd_predict_diff` | Blast radius of a change: per-area diff counts and subnet connectivity |
| `fwd_change_set_checks` | Intent check results for a change set |
| `fwd_api` | Escape hatch: call any Forward operation by its operation ID |
| `forward_networks` (inventory) | Build inventory from Forward devices, with `compose`, `groups`, `keyed_groups` |
| `nqe_diff` (filter) | Compare two NQE result lists (pre/post checks) |

Full option docs: `ansible-doc forwardnetworks.forward.fwd_nqe_query` (and so on).

## Configuration

Credentials are an API token: its access key is the username, its secret the password. Settings resolve as task option, then environment, then the collection's older names.

| Variable | Meaning |
| --- | --- |
| `FORWARD_URL` | Instance URL (aliases `FORWARD_BASE_URL`, `FWD_HOST`) |
| `FORWARD_USERNAME` / `FORWARD_PASSWORD` | Token access key and secret (aliases `FWD_USER` / `FWD_PASS`) |
| `FORWARD_NETWORK_ID` | Default network, so modules can omit `network_id` |
| `FORWARD_VERIFY_TLS` | `false`, or a CA bundle path for a private CA (alias `FORWARD_VALIDATE_CERTS`) |
| `FORWARD_TIMEOUT`, `FORWARD_RETRIES`, `FORWARD_RATE_LIMIT_RPM` | Passed to the SDK |

Per-task `base_url`, `username`, `password`, `validate_certs` and `timeout` override these. Copy `.env.example` to `.env` for local work.

## Quick start

```yaml
- hosts: localhost
  gather_facts: false
  tasks:
    - forwardnetworks.forward.fwd_snapshots:
        network_id: "101"
        latest_processed: true
      register: baseline

    - forwardnetworks.forward.fwd_nqe_query:
        network_id: "101"
        snapshot_id: "{{ baseline.snapshot_id }}"
        query: |
          foreach device in network.devices
          select {name: device.name, platform: device.platform}
      register: devices
```

## Main use cases

- **Intent checks around a change window**: baseline NQE queries, change, collect a new snapshot, re-run and compare with `nqe_diff`. See [docs/INTENT_CHECKS.md](docs/INTENT_CHECKS.md) and `examples/change_control.yml`.
- **Forward Predict**: rehearse a change before touching the network. See `examples/predict_change.yml`.
- **Inventory**: `examples/inventory.forward.yml`.

Examples run from the repo root: `ansible.cfg` points Ansible at the local collection, so nothing needs installing.

## Layout

- `ansible_collections/forwardnetworks/forward/`: the collection
- `docs/`: usage, intent-check workflow, development and publishing notes
- `examples/`: example playbooks and inventory

Development: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Changes: [CHANGELOG.md](CHANGELOG.md).
