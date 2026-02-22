.PHONY: uv-sync test

uv-sync:
	uv sync --no-editable --package awrfo-allocator-service
test:
	uv run python -m pytest tests/
