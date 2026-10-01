"""Core models for Google Voice operations."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CallType(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    MISSED = "missed"
    VOICEMAIL = "voicemail"


class SMSMessage(BaseModel):
    id: str
    sender: str
    recipient: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = True
    direction: str = "incoming"  # incoming or outgoing


class CallRecord(BaseModel):
    id: str
    phone_number: str
    call_type: CallType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int = 0
    transcript: Optional[str] = None


class Voicemail(BaseModel):
    id: str
    sender: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    is_read: bool = False
