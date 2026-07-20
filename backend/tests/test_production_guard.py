"""Stage 8 hardening — the production safety guard refuses to boot a production process
that carries a dangerous dev-only flag (config.assert_production_safety).

The guard is called at import time in main.py; here we exercise the pure function directly
with injected values so every branch is asserted without mutating the real environment.
"""
import pytest

from backend.config import DEV_JWT_SENTINEL, assert_production_safety

SAFE_SECRET = "a-real-64-hex-secret-not-the-dev-sentinel"


# ── production + dangerous flag → refuse to start ─────────────────────────────
def test_production_refuses_dev_return_magic_link():
    with pytest.raises(RuntimeError, match="DEV_RETURN_MAGIC_LINK"):
        assert_production_safety(
            "production", dev_return_magic_link=True, jwt_secret=SAFE_SECRET
        )


def test_production_refuses_dev_jwt_sentinel():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        assert_production_safety(
            "production", dev_return_magic_link=False, jwt_secret=DEV_JWT_SENTINEL
        )


def test_production_reports_all_problems_at_once():
    with pytest.raises(RuntimeError) as exc:
        assert_production_safety(
            "production", dev_return_magic_link=True, jwt_secret=DEV_JWT_SENTINEL
        )
    msg = str(exc.value)
    assert "DEV_RETURN_MAGIC_LINK" in msg and "JWT_SECRET" in msg


# ── production + safe config → boots ──────────────────────────────────────────
def test_production_with_safe_config_passes():
    assert (
        assert_production_safety(
            "production", dev_return_magic_link=False, jwt_secret=SAFE_SECRET
        )
        is None
    )


# ── non-production envs may set the dev flags freely (guard is a no-op) ────────
@pytest.mark.parametrize("env", ["development", "staging", "test"])
def test_non_production_is_a_noop_even_with_dangerous_flags(env):
    # No raise even though both dangerous flags are set — the guard only bites in production.
    assert_production_safety(
        env, dev_return_magic_link=True, jwt_secret=DEV_JWT_SENTINEL
    )
