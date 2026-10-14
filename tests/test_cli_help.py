import pytest
from rich.text import Text
from typer.testing import CliRunner
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
