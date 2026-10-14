from typer.testing import CliRunner
from google_voice_mcp.cli import app


def test_help_short_flag_on_root_and_subcommands():
    runner = CliRunner()
    for command in ([], ["sms"], ["send"], ["calls"], ["voicemails"], ["thread"], ["doctor"], ["serve"]):
        for flag in ("-h", "--help"):
            result = runner.invoke(app, command + [flag])
            assert result.exit_code == 0, result.output
            assert "Usage" in result.output
    result = runner.invoke(app, ["sms", "-h"])
    assert "-j" in result.output and "--json" in result.output
