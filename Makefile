.PHONY: uv-sync help gen-contracts gen-contract-python

uv-sync:
	uv sync --no-editable --all-packages

help:
	@echo "Available targets:"
	@echo "  gen-contracts     Generate protobuf contracts"
	@echo "  lint-contracts    Lint & validate contracts"
	# @echo "  test              Run tests (changed services)"
	# @echo "  up                Start local dev stack"
	# @echo "  down              Stop local dev stack"


gen-contracts:
	cd shared/contracts && npx buf generate --include-imports
	# protoc --protopath=./contracts --python-out=./generated
	find shared/library/awrfo-python/src/ -type d -exec touch {}/__init__.py \;
	
lint-contracts:
	cd shared/contracts && npx buf lint
	cd shared/contracts && npx buf breaking --against '../../.git#branch=main'
