"""A real SDK client/server handshake over subprocess stdio; preview is offline."""
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_stdio_protocol_initialize_list_preview():
    env = dict(os.environ)
    for name in ("ACCOUNT", "PORT", "TAB_ID"):
        env.pop("GOOGLE_VOICE_" + name, None)
    # An unreachable configured port plus an audit hook prohibit network access.
    env["GOOGLE_VOICE_PORT"] = "1"
    parameters = StdioServerParameters(command=sys.executable,
        args=["-c", "import sys, runpy\ndef offline(event, args):\n    if event in ('socket.connect', 'socket.getaddrinfo'):\n        raise RuntimeError('Network forbidden during protocol test')\nsys.addaudithook(offline)\nrunpy.run_module('google_voice_mcp.server', run_name='__main__')"], env=env)
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "google-voice-mcp"
            listing = await session.list_tools()
            assert len(listing.tools) == 6
            result = await session.call_tool("send_sms", {"to": "+12025550123", "message": "protocol preview"})
            assert not result.isError
            assert result.structuredContent["state"] == "preview"
            assert result.structuredContent["text"] == "protocol preview"
            for invalid in ("true", 1):
                rejected = await session.call_tool("send_sms", {"to": "+12025550123", "message": "hi", "confirm": invalid})
                assert rejected.isError
