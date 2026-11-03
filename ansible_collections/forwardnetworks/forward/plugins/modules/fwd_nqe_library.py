#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Forward Networks
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: fwd_nqe_library
short_description: Publish NQE queries to the Forward Networks query library
description:
  - Publishes a set of queries to the library in one commit, keeping queries you ship in step with your playbooks or repository.
  - Each path is added or edited as needed. Unchanged queries are skipped, so a rerun with nothing new reports no change.
  - In check mode a change is always reported, since unchanged queries are only detected while publishing.
  - Optionally validates the queries against a snapshot first, so one that no longer compiles is caught before anyone else sees it.
  - Uses endpoints Forward does not publish; they can change between Forward releases.
extends_documentation_fragment:
  - forwardnetworks.forward.auth
options:
  queries:
    description: Map of library path to query source. Paths gain a leading slash.
    type: dict
  src:
    description:
      - Directory of C(.nqe) files to publish (top level only), each at O(directory)/I(file stem).
      - Local C(import) lines are inlined and C(@primaryKey) is kept, as the SDK does when publishing.
    type: path
  directory:
    description: Library directory the files from O(src) are published under.
    type: str
    default: /
  title:
    description: Commit title.
    type: str
    required: true
  body:
    description: Commit message body.
    type: str
    default: ""
  repository:
    description: Which library to publish to.
    type: str
    choices: [org, fwd]
    default: org
  dry_run_snapshot_id:
    description: Validate against this snapshot before committing. Recommended.
    type: str
  overwrite_drafts:
    description: Publish even when a path has someone else's uncommitted draft, which would be committed with yours.
    type: bool
    default: false
author:
  - Forward Networks (@forwardnetworks)
"""

EXAMPLES = r"""
- name: Publish the team's queries, validated against the latest snapshot
  forwardnetworks.forward.fwd_nqe_library:
    src: queries/
    directory: /MyOrg
    title: Update MyOrg audits
    dry_run_snapshot_id: "{{ baseline.snapshot_id }}"
"""

RETURN = r"""
committed_paths:
  description: Library paths that were added or changed.
  type: list
  elements: str
  returned: success
skipped_paths:
  description: Library paths whose source was unchanged.
  type: list
  elements: str
  returned: success
"""

import os

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.forwardnetworks.forward.plugins.module_utils import sdk


def load_directory(src, directory):
    """Read the top-level .nqe files in src the way the SDK publishes them (imports inlined, @primaryKey kept)."""
    from forward_sdk.nqe.files import iter_query_files, load_query

    base = directory.strip("/")
    return {
        "/" + "/".join(part for part in (base, path.stem) if part): load_query(path, for_execution=False)
        for path in iter_query_files(src)
    }


def main():
    module = AnsibleModule(
        argument_spec={
            "base_url": {"type": "str"},
            "username": {"type": "str"},
            "password": {"type": "str", "no_log": True},
            "validate_certs": {"type": "bool"},
            "timeout": {"type": "float"},
            "queries": {"type": "dict"},
            "src": {"type": "path"},
            "directory": {"type": "str", "default": "/"},
            "title": {"type": "str", "required": True},
            "body": {"type": "str", "default": ""},
            "repository": {"type": "str", "choices": ["org", "fwd"], "default": "org"},
            "dry_run_snapshot_id": {"type": "str"},
            "overwrite_drafts": {"type": "bool", "default": False},
        },
        required_one_of=[("queries", "src")],
        supports_check_mode=True,
    )
    p = module.params
    files = {k: str(v) for k, v in (p["queries"] or {}).items()}
    if p["src"]:
        if not sdk.HAS_SDK:
            sdk.require_sdk(module)
        if not os.path.isdir(p["src"]):
            module.fail_json(msg="src is not a directory: %s" % p["src"])
        files.update(load_directory(p["src"], p["directory"]))
    if not files:
        module.fail_json(msg="no queries to publish")
    if module.check_mode:
        module.exit_json(changed=True, msg="check_mode: nothing published", committed_paths=[], skipped_paths=[])

    client = sdk.get_client(module)
    try:
        report = client.nqe.repo.publish(
            files,
            title=p["title"],
            body=p["body"],
            repository=p["repository"],
            dry_run_snapshot_id=p["dry_run_snapshot_id"],
            overwrite_drafts=p["overwrite_drafts"],
        )
    except sdk.ForwardError as exc:
        module.fail_json(msg=sdk.error_message(exc))
    finally:
        client.close()
    committed = list(report.committed_paths)
    module.exit_json(changed=bool(committed), committed_paths=committed, skipped_paths=list(report.skipped_paths))


if __name__ == "__main__":
    main()
