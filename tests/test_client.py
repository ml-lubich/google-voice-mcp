import pytest

from google_voice_mcp.browser import VoiceError
from google_voice_mcp.client import GoogleVoiceClient


class Browser:
    def __init__(self, **config):
        self.config = config
        self.actions = []

    def inspect(self):
        return {"account_email": "test@example.org", "backend": "chrome"}

    def read(self, kind, limit, unread_only=False):
        self.actions.append((kind, limit, unread_only))
        return {"items": [], "limited_to_visible": True}

    def send(self, recipient, text):
        self.actions.append((recipient, text))
        return {"state": "outcome_unknown"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("ACCOUNT", "PORT", "TAB_ID"):
        monkeypatch.delenv("GOOGLE_VOICE_" + name, raising=False)


def test_preview_has_no_backend_or_auth(monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("Preview touched Chrome")
    monkeypatch.setattr("google_voice_mcp.client.VoiceBrowser", forbidden)
    client = GoogleVoiceClient()
    assert client.send_sms("+12025550123", "Exact text\n  ") == {
        "state": "preview", "account_email": None, "recipient": "+12025550123",
        "text": "Exact text\n  ", "requires_confirmation": True}


def test_env_and_lazy_browser(monkeypatch):
    monkeypatch.setenv("GOOGLE_VOICE_ACCOUNT", " test@example.org ")
    monkeypatch.setenv("GOOGLE_VOICE_PORT", "9333")
    monkeypatch.setenv("GOOGLE_VOICE_TAB_ID", "abc")
    monkeypatch.setattr("google_voice_mcp.client.VoiceBrowser", Browser)
    client = GoogleVoiceClient()
    assert client.doctor()["backend"] == "chrome"
    assert client._backend().config == {"account_email": "test@example.org", "port": 9333, "tab_id": "abc"}
    assert client.doctor()["account_email"] == "test@example.org"


def test_read_routing_and_send_preserves_unknown():
    browser = Browser()
    client = GoogleVoiceClient("test@example.org", 9222, "abc", browser)
    for method in (client.list_sms, client.list_calls, client.list_voicemails, client.read_thread):
        assert method()["items"] == []
    client.list_sms(100, True)
    assert browser.actions == [("sms", 10, False), ("calls", 10, False),
                               ("voicemails", 10, False), ("thread", 20, False), ("sms", 100, True)]
    assert client.send_sms("+12025550123", "approved", True)["state"] == "outcome_unknown"
    assert browser.actions[-1] == ("+12025550123", "approved")


@pytest.mark.parametrize("method,args", [("list_sms", ()), ("list_calls", ()),
    ("list_voicemails", ()), ("read_thread", ()), ("send_sms", ("+12025550123", "hello", True))])
def test_account_required(method, args):
    with pytest.raises(VoiceError, match="GOOGLE_VOICE_ACCOUNT"):
        getattr(GoogleVoiceClient(browser=Browser()), method)(*args)


@pytest.mark.parametrize("value", [0, -1, 101, True, 1.5, "10", None])
def test_strict_limits(value):
    with pytest.raises(VoiceError, match="limit"):
        GoogleVoiceClient("test@example.org", browser=Browser()).list_sms(value)


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_strict_boolean(value):
    client = GoogleVoiceClient()
    with pytest.raises(VoiceError, match="confirm"):
        client.send_sms("+12025550123", "hi", value)
    with pytest.raises(VoiceError, match="unread_only"):
        client.list_sms(unread_only=value)


@pytest.mark.parametrize("recipient", [None, "", "12025550123", "+02025550123", "+1 2025550123", "+123", "+1234567890123456"])
def test_recipient_validation(recipient):
    with pytest.raises(VoiceError, match="recipient"):
        GoogleVoiceClient().send_sms(recipient, "hello")


@pytest.mark.parametrize("text", [None, "", "  ", "x" * 1601])
def test_text_validation(text):
    with pytest.raises(VoiceError, match="text"):
        GoogleVoiceClient().send_sms("+12025550123", text)


@pytest.mark.parametrize("kwargs", [{"account_email": " "}, {"account_email": 4},
    {"port": True}, {"port": 0}, {"port": 65536}, {"tab_id": 3}, {"tab_id": " "}])
def test_config_validation(kwargs):
    with pytest.raises(VoiceError):
        GoogleVoiceClient(**kwargs)


def test_bad_env_port(monkeypatch):
    monkeypatch.setenv("GOOGLE_VOICE_PORT", "bad")
    with pytest.raises(VoiceError, match="GOOGLE_VOICE_PORT"):
        GoogleVoiceClient()
