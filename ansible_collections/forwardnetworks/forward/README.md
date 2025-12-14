# forwardnetworks.forward

An Ansible Collection scaffolding integration with the Forward Networks API.

Current content:

- Modules:
  - `fwd_api` – generic REST wrapper
  - `fwd_nqe_query` – NQE query runner
  - `fwd_devices` – device inventory fetcher
  - `fwd_snapshots` – snapshot inventory
  - `fwd_snapshot_collect` – trigger/wait for snapshots
  - `fwd_path_search` – single path search
  - `fwd_path_search_bulk` – multiple path searches
- Inventory plugin:
  - `forward_networks` – builds Ansible inventory from Forward devices, with filter/compose support
- Filters:
  - `nqe_diff` – compare NQE results (pre/post intent checks)

See `../../../../docs/SPEC.md` for design/spec notes and `../../../../docs/USAGE.md` for examples.
