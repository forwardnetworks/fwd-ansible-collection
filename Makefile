COLLECTION_DIR := ansible_collections/forwardnetworks/forward
VENV := .venv
PY := $(VENV)/bin/python
BIN := $(abspath $(VENV))/bin

.PHONY: venv compile units sanity test example-api example-inventory

# Dev environment: ansible-core, pytest and the SDK (the collection's runtime requirement).
venv:
	uv venv $(VENV) --python 3.13
	uv pip install --python $(PY) ansible-core pytest "forward-sdk>=0.1.32"

compile:
	$(PY) -m compileall -q $(COLLECTION_DIR)/plugins

units:
	cd $(COLLECTION_DIR) && PATH=$(BIN):$$PATH ansible-test units --venv --python 3.13 --requirements

# Runs in a throwaway venv; add --docker default instead of --venv to use the container images.
sanity:
	cd $(COLLECTION_DIR) && PATH=$(BIN):$$PATH ansible-test sanity --venv --python 3.13

test: units sanity

example-api:
	@set -a; . ./.env 2>/dev/null || true; set +a; \
	$(BIN)/ansible-playbook -i localhost, examples/run_api.yml

example-inventory:
	@set -a; . ./.env 2>/dev/null || true; set +a; \
	$(BIN)/ansible-inventory -i examples/inventory.forward.yml --graph
