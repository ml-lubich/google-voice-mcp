"""CLI interface for google-voice-mcp."""

import json
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from google_voice_mcp.client import GoogleVoiceClient
from google_voice_mcp.server import create_server

app = typer.Typer(help="Google Voice CLI and MCP Server")
console = Console()


@app.command()
def sms(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of messages to list"),
    unread: bool = typer.Option(False, "--unread", "-u", help="Show unread messages only"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List recent SMS messages."""
    client = GoogleVoiceClient()
    messages = client.list_sms(limit=limit, unread_only=unread)
    if as_json:
        console.print_json(data=[m.model_dump(mode="json") for m in messages])
        return

    table = Table(title="Google Voice — SMS Messages")
    table.add_column("ID", style="dim")
    table.add_column("Direction", style="cyan")
    table.add_column("Contact", style="green")
    table.add_column("Message", style="white")
    table.add_column("Time", style="magenta")

    for m in messages:
        contact = m.recipient if m.direction == "outgoing" else m.sender
        table.add_row(
            m.id,
            m.direction.upper(),
            contact,
            m.text,
            m.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command()
def send(
    to: str = typer.Argument(..., help="Recipient phone number"),
    message: str = typer.Argument(..., help="SMS message text"),
):
    """Send an SMS message."""
    client = GoogleVoiceClient()
    msg = client.send_sms(recipient=to, text=message)
    console.print(f"[green]✓ Sent SMS to {to}:[/green] {message} (id: {msg.id})")


@app.command()
def calls(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of calls to list"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List recent call history."""
    client = GoogleVoiceClient()
    call_records = client.list_calls(limit=limit)
    if as_json:
        console.print_json(data=[c.model_dump(mode="json") for c in call_records])
        return

    table = Table(title="Google Voice — Call History")
    table.add_column("ID", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Number", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Time", style="magenta")

    for c in call_records:
        table.add_row(
            c.id,
            c.call_type.value.upper(),
            c.phone_number,
            f"{c.duration_seconds}s",
            c.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command()
def voicemails(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of voicemails to list"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List voicemails and transcripts."""
    client = GoogleVoiceClient()
    vms = client.list_voicemails(limit=limit)
    if as_json:
        console.print_json(data=[v.model_dump(mode="json") for v in vms])
        return

    table = Table(title="Google Voice — Voicemails")
    table.add_column("ID", style="dim")
    table.add_column("From", style="green")
    table.add_column("Transcript", style="white")
    table.add_column("Duration", style="yellow")
    table.add_column("Time", style="magenta")

    for v in vms:
        table.add_row(
            v.id,
            v.sender,
            v.transcript or "(No transcript)",
            f"{v.duration_seconds}s",
            v.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command()
def serve():
    """Start the Model Context Protocol (MCP) server over stdio."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    app()
