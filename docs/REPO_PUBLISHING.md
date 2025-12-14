# Publishing to github.com/forwardnetworks/fwd-ansible

The legacy repository already exists (`gh repo view forwardnetworks/fwd-ansible`). Use the GitHub CLI to stage the new Ansible collection layout and prep for a release.

## 1. Prepare a feature branch

```bash
gh repo clone forwardnetworks/fwd-ansible
cd fwd-ansible
git checkout -b ansible-collection-mvp
```

Copy the contents of this workspace (the `ansible_collections/forwardnetworks/forward` tree, docs, examples, Makefile, etc.) into the cloned repo, removing the obsolete `fwd-api` layout.

## 2. Run tests locally

From the repo root:

```bash
make compile
make sanity                      # ansible-test sanity --docker default
ansible-test units --python 3.14 --color no
```

Optionally exercise live API workflows (requires `.env`):

```bash
ANSIBLE_CONFIG=$PWD/ansible.cfg PYTHONPATH=$PWD:$PYTHONPATH \
  ansible-playbook -c local -i localhost, examples/run_api.yml
```

## 3. Commit and push

```bash
git status
git add ansible_collections docs examples tests Makefile README.md CHANGELOG.md
git commit -m "feat: migrate to new Ansible collection MVP"
git push --set-upstream origin ansible-collection-mvp
```

## 4. Create a pull request

```bash
gh pr create \
  --title "Ansible collection MVP" \
  --body "Replace legacy modules with the new collection layout (tests: sanity + units)." \
  --base main \
  --head ansible-collection-mvp
```

Use `gh pr view --web` to review/merge once approvals are in.

## 5. Tag and release

After merge:

```bash
gh release create v0.1.0 \
  --notes-file CHANGELOG.md \
  --title "forwardnetworks.forward 0.1.0"
```

## 6. Build/publish to Ansible Galaxy (private or public)

From the repo root:

```bash
ansible-galaxy collection build
ansible-galaxy collection publish forwardnetworks-forward-0.1.0.tar.gz --api-key <GALAXY_TOKEN>
```

For a private Galaxy instance, replace the publish command with the appropriate URL/API key.

