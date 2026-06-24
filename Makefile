.PHONY: install run synthetic test lint clean

install:
	uv venv .venv --python 3.12
	uv pip install --python .venv/bin/python -e ".[dev]"

run:
	.venv/bin/neoflow run-all

synthetic:
	.venv/bin/neoflow run-all --source synthetic

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check src tests

clean:
	rm -rf data/raw data/staged data/marts exports reports
