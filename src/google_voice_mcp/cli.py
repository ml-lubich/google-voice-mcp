"""Google Voice CLI. All output is JSON, including operational errors."""

import json

from typer._click.exceptions import ClickException
import typer
from typer.core import TyperGroup

from google_voice_mcp.browser import VoiceError
from google_voice_mcp.client import GoogleVoiceClient
from google_voice_mcp.server import create_server


class JsonGroup(TyperGroup):
    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **{**kwargs, "standalone_mode": False})
        except ClickException as error:
            typer.echo(json.dumps({"error": error.format_message()}))
            raise SystemExit(error.exit_code) from None


app = typer.Typer(cls=JsonGroup, help="Google Voice through existing Chrome. Output is JSON.",
                  context_settings={"help_option_names": ["-h", "--help"]})


@app.callback()
def configure(ctx: typer.Context,
              account: str | None = typer.Option(None, "--account", help="Expected account email (or GOOGLE_VOICE_ACCOUNT)"),
              port: int | None = typer.Option(None, "--port", help="Chrome CDP port (or GOOGLE_VOICE_PORT)"),
              tab_id: str | None = typer.Option(None, "--tab-id", help="Exact Chrome tab ID (or GOOGLE_VOICE_TAB_ID)"),
              as_json: bool = typer.Option(False, "--json", "-j", help="JSON output (always enabled)")):
    ctx.obj = {"account_email": account, "port": port, "tab_id": tab_id}


def _run(ctx, operation, **kwargs):
    try:
        result = getattr(GoogleVoiceClient(**ctx.obj), operation)(**kwargs)
    except VoiceError as error:
        raise ClickException(str(error)) from None
    typer.echo(json.dumps(result, ensure_ascii=False))


@app.command()
def doctor(ctx: typer.Context, as_json: bool = typer.Option(False, "--json", "-j")):
    """Inspect browser connection and account identity."""
    _run(ctx, "doctor")


@app.command()
def sms(ctx: typer.Context, limit: int = typer.Option(10, "--limit", "-l"),
        unread: bool = typer.Option(False, "--unread", "-u"),
        as_json: bool = typer.Option(False, "--json", "-j")):
    """List bounded visible SMS summaries."""
    _run(ctx, "list_sms", limit=limit, unread_only=unread)


@app.command()
def calls(ctx: typer.Context, limit: int = typer.Option(10, "--limit", "-l"),
          as_json: bool = typer.Option(False, "--json", "-j")):
    """List bounded visible call history."""
    _run(ctx, "list_calls", limit=limit)


@app.command()
def voicemails(ctx: typer.Context, limit: int = typer.Option(10, "--limit", "-l"),
              as_json: bool = typer.Option(False, "--json", "-j")):
    """List bounded visible voicemail summaries."""
    _run(ctx, "list_voicemails", limit=limit)


@app.command()
def thread(ctx: typer.Context, limit: int = typer.Option(20, "--limit", "-l"),
           as_json: bool = typer.Option(False, "--json", "-j")):
    """Read bounded messages in the selected conversation."""
    _run(ctx, "read_thread", limit=limit)


@app.command()
def send(ctx: typer.Context, to: str, message: str,
         confirm: bool = typer.Option(False, "--confirm", help="Execute the exact user-approved message"),
         as_json: bool = typer.Option(False, "--json", "-j")):
    """Preview locally; --confirm submits to the matching selected thread."""
    _run(ctx, "send_sms", recipient=to, text=message, confirm=confirm)


@app.command()
def serve(ctx: typer.Context):
    """Start MCP over stdio."""
    try:
        client = GoogleVoiceClient(**ctx.obj)
    except VoiceError as error:
        raise ClickException(str(error)) from None
    create_server(client).run(transport="stdio")


if __name__ == "__main__":
    app()
