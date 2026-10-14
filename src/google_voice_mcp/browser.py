"""Bounded DOM access to an exact tab in the user's existing Chrome session."""
from __future__ import annotations

import json
import re
from importlib.resources import files
from urllib.parse import urlsplit

from own_chrome import cdp


class VoiceError(RuntimeError):
    """A safe, actionable error with no browser response or message content."""


_ERRORS = {
    'origin': 'The tab is no longer on Google Voice.',
    'account_unknown': 'Cannot uniquely verify the signed-in Google Account.',
    'account_mismatch': 'The Google Account does not match the expected account.',
    'section': 'Open the requested section in Google Voice first.',
    'unsupported_dom': 'The current Google Voice layout could not be verified.',
    'recipient': 'Open an existing one-to-one thread whose header shows the exact international recipient.',
    'draft': 'An existing draft is present; it was not changed.',
    'changed': 'Account, thread, recipient, or draft changed; sending was refused.',
    'send_disabled': 'The send button is unavailable; the draft may remain. Inspect it before continuing.',
}


def _voice_url(value):
    try:
        url = urlsplit(value)
        return url.scheme == 'https' and url.hostname == 'voice.google.com' and url.port in (None, 443) and not url.username
    except ValueError:
        return False


class VoiceBrowser:
    def __init__(self, account_email=None, port=9222, tab_id=None):
        if type(port) is not int or not 1 <= port <= 65535:
            raise VoiceError('Port must be an integer from 1 to 65535.')
        self.account_email = account_email
        self.port = port
        self.tab_id = tab_id

    def _page(self):
        try:
            cdp.describe(self.port)
            pages = [p for p in cdp.pages(self.port) if _voice_url(p.get('url', ''))]
        except Exception:
            raise VoiceError('Chrome connection failed. Open your existing Chrome debugging session.') from None
        if self.tab_id is not None:
            pages = [p for p in pages if p.get('id') == self.tab_id]
        if len(pages) != 1:
            raise VoiceError('Select exactly one open Google Voice tab using --tab-id.')
        page = pages[0]
        if not isinstance(page.get('id'), str) or not page['id']:
            raise VoiceError('Google Voice tab has no valid identifier.')
        try:
            ws = urlsplit(page.get('webSocketDebuggerUrl', ''))
            safe = (ws.scheme == 'ws' and ws.hostname in ('localhost', '127.0.0.1')
                    and ws.port == self.port and not ws.username and not ws.password)
        except ValueError:
            safe = False
        if not safe:
            raise VoiceError('Google Voice tab has no trusted local debugging endpoint.')
        return page

    def _run(self, page, action, **kwargs):
        args = {'action': action, 'account_email': self.account_email, **kwargs}
        source = files('google_voice_mcp').joinpath('scripts/voice.js').read_text(encoding='utf-8')
        expression = f'({source})({json.dumps(args, ensure_ascii=True)})'
        try:
            result = cdp.evaluate(self.port, expression, page=page)
        except Exception:
            if action == 'send':
                return {'state': 'outcome_unknown', 'delivery_confirmed': False,
                        'detail': 'Browser response was lost. Inspect the thread and draft; do not retry automatically.'}
            raise VoiceError('Browser operation failed. Inspect the selected Google Voice tab.') from None
        if isinstance(result, dict) and 'error' in result:
            code = result['error']
            raise VoiceError(_ERRORS.get(code, 'Google Voice layout could not be verified.')
                             if isinstance(code, str) else 'Google Voice layout could not be verified.')
        valid = isinstance(result, dict)
        if action == 'send':
            if not valid or result.get('state') not in ('submitted', 'outcome_unknown') or result.get('delivery_confirmed') is not False:
                return {'state': 'outcome_unknown', 'delivery_confirmed': False}
        else:
            if not valid or not isinstance(result.get('account_email'), str) or 'section' not in result:
                raise VoiceError('Google Voice returned an unrecognized result.')
            if action == 'read' and (not isinstance(result.get('items'), list) or result.get('limited_to_visible') is not True):
                raise VoiceError('Google Voice returned an unrecognized result.')
        return result

    def inspect(self):
        page = self._page()
        return {**self._run(page, 'inspect'), 'tab_id': page['id'],
                'backend': 'chrome'}

    def read(self, kind, limit, unread_only=False):
        if not self.account_email:
            raise VoiceError('An expected Google Voice account is required.')
        if kind not in ('sms', 'calls', 'voicemails', 'thread'):
            raise VoiceError('Unsupported read kind.')
        if type(limit) is not int or not 1 <= limit <= 100 or type(unread_only) is not bool:
            raise VoiceError('Limit must be an integer from 1 to 100 and unread_only must be boolean.')
        return self._run(self._page(), 'read', kind=kind, limit=limit, unread_only=unread_only)

    def send(self, recipient, text):
        if not self.account_email:
            raise VoiceError('An expected Google Voice account is required.')
        if not isinstance(recipient, str) or not re.fullmatch(r'\+[1-9][0-9]{7,14}', recipient):
            raise VoiceError('Recipient must be an international phone number such as +15551234567.')
        if not isinstance(text, str) or not text.strip() or len(text) > 1600:
            raise VoiceError('Text must contain 1 to 1600 characters.')
        return self._run(self._page(), 'send', recipient=recipient, text=text)
