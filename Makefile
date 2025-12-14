.PHONY: compile sanity

compile:
	python3 -m compileall -q ansible_collections/forwardnetworks/forward/plugins

sanity:
	cd ansible_collections/forwardnetworks/forward && ansible-test sanity --docker default

.PHONY: example-api example-inventory

example-api:
	@set -a; . ./.env 2>/dev/null || true; set +a; \
	export FORWARD_BASE_URL="$${FORWARD_BASE_URL:-$${FWD_HOST}}"; \
	export FORWARD_USERNAME="$${FORWARD_USERNAME:-$${FWD_USER}}"; \
	export FORWARD_PASSWORD="$${FORWARD_PASSWORD:-$${FWD_PASS}}"; \
	ansible-playbook -i localhost, examples/run_api.yml

example-inventory:
	@set -a; . ./.env 2>/dev/null || true; set +a; \
	export FORWARD_BASE_URL="$${FORWARD_BASE_URL:-$${FWD_HOST}}"; \
	export FORWARD_USERNAME="$${FORWARD_USERNAME:-$${FWD_USER}}"; \
	export FORWARD_PASSWORD="$${FORWARD_PASSWORD:-$${FWD_PASS}}"; \
	ansible-inventory -i examples/inventory.forward.yml --graph
