"""MCP Server implementation for Google Voice."""

import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    EmbeddedResource,
)

from google_voice_mcp.client import GoogleVoiceClient


def create_server() -> Server:
    app = Server("google-voice-mcp")
    client = GoogleVoiceClient()

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_sms",
                description="List recent SMS text messages from Google Voice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of messages to retrieve (default: 10)",
                            "default": 10,
                        },
                        "unread_only": {
                            "type": "boolean",
                            "description": "Filter for unread messages only",
                            "default": False,
                        },
                    },
                },
            ),
            Tool(
                name="send_sms",
                description="Send an SMS message to a phone number via Google Voice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient phone number (e.g. +16262344927)",
                        },
                        "message": {
                            "type": "string",
                            "description": "Text body of the SMS",
                        },
                    },
                    "required": ["to", "message"],
                },
            ),
            Tool(
                name="list_calls",
                description="List incoming, outgoing, and missed call history from Google Voice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of call logs to retrieve (default: 10)",
                            "default": 10,
                        },
                    },
                },
            ),
            Tool(
                name="list_voicemails",
                description="List voicemails along with transcription text",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of voicemails to retrieve (default: 10)",
                            "default": 10,
                        },
                    },
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
        args = arguments or {}

        if name == "list_sms":
            limit = args.get("limit", 10)
            unread_only = args.get("unread_only", False)
            msgs = client.list_sms(limit=limit, unread_only=unread_only)
            result = [m.model_dump(mode="json") for m in msgs]
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "send_sms":
            to = args["to"]
            message = args["message"]
            msg = client.send_sms(recipient=to, text=message)
            import json
            return [TextContent(type="text", text=json.dumps(msg.model_dump(mode="json"), indent=2))]

        elif name == "list_calls":
            limit = args.get("limit", 10)
            calls = client.list_calls(limit=limit)
            result = [c.model_dump(mode="json") for c in calls]
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_voicemails":
            limit = args.get("limit", 10)
            vms = client.list_voicemails(limit=limit)
            result = [v.model_dump(mode="json") for v in vms]
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    def run():
        async def main():
            async with stdio_server() as (read_stream, write_stream):
                await app.run(
                    read_stream,
                    write_stream,
                    app.create_initialization_options(),
                )

        asyncio.run(main())

    app.run = run
    return app
