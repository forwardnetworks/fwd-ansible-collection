# Intent / Pre-Post Check Workflow

Primary goal: use Ansible to orchestrate Forward Networks checks before and after a change window.

## Workflow (overview)

1. **Pre-change baseline**
   - Run NQE queries (compliance, coverage, etc.) via `forwardnetworks.forward.fwd_nqe_query`.
   - Capture results locally (e.g., `set_fact` → `copy` or `ansible.builtin.copy` to disk).
2. **Change execution**
   - Apply network changes (outside this collection).
3. **Post-change validation**
   - Re-run the same NQE queries and compare to the baseline.
   - Optionally, run intent-specific APIs:
     - `forwardnetworks.forward.fwd_devices` to confirm device counts / state.
     - `forwardnetworks.forward.fwd_snapshots` to ensure snapshot processing completed.
     - `forwardnetworks.forward.fwd_path_search` to test specific traffic paths.
4. **Reporting**
   - Use Ansible `debug`, `assert`, or custom modules/templates to enforce pass/fail.

## Recommended playbook structure

```yaml
- hosts: localhost
  gather_facts: false
  vars:
    network_id: "{{ lookup('env', 'FWD_NETWORKID') }}"
    queries:
      - name: "No BGP session drops"
        query_id: "bgp_no_drops"
      - name: "Critical ACL coverage"
        query_id: "acl_coverage"
  tasks:
    - name: Run baseline queries
      loop: "{{ queries }}"
      loop_control:
        label: "{{ item.name }}"
      forwardnetworks.forward.fwd_nqe_query:
        network_id: "{{ network_id }}"
        query_id: "{{ item.query_id }}"
      register: baseline_results

    # ... apply network changes ...

    - name: Run post-change queries
      loop: "{{ queries }}"
      loop_control:
        label: "{{ item.name }}"
      forwardnetworks.forward.fwd_nqe_query:
        network_id: "{{ network_id }}"
        query_id: "{{ item.query_id }}"
      register: post_results

    - name: Compare results (simplistic example)
      vars:
        baseline_rows: "{{ baseline_results.results[0].result.items }}"
        post_rows: "{{ post_results.results[0].result.items }}"
        diff: "{{ baseline_rows | nqe_diff(post_rows) }}"
      ansible.builtin.assert:
        that:
          - diff.added_count == 0
        fail_msg: "New violations detected: {{ diff.added }}"
```

## Path search checks

- Use `forwardnetworks.forward.fwd_path_search` to validate reachability or explicit blocks.
- Tips:
  - When traffic should succeed, set `intent: PREFER_DELIVERED` and assert at least one path exists.
  - When traffic should fail, set `intent: VIOLATIONS_ONLY` or `PREFER_VIOLATIONS` and assert violation reasons match expectations.
  - Combine with `max_results` and `include_network_functions` to tune response verbosity/performance.
- For multiple flows, prefer `forwardnetworks.forward.fwd_path_search_bulk` so the API evaluates them in a single call.
- Use `forwardnetworks.forward.fwd_snapshot_collect` to trigger and wait for snapshots as part of pre/post change workflows.

## Next steps

- Provide fixtures/examples to store baseline outputs in a Git repo or artifact storage.
- Expand `fwd_path_search_bulk` examples (naming flows, gating via asserts).
- Use the sample playbooks:
  - `examples/nqe_intent.yml` for baseline/diff storage.
  - `examples/change_control.yml` for snapshot-triggered pre/post comparisons.
