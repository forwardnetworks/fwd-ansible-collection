# Development

## Local collection usage

This repo includes `ansible.cfg` setting:

- `collections_paths = ./ansible_collections`

So running playbooks from the repo root will use the local collection automatically.

## Suggested validation

If you have `ansible-test` available:

```bash
cd ansible_collections/forwardnetworks/forward
ansible-test sanity --docker default
```

## Local env file (development)

This repo expects you to keep secrets out of git. Use:

- `.env.example` as a template
- create a local `.env` file (gitignored)

In your shell:

```bash
set -a; . ./.env; set +a
export FORWARD_BASE_URL="$FWD_HOST"
export FORWARD_USERNAME="$FWD_USER"
export FORWARD_PASSWORD="$FWD_PASS"
```

## Helpful make targets

```bash
make compile            # byte-compile plugins for quick syntax validation
make example-api        # run examples/run_api.yml (sources .env automatically)
make example-inventory  # run ansible-inventory using examples/inventory.forward.yml
```

## Intent baselines

- Baseline artifacts are stored under `./baselines/` (gitignored by default).
- Use `examples/nqe_intent.yml` to capture a baseline (first run) and compare subsequent runs using the `nqe_diff` filter.
- See `examples/change_control.yml` for a full change-control workflow (pre/post snapshot + comparisons).

## Testing

- Sanity: `make sanity` (runs `ansible-test sanity` in Docker).
- Unit tests: `ansible-test units --python 3.11` (tests under `tests/unit/` cover helper utilities/filters).
