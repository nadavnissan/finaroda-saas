"""JWT auth helpers + get_current_user dependency (hardened per SPEC §4)."""
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt

from backend.config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, JWT_SECRET
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
import backend.config as _cfg


def create_access_token(user_id: int) -> str:
    """Create a JWT with sub=user_id, exp=now+JWT_EXPIRE_DAYS."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_magic_link_token() -> str:
    """Cryptographically secure 48-char token (the RAW token, emailed to the user)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(48))


def hash_token(token: str) -> str:
    """SHA-256 hex of a magic-link token. Only the HASH is persisted (SPEC §4)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> CurrentUser:
    """Extract and validate the user from the JWT cookie. Raises 401 if invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Not authenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not access_token:
        raise credentials_exception
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    rows = await db.execute_fetchall(
        """SELECT internal_id, email, auth_provider, is_admin, tier,
                  subscription_status, created_at, last_login_at, onboarding_completed_at
           FROM users WHERE internal_id = ?""",
        (user_id,),
    )
    if not rows:
        raise credentials_exception

    row = dict(rows[0])
    # Attach the user id (only — no PII) to the Sentry scope when monitoring is on.
    from backend.core.monitoring import set_request_user

    set_request_user(row["internal_id"])
    return CurrentUser(
        internal_id=row["internal_id"],
        email=row["email"],
        auth_provider=row.get("auth_provider", "email"),
        is_admin=bool(row.get("is_admin", 0)),
        tier=row.get("tier", "free"),
        subscription_status=row.get("subscription_status", "none"),
        created_at=row.get("created_at"),
        last_login_at=row.get("last_login_at"),
        onboarding_completed=bool(row.get("onboarding_completed_at")),
    )


async def is_email_allowed(email: str, db: aiosqlite.Connection) -> bool:
    """True if the email may sign up (bypassed when FEATURE_PUBLIC_SIGNUPS_OPEN=True)."""
    if _cfg.FEATURE_PUBLIC_SIGNUPS_OPEN:
        return True
    rows = await db.execute_fetchall(
        "SELECT 1 FROM beta_allowlist WHERE email = ?", (email.lower().strip(),)
    )
    return bool(rows)


def is_bootstrap_admin(email: str) -> bool:
    """Whether this email should be auto-granted is_admin on signup (bootstrap)."""
    return email.lower().strip() in _cfg.ADMIN_BOOTSTRAP_EMAILS


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency: requires admin (DB role users.is_admin). Raises 403 otherwise."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin only"},
        )
    return user


async def require_active_trial(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> CurrentUser:
    """Dependency: 402 if the user's trial has expired and no active sub. Admins bypass."""
    if user.is_admin or user.subscription_status == "active":
        return user
    rows = await db.execute_fetchall(
        "SELECT trial_ends_at FROM users WHERE internal_id = ?", (user.internal_id,)
    )
    if rows and rows[0][0]:
        trial_end = datetime.fromisoformat(str(rows[0][0]).replace("Z", "+00:00"))
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        if trial_end < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=402,
                detail={"code": "TRIAL_EXPIRED", "message": "Trial period has ended"},
            )
    return user
