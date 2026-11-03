# Intent / pre-post check workflow

Use Ansible to orchestrate Forward checks before and after a change window.

1. **Pre-change baseline.** Find the baseline snapshot with `fwd_snapshots` (`latest_processed: true`) and run NQE queries against it with `fwd_nqe_query`. Pinning `snapshot_id` keeps the comparison stable.
2. **Change.** Apply the change (outside this collection).
3. **Post-change.** `fwd_snapshot_collect` starts a collection and returns the processed snapshot. Re-run the same queries against it and compare with `nqe_diff`.
4. **Gate.** `assert` on the diff, on `fwd_snapshot_checks` results, and on path searches for flows that must (or must not) be delivered.

```yaml
- hosts: localhost
  gather_facts: false
  vars:
    network_id: "{{ lookup('env', 'FORWARD_NETWORK_ID') }}"
  tasks:
    - forwardnetworks.forward.fwd_snapshots:
        network_id: "{{ network_id }}"
        latest_processed: true
      register: pre

    - forwardnetworks.forward.fwd_nqe_query:
        network_id: "{{ network_id }}"
        snapshot_id: "{{ pre.snapshot_id }}"
        query_path: /Audits/BGP
      register: before

    # ... apply the change ...

    - forwardnetworks.forward.fwd_snapshot_collect:
        network_id: "{{ network_id }}"
      register: post

    - forwardnetworks.forward.fwd_nqe_query:
        network_id: "{{ network_id }}"
        snapshot_id: "{{ post.snapshot_id }}"
        query_path: /Audits/BGP
      register: after

    - ansible.builtin.assert:
        that: (before.rows | forwardnetworks.forward.nqe_diff(after.rows)).added_count == 0
        fail_msg: "New violations after the change"
```

## Path search checks

- Traffic that should succeed: `intent: PREFER_DELIVERED`, assert at least one path.
- Traffic that should be blocked: `intent: VIOLATIONS_ONLY` returns only non-delivered paths, so assert one exists. `PREFER_VIOLATIONS` finds drops, loops and blackholes first.
- Several flows: `fwd_path_search_bulk` evaluates them in one call. `intent` and the limits apply to the whole call.

## Checking before you change

With Forward Predict you can rehearse the change first: stage it with `fwd_change_set`, run `fwd_predict`, then read `fwd_predict_diff` and `fwd_snapshot_checks` on the predicted snapshot. See `examples/predict_change.yml`.

## Examples

- `examples/nqe_intent.yml`: store a baseline on disk and diff later runs against it.
- `examples/change_control.yml`: baseline, collect, compare, check gate.
- `examples/predict_change.yml`: rehearse a change in Predict.
