"""Pytest configuration — tests import ``app`` with pythonpath = backend root."""

import os

os.environ.setdefault("LANGSMITH_TRACING", "false")
