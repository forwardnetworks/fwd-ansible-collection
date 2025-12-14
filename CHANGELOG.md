# Changelog

## 0.1.0 (2024-12-13)

- Initial Forward Networks collection scaffold.
- Modules: `fwd_api`, `fwd_nqe_query`, `fwd_devices`, `fwd_snapshots`, `fwd_snapshot_collect`, `fwd_snapshot_export`, `fwd_path_search`, `fwd_path_search_bulk`.
- Inventory plugin: `forward_networks`.
- Filter: `nqe_diff`.
- Examples covering API usage, inventory, intent baselines, path search, and change control workflows.
- Tests: sanity (`ansible-test sanity`) and unit tests for helper utilities/filters (`ansible-test units --python 3.13`).
