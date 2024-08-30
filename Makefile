.PHONY: lint fix format typecheck

lint:
	rye run ruff check

fix:
	rye run ruff check --fix

format:
	rye run ruff format

typecheck:
	rye run mypy src/ --strict