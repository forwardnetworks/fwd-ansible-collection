# Forward Networks Ansible Integration (Scaffold)

This repository scaffolds a modern Ansible **Collection** for integrating with the Forward Networks API.

- Collection: `forwardnetworks.forward`
- Modules:
  - `fwd_api`: generic REST wrapper
  - `fwd_nqe_query`: NQE query runner
  - `fwd_devices`: network/snapshot device inventory (GET `/api/networks/{networkId}/devices`)
  - `fwd_snapshots`: snapshot metadata (GET `/api/networks/{networkId}/snapshots`)
  - `fwd_snapshot_collect`: trigger/wait for snapshots
  - `fwd_snapshot_export`: download snapshot archives
  - `fwd_snapshot_checks`: retrieve existing snapshot checks
  - `fwd_path_search`: single path search (GET `/api/networks/{networkId}/paths`)
  - `fwd_path_search_bulk`: run multiple searches (POST `/api/networks/{networkId}/paths-bulk`)
- Inventory: `forward_networks` dynamic inventory with filter + compose support
- Filters: `nqe_diff` for comparing NQE query results (pre/post checks)

## Quick start (development)

1) Install Ansible (ansible-core) in a virtualenv.

2) Ensure Ansible can find the local collection:

```bash
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
```

3) Run example commands (after sourcing `.env` if desired):

```bash
make example-api           # fwd_api example
make example-inventory     # dynamic inventory example
ansible-playbook -i localhost, examples/get_devices.yml
ansible-playbook -i localhost, examples/get_snapshots.yml
ansible-playbook -i localhost, examples/path_search.yml
ansible-playbook -i localhost, examples/path_search_bulk.yml
ansible-playbook -i localhost, examples/nqe_intent.yml   # baseline/diff workflow
ansible-playbook -i localhost, examples/change_control.yml  # snapshot + intent workflow
```

## Authentication

By default, modules and inventory read credentials from environment variables:

- `FORWARD_BASE_URL` (example: `https://app.forwardnetworks.com`) (alias: `FWD_HOST`)
- `FORWARD_TOKEN` (token-as-username for HTTP Basic)
- `FORWARD_USERNAME` / `FORWARD_PASSWORD` (HTTP Basic) (aliases: `FWD_USER` / `FWD_PASS`)
- `FORWARD_VALIDATE_CERTS` (`true`/`false`, optional)
- `FORWARD_TIMEOUT` (seconds, optional)

Per-task parameters can override env vars.

Auth is sent as HTTP Basic per the included `openapi.json` (either token-only or username/password).

## Primary use case: intent checks (pre/post change)

The collection is designed around Forward Networks intent workflows:

- **Pre-change**: capture baseline with `fwd_nqe_query`, `fwd_devices`, and `fwd_snapshots`.
- **Change window**: perform your network updates (outside this repo).
- **Post-change**: re-run the same NQE queries and compare results (use the `nqe_diff` filter). Optionally run path searches (`fwd_path_search` / `fwd_path_search_bulk`) to validate reachability or expected blocks.

See `docs/INTENT_CHECKS.md` for a detailed walkthrough and playbook outline.

## Repository layout

- `ansible_collections/forwardnetworks/forward/`: the collection
- `docs/`: design notes and specs
- `examples/`: example playbooks and inventory configs
