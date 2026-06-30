"""Pytest fixtures / env setup for the backend test suite.

Sets a throwaway DATABASE_URL BEFORE backend.config is imported so tests never
touch the real dev DB.
"""
import os
import tempfile
from pathlib import Path

# Point the app at a temp DB before any backend import reads config.
_tmp_db = Path(tempfile.gettempdir()) / "finaroda_test.db"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ["DATABASE_URL"] = str(_tmp_db)
