"""Pytest fixtures / env setup for the backend test suite.

Sets a throwaway DATABASE_URL and dev-mode flags BEFORE backend.config is imported,
so tests never touch the real dev DB and the magic link is returned in responses.
"""
import os
import tempfile
from pathlib import Path

# Throwaway DB, wiped at session start for isolation.
_tmp_db = Path(tempfile.gettempdir()) / "finaroda_test.db"
for suffix in ("", "-wal", "-shm"):
    p = Path(str(_tmp_db) + suffix)
    if p.exists():
        p.unlink()

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = str(_tmp_db)
os.environ["DEV_RETURN_MAGIC_LINK"] = "true"       # magic link returned in API response
os.environ["FEATURE_PUBLIC_SIGNUPS_OPEN"] = "true"  # bypass beta gate by default in tests
os.environ["FEATURE_CARDCOM_LIVE"] = "false"        # never hit a real terminal in tests
