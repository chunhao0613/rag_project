lint:
	ruff check core services tests app.py

test:
	pytest

check: lint test
