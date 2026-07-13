"""Support ticket models (B3 'Report a problem' → B7 queue). Table: mig 018."""
from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["bug", "question", "billing", "other"]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    category: TicketCategory = "bug"
    app_version: str | None = Field(default=None, max_length=40)  # captured for debugging


class TicketResponse(BaseModel):
    id: int
    status: str
