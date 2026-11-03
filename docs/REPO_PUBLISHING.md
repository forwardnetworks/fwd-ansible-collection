# Publishing to github.com/forwardnetworks/fwd-ansible-collection

The legacy repository already exists (`gh repo view forwardnetworks/fwd-ansible-collection`). Use the GitHub CLI to stage the new Ansible collection layout and prep for a release.

## 1. Prepare a feature branch

```bash
gh repo clone forwardnetworks/fwd-ansible-collection
cd fwd-ansible-collection
git checkout -b ansible-collection-mvp
```

Copy the contents of this workspace (the `ansible_collections/forwardnetworks/forward` tree, docs, examples, Makefile, etc.) into the cloned repo, removing the obsolete `fwd-api` layout.

## 2. Run tests locally

From the repo root:

```bash
make compile
make test                        # ansible-test units + sanity
```

Optionally exercise live API workflows (requires `.env`):

```bash
ANSIBLE_CONFIG=$PWD/ansible.cfg PYTHONPATH=$PWD:$PYTHONPATH \
  ansible-playbook -c local -i localhost, examples/run_api.yml
```

## 3. Commit and push

```bash
git status
git add ansible_collections docs examples Makefile ansible.cfg .gitignore .env.example CLAUDE.md README.md CHANGELOG.md
git commit -m "feat: migrate to new Ansible collection MVP"
git push --set-upstream origin ansible-collection-mvp
```

## 4. Create a pull request

```bash
gh pr create \
  --title "Ansible collection MVP" \
  --body "Replace legacy modules with the new collection layout (tests: sanity + units)." \
  --base master \
  --head ansible-collection-mvp
```

Use `gh pr view --web` to review/merge once approvals are in.

## 5. Tag and release

After merge:

```bash
gh release create v0.2.0 \
  --notes-file CHANGELOG.md \
  --title "forwardnetworks.forward 0.2.0"
```

## 6. Build and publish to Ansible Galaxy

One-time setup:

1. Sign in at <https://galaxy.ansible.com> with GitHub (the account that will publish).
2. Make sure the `forwardnetworks` namespace exists and that you own it. Galaxy ties namespaces to GitHub accounts and organizations; for an organization namespace, request it through the process in the Galaxy documentation (a request issue on `ansible/galaxy`) and have it assigned to the publishing user. Check the current steps in the Galaxy docs before filing.
3. Create an API token at <https://galaxy.ansible.com/ui/token/> and keep it in a secret store (CI secret), not in the repo.

Per release:

```bash
# bump version in ansible_collections/forwardnetworks/forward/galaxy.yml and CHANGELOG.md, run `make test`
ansible-galaxy collection build ansible_collections/forwardnetworks/forward --output-path dist/
ansible-galaxy collection publish dist/forwardnetworks-forward-<version>.tar.gz --token "$GALAXY_API_KEY"
```

Galaxy imports the tarball asynchronously; the import log shows any metadata problems. Versions are immutable once published, so rehearse with `ansible-galaxy collection install dist/*.tar.gz -p /tmp/try` and run a module from that copy first.

Things to settle before the first publish:

- **License.** GPL-3.0-or-later, matching the module headers (the Ansible convention). `LICENSE` at the repo root and `COPYING` in the collection hold the text.
- **Python dependency.** Galaxy does not install pip packages. The README and `requirements.txt` say users need `forward-sdk>=0.1.32`; for Execution Environments, `requirements.txt` is picked up by `ansible-builder`.
- **Private Galaxy / Automation Hub.** Use the same `build` and `publish` with `--server` pointing at your instance.
