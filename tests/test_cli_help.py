from typer.testing import CliRunner

from google_voice_mcp.cli import app

runner = CliRunner()


def test_help_short_flag_on_root_and_subcommands():
    for args in (["-h"], ["--help"], ["sms", "-h"], ["send", "-h"], ["serve", "-h"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, (args, result.output)
        assert "Usage" in result.output
    sms_help = runner.invoke(app, ["sms", "-h"])
    assert "-j" in sms_help.output and "--json" in sms_help.output
