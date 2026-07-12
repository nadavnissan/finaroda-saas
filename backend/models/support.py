"""Support ticket models (B3 'Report a problem' → B7 queue). Table: mig 018."""
from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["bug", "question", "billing", "other"]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    category: TicketCategory = "bug"


class TicketResponse(BaseModel):
    id: int
    status: str
