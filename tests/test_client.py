import pytest
from google_voice_mcp.client import GoogleVoiceClient
from google_voice_mcp.models import CallType


def test_client_init():
    client = GoogleVoiceClient()
    assert len(client.list_sms()) > 0
    assert len(client.list_calls()) > 0
    assert len(client.list_voicemails()) > 0


def test_send_sms():
    client = GoogleVoiceClient()
    msg = client.send_sms("+16262344927", "Test automated message")
    assert msg.recipient == "+16262344927"
    assert msg.text == "Test automated message"
    assert msg.direction == "outgoing"

    all_msgs = client.list_sms(limit=5)
    assert any(m.id == msg.id for m in all_msgs)


def test_list_sms_unread():
    client = GoogleVoiceClient()
    all_msgs = client.list_sms(unread_only=True)
    assert all(not m.is_read for m in all_msgs)


def test_list_calls():
    client = GoogleVoiceClient()
    calls = client.list_calls(limit=1)
    assert len(calls) == 1
    assert calls[0].call_type == CallType.INCOMING
