"""MCP tools served by the SDK's standard stdio transport."""

from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import StrictBool, StrictInt, StrictStr

from google_voice_mcp.client import GoogleVoiceClient


def create_server(client=None) -> FastMCP:
    server = FastMCP("google-voice-mcp")
    voice = client if client is not None else GoogleVoiceClient()

    @server.tool()
    def doctor() -> dict[str, Any]:
        """Inspect Chrome and the selected Voice account without reading history."""
        return voice.doctor()

    @server.tool()
    def list_sms(limit: StrictInt = 10, unread_only: StrictBool = False) -> dict[str, Any]:
        """Read bounded visible SMS summaries; requires configured expected account."""
        return voice.list_sms(limit=limit, unread_only=unread_only)

    @server.tool()
    def list_calls(limit: StrictInt = 10) -> dict[str, Any]:
        """Read bounded visible call history in the selected tab."""
        return voice.list_calls(limit=limit)

    @server.tool()
    def list_voicemails(limit: StrictInt = 10) -> dict[str, Any]:
        """Read bounded visible voicemail summaries in the selected tab."""
        return voice.list_voicemails(limit=limit)

    @server.tool()
    def read_thread(limit: StrictInt = 20) -> dict[str, Any]:
        """Read bounded messages from the currently selected conversation."""
        return voice.read_thread(limit=limit)

    @server.tool()
    def send_sms(to: StrictStr, message: StrictStr, confirm: StrictBool = False) -> dict[str, Any]:
        """Preview locally. Set confirm=true only after user approves exact recipient and text.

        Execution requires configured expected account and the matching selected one-to-one
        thread with no existing draft. Never retry an outcome_unknown result.
        """
        return voice.send_sms(recipient=to, text=message, confirm=confirm)

    return server


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
