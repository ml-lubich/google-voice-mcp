"""Browser boundary tests: no real Chrome or personal messages are accessed."""
import json
from unittest.mock import Mock

import pytest

from google_voice_mcp import browser
from google_voice_mcp.browser import VoiceBrowser, VoiceError

ACCOUNT = 'owner@example.test'
PAGE = {'id': 'exact', 'url': 'https://voice.google.com/u/1/messages',
        'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/exact'}


@pytest.fixture
def cdp(monkeypatch):
    fake = Mock()
    fake.pages.return_value = [PAGE]
    fake.evaluate.return_value = {'account_email': ACCOUNT, 'section': 'messages'}
    monkeypatch.setattr(browser, 'cdp', fake)
    return fake


def test_inspect_exact_page(cdp):
    result = VoiceBrowser(ACCOUNT).inspect()
    assert result['backend'] == 'chrome'
    assert result['tab_id'] == 'exact'
    cdp.describe.assert_called_once_with(9222)
    assert cdp.evaluate.call_args.kwargs == {'page': PAGE}
    assert ACCOUNT in cdp.evaluate.call_args.args[1]


@pytest.mark.parametrize('pages', [[], [PAGE, dict(PAGE, id='second')],
    [dict(PAGE, url='https://evil.test/voice.google.com')],
    [dict(PAGE, url='https://sub.voice.google.com/')],
    [dict(PAGE, url='http://voice.google.com/')], [dict(PAGE, url='https://[')]])
def test_unsafe_or_ambiguous_pages(cdp, pages):
    cdp.pages.return_value = pages
    with pytest.raises(VoiceError):
        VoiceBrowser().inspect()
    cdp.evaluate.assert_not_called()


def test_explicit_tab(cdp):
    cdp.pages.return_value = [dict(PAGE, id='other'), PAGE]
    assert VoiceBrowser(tab_id='exact').inspect()['tab_id'] == 'exact'
    with pytest.raises(VoiceError):
        VoiceBrowser(tab_id='absent').inspect()


@pytest.mark.parametrize('ws', ['', 'ws://evil.test:9222/x', 'wss://127.0.0.1:9222/x',
    'ws://127.0.0.1:9223/x', 'ws://user@localhost:9222/x', 'ws://['])
def test_websocket_rejected(cdp, ws):
    cdp.pages.return_value = [dict(PAGE, webSocketDebuggerUrl=ws)]
    with pytest.raises(VoiceError):
        VoiceBrowser().inspect()
    cdp.evaluate.assert_not_called()


def test_read(cdp):
    cdp.evaluate.return_value = {'items': [], 'account_email': ACCOUNT, 'section': 'messages',
                                 'limited_to_visible': True}
    assert VoiceBrowser(ACCOUNT).read('sms', 7, True)['items'] == []
    expression = cdp.evaluate.call_args.args[1]
    assert '"limit": 7' in expression and '"unread_only": true' in expression


@pytest.mark.parametrize('kwargs', [{'kind': 'invalid', 'limit': 1}, {'kind': 'sms', 'limit': True},
    {'kind': 'sms', 'limit': 0}, {'kind': 'sms', 'limit': 101},
    {'kind': 'sms', 'limit': 1, 'unread_only': 'false'}])
def test_invalid_read(cdp, kwargs):
    with pytest.raises(VoiceError):
        VoiceBrowser(ACCOUNT).read(**kwargs)
    cdp.describe.assert_not_called()


def test_account_required_read_send(cdp):
    with pytest.raises(VoiceError):
        VoiceBrowser().read('sms', 1)
    with pytest.raises(VoiceError):
        VoiceBrowser().send('+15551234567', 'hello')
    cdp.describe.assert_not_called()


@pytest.mark.parametrize('recipient,text', [('5551234567', 'hello'), ('+0123', 'hello'),
    ('+15551234567', ''), ('+15551234567', '   '), ('+15551234567', None)])
def test_invalid_send(cdp, recipient, text):
    with pytest.raises(VoiceError):
        VoiceBrowser(ACCOUNT).send(recipient, text)
    cdp.describe.assert_not_called()


def test_send_once(cdp):
    cdp.evaluate.return_value = {'state': 'submitted', 'delivery_confirmed': False}
    assert VoiceBrowser(ACCOUNT).send('+15551234567', 'hello')['state'] == 'submitted'
    assert cdp.evaluate.call_count == 1


def test_uncertain_send_transport(cdp):
    cdp.evaluate.side_effect = RuntimeError('private data')
    result = VoiceBrowser(ACCOUNT).send('+15551234567', 'hello')
    assert result['state'] == 'outcome_unknown'
    assert 'private data' not in str(result)
    assert cdp.evaluate.call_count == 1


@pytest.mark.parametrize('reply', [None, 'raw private', {'error': 'account_mismatch'}, {'error': 'private data'}])
def test_bad_dom_reply(cdp, reply):
    cdp.evaluate.return_value = reply
    with pytest.raises(VoiceError) as exc:
        VoiceBrowser(ACCOUNT).inspect()
    assert 'private data' not in str(exc.value)


def test_cdp_errors_redacted(cdp):
    cdp.describe.side_effect = RuntimeError('private body')
    with pytest.raises(VoiceError, match='Chrome connection failed') as exc:
        VoiceBrowser().inspect()
    assert 'private' not in str(exc.value)
    cdp.describe.side_effect = None
    cdp.evaluate.side_effect = RuntimeError('private body')
    with pytest.raises(VoiceError, match='Browser operation failed'):
        VoiceBrowser().inspect()


@pytest.mark.parametrize('port', [True, 0, 65536, '9222'])
def test_invalid_port(port):
    with pytest.raises(VoiceError):
        VoiceBrowser(port=port)


def test_send_missing_response_is_unknown(cdp):
    cdp.evaluate.return_value = None
    assert VoiceBrowser(ACCOUNT).send('+15551234567', 'hello')['state'] == 'outcome_unknown'


@pytest.mark.parametrize('reply', [{}, {'error': []}, {'section': 'messages'},
    {'account_email': ACCOUNT}, {'account_email': ACCOUNT, 'section': 'messages'}])
def test_malformed_read_results(cdp, reply):
    cdp.evaluate.return_value = reply
    with pytest.raises(VoiceError):
        VoiceBrowser(ACCOUNT).read('sms', 1)


def test_missing_tab_identifier(cdp):
    cdp.pages.return_value = [dict(PAGE, id=None)]
    with pytest.raises(VoiceError):
        VoiceBrowser().inspect()
