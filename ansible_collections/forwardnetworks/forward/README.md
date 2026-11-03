# forwardnetworks.forward

Ansible collection for the Forward Networks API, built on [forward-sdk](https://github.com/forwardnetworks/forward-python-sdk).

Requires `forward-sdk>=0.1.32` (Python 3.10+) on the host that runs the modules, and ansible-core 2.17+.

- Modules: `fwd_nqe_query`, `fwd_devices`, `fwd_snapshots`, `fwd_snapshot_collect`, `fwd_snapshot_export`, `fwd_snapshot_upload`, `fwd_snapshot`, `fwd_nqe_diff`, `fwd_nqe_library`, `fwd_networks`, `fwd_network`, `fwd_device_tag`, `fwd_location`, `fwd_collection_schedule`, `fwd_webhook`, `fwd_snapshot_checks`, `fwd_path_search`, `fwd_path_search_bulk`, `fwd_change_set`, `fwd_predict`, `fwd_predict_diff`, `fwd_change_set_checks`, `fwd_api`
- Inventory plugin: `forward_networks`
- Filter: `nqe_diff`

Read the options with `ansible-doc forwardnetworks.forward.<module>`. Setup, configuration and examples are in the repository README: <https://github.com/forwardnetworks/fwd-ansible-collection#readme>.
