.PHONY: dev test

dev:
	uv run fastapi dev app/main.py --reload-dir app

test:
	uv run python -m pytest tests/
