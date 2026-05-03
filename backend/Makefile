.PHONY: test coverage venv

# Create venv and install deps (optional one-time setup)
venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Run tests from backend/ — uses .venv when present
test:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest tests/ $(ARGS); \
	else \
		python3 -m pytest tests/ $(ARGS); \
	fi

# Term summary + HTML report under htmlcov/
coverage:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest tests/ \
			--cov=app \
			--cov-config=.coveragerc \
			--cov-report=term-missing \
			--cov-report=html \
			$(ARGS); \
	else \
		python3 -m pytest tests/ \
			--cov=app \
			--cov-config=.coveragerc \
			--cov-report=term-missing \
			--cov-report=html \
			$(ARGS); \
	fi
