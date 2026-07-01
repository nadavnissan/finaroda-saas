"""Auth request/response models (clean — no career fields)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class GoogleAuthRequest(BaseModel):
    id_token: str


class AppleAuthRequest(BaseModel):
    identity_token: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: Optional[str] = None
    utm_source: Optional[str] = None


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    internal_id: int
    email: str
    auth_provider: str = "email"
    is_admin: bool = False
    tier: str = "free"
    subscription_status: str = "none"
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    onboarding_completed: bool = False
