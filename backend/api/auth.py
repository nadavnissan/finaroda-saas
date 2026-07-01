"""Auth endpoints: magic-link (signup+login), verify, google, apple(stub), logout, me."""
from datetime import datetime, timedelta, timezone

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, Response

from backend.config import (
    DEV_RETURN_MAGIC_LINK,
    ENVIRONMENT,
    JWT_EXPIRE_DAYS,
    MAGIC_LINK_EXPIRE_MINUTES,
    RESEND_API_KEY,
    TRIAL_DAYS,
)
from backend.core.auth import (
    create_access_token,
    generate_magic_link_token,
    get_current_user,
    hash_token,
    is_bootstrap_admin,
    is_email_allowed,
)
from backend.core.database import get_db_connection
from backend.core.email import ResendEmailClient, send_welcome_email
from backend.core.google_oauth import verify_google_id_token
from backend.models.auth import CurrentUser, GoogleAuthRequest, MagicLinkRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = structlog.get_logger(__name__)

_email_client = ResendEmailClient()

_BETA_GATE = {
    "code": "BETA_GATE",
    "message": "FINARODA is in closed beta. Join the waitlist.",
    "waitlist_url": "/coming-soon",
}


def _set_auth_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key="access_token",
        value=create_access_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=JWT_EXPIRE_DAYS * 24 * 3600,
        secure=(ENVIRONMENT == "production"),
    )


@router.post("/magic-link")
async def request_magic_link(
    body: MagicLinkRequest,
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    """Request a magic link. Creates the user on first visit (signup == login)."""
    email = body.email.lower().strip()

    if not await is_email_allowed(email, db):
        raise HTTPException(status_code=403, detail=_BETA_GATE)

    existing = await db.execute_fetchall(
        "SELECT internal_id, first_name FROM users WHERE email = ?", (email,)
    )
    if not existing:
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "INSERT INTO users (email, auth_provider, is_admin, created_at) VALUES (?, 'email', ?, ?)",
            (email, 1 if is_bootstrap_admin(email) else 0, now_iso),
        )
        user_id = cursor.lastrowid
        first_name = None
        await db.commit()
        await send_welcome_email(email)
    else:
        user_id = existing[0][0]
        first_name = existing[0][1]

    raw_token = generate_magic_link_token()
    expires = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)
    # Store only the HASH (SPEC §4) — the raw token lives only in the emailed link.
    await db.execute(
        "UPDATE users SET magic_link_token = ?, magic_link_expires_at = ? WHERE internal_id = ?",
        (hash_token(raw_token), expires.isoformat(), user_id),
    )
    await db.commit()

    result = await _email_client.send_magic_link(email, raw_token, first_name)

    response_data: dict = {"message": "Magic link sent", "email": email}
    if DEV_RETURN_MAGIC_LINK and not RESEND_API_KEY and isinstance(result, str):
        response_data["dev_magic_link"] = result
        response_data["dev_warning"] = "DEV MODE — link in response. NEVER enable in production."
    return response_data


@router.get("/verify")
async def verify_magic_link(
    token: str,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    """Verify a magic-link token (matched by hash) and set the JWT cookie."""
    rows = await db.execute_fetchall(
        "SELECT internal_id, magic_link_expires_at FROM users WHERE magic_link_token = ?",
        (hash_token(token),),
    )
    if not rows:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        )

    row = dict(rows[0])
    user_id = row["internal_id"]
    expires_str = row.get("magic_link_expires_at")
    if expires_str:
        expires = datetime.fromisoformat(str(expires_str).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401, detail={"code": "EXPIRED_TOKEN", "message": "Token expired"}
            )

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE users SET magic_link_token = NULL, magic_link_expires_at = NULL,
           email_verified_at = COALESCE(email_verified_at, ?), last_login_at = ?
           WHERE internal_id = ?""",
        (now_iso, now_iso, user_id),
    )
    await db.commit()

    _set_auth_cookie(response, user_id)
    return {"message": "Authenticated successfully"}


@router.post("/google")
async def google_oauth(
    body: GoogleAuthRequest,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    """Authenticate via Google ID token. Creates the user on first visit."""
    try:
        info = await verify_google_id_token(body.id_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_GOOGLE_TOKEN", "message": str(exc)}
        ) from exc

    email = info["email"]
    if not await is_email_allowed(email, db):
        raise HTTPException(status_code=403, detail=_BETA_GATE)

    existing = await db.execute_fetchall(
        "SELECT internal_id FROM users WHERE email = ?", (email,)
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    if not existing:
        cursor = await db.execute(
            """INSERT INTO users
               (email, auth_provider, email_verified_at, first_name, last_name, is_admin, created_at)
               VALUES (?, 'google', ?, ?, ?, ?, ?)""",
            (
                email,
                now_iso,
                info.get("given_name", ""),
                info.get("family_name", ""),
                1 if is_bootstrap_admin(email) else 0,
                now_iso,
            ),
        )
        user_id = cursor.lastrowid
        await db.commit()
        await send_welcome_email(email, first_name=info.get("given_name") or None)
    else:
        user_id = existing[0][0]

    await db.execute(
        "UPDATE users SET last_login_at = ? WHERE internal_id = ?", (now_iso, user_id)
    )
    await db.commit()

    _set_auth_cookie(response, user_id)
    return {"message": "Authenticated via Google", "email": email}


@router.post("/apple")
async def apple_oauth():
    """Apple Sign In — documented stub (V2). Returns 501."""
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Apple Sign In is not available in V1. Use magic link or Google.",
        },
    )


@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {"data": current_user.model_dump()}
