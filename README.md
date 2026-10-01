# google-voice-mcp

Google Voice CLI & MCP (Model Context Protocol) server for SMS, call history, and voicemail automation.

## Features

- **CLI Surface (`gvoice`)**: List SMS, send SMS messages, view call history, and retrieve transcribed voicemails.
- **MCP Server (`google-voice-mcp serve`)**: Agent-callable tool interface exposing `list_sms`, `send_sms`, `list_calls`, and `list_voicemails` over standard I/O (stdio).
- **Type-safe & Tested**: Built with Pydantic, Typer, Rich, and standard Python MCP SDK.

## Installation

```bash
pip install -e .
```

Or run via uv:
```bash
uv pip install -e .
```

## Usage

### CLI Commands

```bash
# List recent SMS messages
gvoice sms --limit 5

# Send an SMS
gvoice send +16262344927 "Hey Joe, testing the MCP server"

# View call logs
gvoice calls --limit 10

# View voicemails and transcripts
gvoice voicemails --limit 5
```

### Running as MCP Server

Add to your MCP configuration (e.g. `~/.cursor/mcp.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "google-voice": {
      "command": "gvoice",
      "args": ["serve"]
    }
  }
}
```

## License

MIT
