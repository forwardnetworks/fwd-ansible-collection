from __future__ import annotations

import json


def _normalize_row(row):
    """
    Convert arbitrary JSON-compatible data into a deterministic string for diffing.
    """
    try:
        return json.dumps(row, sort_keys=True, separators=(",", ":"))
    except TypeError:
        # Fallback for non-serializable entries: convert to string.
        return str(row)


def nqe_diff(baseline, current):
    """
    Compute added/removed/same rows between two NQE query result lists.
    Both inputs should be iterables of dict/list/primitive items.
    """
    baseline = baseline or []
    current = current or []

    base_map = {_normalize_row(item): item for item in baseline}
    curr_map = {_normalize_row(item): item for item in current}

    base_keys = set(base_map.keys())
    curr_keys = set(curr_map.keys())

    added = [curr_map[k] for k in sorted(curr_keys - base_keys)]
    removed = [base_map[k] for k in sorted(base_keys - curr_keys)]
    unchanged = [curr_map[k] for k in sorted(base_keys & curr_keys)]

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "added_count": len(added),
        "removed_count": len(removed),
        "unchanged_count": len(unchanged),
    }


class FilterModule(object):
    def filters(self):
        return {
            "nqe_diff": nqe_diff,
        }
