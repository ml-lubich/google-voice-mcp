import json

import pytest
from rich.text import Text
from typer.testing import CliRunner
from google_voice_mcp import __version__
from google_voice_mcp.cli import app


@pytest.mark.parametrize("force_color", [False, True])
def test_help_short_flag_on_root_and_subcommands(monkeypatch, force_color):
    if force_color:
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("TERM", "xterm-256color")
    runner = CliRunner()
    for command in ([], ["sms"], ["send"], ["calls"], ["voicemails"], ["thread"], ["doctor"], ["serve"]):
        for flag in ("-h", "--help"):
            result = runner.invoke(app, command + [flag], color=force_color)
            assert result.exit_code == 0, result.output
            assert "Usage" in Text.from_ansi(result.output).plain
    result = runner.invoke(app, ["sms", "-h"], color=force_color)
    output = Text.from_ansi(result.output).plain
    assert "-j" in output and "--json" in output


def test_agent_schema_reports_registered_cli_commands_and_parameters():
    result = CliRunner().invoke(app, ["agent", "schema"])

    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert schema["version"] == __version__
    assert schema["tool"] == "gvoice"
    assert schema["mcp"] == "google-voice-mcp"
    assert {param["name"] for param in schema["global_params"]} == {
        "account",
        "port",
        "tab_id",
        "as_json",
    }
    commands = {command["name"]: command for command in schema["commands"]}
    assert set(commands) == {
        "doctor",
        "sms",
        "calls",
        "voicemails",
        "thread",
        "send",
        "serve",
        "agent schema",
    }
    send_params = {param["name"]: param for param in commands["send"]["params"]}
    assert send_params["to"]["required"] is True
    assert "--confirm" in send_params["confirm"]["flags"]
