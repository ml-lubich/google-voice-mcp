"""Bounded Google Voice operations through the user's existing Chrome."""

import os

from google_voice_mcp.browser import VoiceBrowser, VoiceError
from google_voice_mcp.models import boolean, integer, message


class GoogleVoiceClient:
    def __init__(self, account_email=None, port=None, tab_id=None, browser=None):
        self.account_email = account_email if account_email is not None else os.getenv("GOOGLE_VOICE_ACCOUNT")
        if self.account_email is not None:
            if not isinstance(self.account_email, str) or not self.account_email.strip():
                raise VoiceError("account must be a nonempty email address")
            self.account_email = self.account_email.strip()
        if port is None:
            configured = os.getenv("GOOGLE_VOICE_PORT", "9222")
            try:
                port = int(configured)
            except ValueError:
                raise VoiceError("GOOGLE_VOICE_PORT must be an integer") from None
        self.port = integer(port, "port", 65535)
        self.tab_id = tab_id if tab_id is not None else os.getenv("GOOGLE_VOICE_TAB_ID")
        if self.tab_id is not None and (not isinstance(self.tab_id, str) or not self.tab_id.strip()):
            raise VoiceError("tab_id must be a nonempty string")
        self._browser = browser

    def _backend(self):
        if self._browser is None:
            self._browser = VoiceBrowser(account_email=self.account_email, port=self.port, tab_id=self.tab_id)
        return self._browser

    def _require_account(self):
        if not self.account_email:
            raise VoiceError("Set GOOGLE_VOICE_ACCOUNT or supply --account before reading or sending")

    def doctor(self) -> dict:
        return self._backend().inspect()

    def _read(self, kind, limit, unread_only=False):
        integer(limit, "limit", 100)
        boolean(unread_only, "unread_only")
        self._require_account()
        return self._backend().read(kind, limit, unread_only=unread_only)

    def list_sms(self, limit=10, unread_only=False) -> dict:
        return self._read("sms", limit, unread_only)

    def list_calls(self, limit=10) -> dict:
        return self._read("calls", limit)

    def list_voicemails(self, limit=10) -> dict:
        return self._read("voicemails", limit)

    def read_thread(self, limit=20) -> dict:
        return self._read("thread", limit)

    def send_sms(self, recipient, text, confirm=False) -> dict:
        boolean(confirm, "confirm")
        message(recipient, text)
        if not confirm:
            return {"state": "preview", "account_email": self.account_email,
                    "recipient": recipient, "text": text, "requires_confirmation": True}
        self._require_account()
        return self._backend().send(recipient, text)
