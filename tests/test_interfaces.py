import json
import runpy

import pytest
from typer.testing import CliRunner

from google_voice_mcp import cli, server
from google_voice_mcp.client import GoogleVoiceClient
from test_client import Browser


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.delenv("GOOGLE_VOICE_ACCOUNT", raising=False)
    monkeypatch.delenv("GOOGLE_VOICE_PORT", raising=False)
    return CliRunner()


def test_cli_preview_and_errors(runner):
    result = runner.invoke(cli.app, ["send", "+12025550123", "hi", "-j"])
    assert result.exit_code == 0
    assert json.loads(result.output)["state"] == "preview"
    for args in (["sms"], ["send", "bad", "hello"], ["sms", "-l", "bad"],
                 ["sms", "-l", "0"], ["missing"], ["send"], ["serve", "--bad"],
                 ["--port", "0", "serve"]):
        result = runner.invoke(cli.app, args)
        assert result.exit_code != 0, (args, result.output)
        assert "error" in json.loads(result.output)


def test_cli_routing(runner, monkeypatch):
    browser = Browser()
    captured = []
    def factory(**kwargs):
        captured.append(kwargs)
        return GoogleVoiceClient(**kwargs, browser=browser)
    monkeypatch.setattr(cli, "GoogleVoiceClient", factory)
    for name in ("doctor", "sms", "calls", "voicemails", "thread"):
        result = runner.invoke(cli.app, ["--account", "test@example.org", "--port", "9333", "--tab-id", "abc", "--json", name])
        assert result.exit_code == 0, result.output
        assert isinstance(json.loads(result.output), dict)
    assert captured[0] == {"account_email": "test@example.org", "port": 9333, "tab_id": "abc"}


def test_serve_and_server_main(runner, monkeypatch):
    calls = []
    class Server:
        def run(self, **kwargs):
            calls.append(kwargs)
    monkeypatch.setattr(cli, "create_server", lambda client: Server())
    assert runner.invoke(cli.app, ["serve"]).exit_code == 0
    monkeypatch.setattr(server, "create_server", lambda: Server())
    server.main()
    assert calls == [{"transport": "stdio"}, {"transport": "stdio"}]


@pytest.mark.asyncio
async def test_mcp_tools_and_strict_arguments(monkeypatch):
    browser = Browser()
    app = server.create_server(GoogleVoiceClient("test@example.org", browser=browser))
    tools = await app.list_tools()
    assert {t.name for t in tools} == {"doctor", "list_sms", "list_calls", "list_voicemails", "read_thread", "send_sms"}
    for name in ("doctor", "list_sms", "list_calls", "list_voicemails", "read_thread"):
        await app.call_tool(name, {})
    result = await app.call_tool("send_sms", {"to": "+12025550123", "message": "hello"})
    assert "preview" in str(result)
    for args in ({"confirm": "true"}, {"confirm": 1}):
        with pytest.raises(Exception, match="boolean"):
            await app.call_tool("send_sms", {"to": "+12025550123", "message": "hello", **args})
    for name, args in (("list_sms", {"unread_only": "false"}), ("list_calls", {"limit": "10"}),
                       ("list_calls", {"limit": True}), ("list_calls", {"limit": 0})):
        with pytest.raises(Exception):
            await app.call_tool(name, args)
    monkeypatch.delenv("GOOGLE_VOICE_ACCOUNT", raising=False)
    assert server.create_server() is not None


def test_module_entrypoints(monkeypatch):
    # Execute actual module guards, replacing only their terminal/stdio runners.
    import typer
    from mcp.server.fastmcp import FastMCP
    called = []
    monkeypatch.setattr(typer.Typer, "__call__", lambda self: called.append("cli"))
    monkeypatch.setattr(FastMCP, "run", lambda self, **kwargs: called.append(kwargs))
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        runpy.run_module("google_voice_mcp.cli", run_name="__main__")
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        runpy.run_module("google_voice_mcp.server", run_name="__main__")
    assert called == ["cli", {"transport": "stdio"}]
