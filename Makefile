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
	cd shared/contracts && buf generate --include-imports
	# protoc --protopath=./contracts --python-out=./generated
	find shared/generated/awrfo-python/src/ -type d -exec touch {}/__init__.py \;
	
lint-contracts:
	cd shared/contracts && buf lint
	cd shared/contracts && buf breaking --against '../../.git#branch=main'
