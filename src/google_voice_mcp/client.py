"""Google Voice client mock & integration layer."""

import os
from typing import List, Optional
from datetime import datetime
import uuid

from google_voice_mcp.models import SMSMessage, CallRecord, CallType, Voicemail


class GoogleVoiceClient:
    """Client for Google Voice actions."""

    def __init__(self, account_email: Optional[str] = None):
        self.account_email = account_email or os.getenv("GOOGLE_VOICE_ACCOUNT", "default")
        # In-memory store for active session/mocking/caching
        self._messages: List[SMSMessage] = [
            SMSMessage(
                id="msg-1",
                sender="+16262344927",
                recipient="+14155552671",
                text="Hey, checking in on the MCP server progress!",
                timestamp=datetime.utcnow(),
                is_read=True,
                direction="incoming",
            )
        ]
        self._calls: List[CallRecord] = [
            CallRecord(
                id="call-1",
                phone_number="+16262344927",
                call_type=CallType.INCOMING,
                timestamp=datetime.utcnow(),
                duration_seconds=142,
            )
        ]
        self._voicemails: List[Voicemail] = [
            Voicemail(
                id="vm-1",
                sender="+16262344927",
                timestamp=datetime.utcnow(),
                duration_seconds=35,
                transcript="Hey Misha, give me a call back when you get a chance regarding the demo.",
                is_read=False,
            )
        ]

    def send_sms(self, recipient: str, text: str) -> SMSMessage:
        msg = SMSMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            sender=self.account_email,
            recipient=recipient,
            text=text,
            timestamp=datetime.utcnow(),
            is_read=True,
            direction="outgoing",
        )
        self._messages.append(msg)
        return msg

    def list_sms(self, limit: int = 10, unread_only: bool = False) -> List[SMSMessage]:
        msgs = self._messages
        if unread_only:
            msgs = [m for m in msgs if not m.is_read]
        return msgs[-limit:]

    def list_calls(self, limit: int = 10) -> List[CallRecord]:
        return self._calls[-limit:]

    def list_voicemails(self, limit: int = 10) -> List[Voicemail]:
        return self._voicemails[-limit:]
