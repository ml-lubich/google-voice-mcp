# google-voice-mcp

Google Voice CLI and MCP server using an existing signed-in Chrome session. The `gvoice` CLI and MCP tools share one client. This replaces the original in-memory demonstration: live operations require an actual browser connection and never substitute sample messages.

## Why this does not use Google Cloud OAuth

Google Cloud does not offer a supported public Google Voice API for a personal Voice inbox, SMS sending, call history, or voicemail retrieval. Google Sheets has an official API and OAuth scopes; its OAuth token does not grant Voice access. Google's Speech-to-Text, Text-to-Speech, and other voice-related Cloud products are different services, not an API to your Google Voice number.

We reuse the Sheets integration's architecture (shared CLI/MCP client, local previews, explicit confirmation, diagnostics, and synthetic testing), not its Google Cloud connection. Authentication stays in Chrome. The tool does not extract cookies, reuse Sheets credentials, or call undocumented Voice endpoints. See [Google's OAuth scope directory](https://developers.google.com/identity/protocols/oauth2/scopes) and [Voice's documented messaging interface](https://support.google.com/voice/answer/115116).

## Setup

```sh
uv tool install git+https://github.com/ml-lubich/google-voice-mcp.git
```

Use the Chrome profile you have already signed into with remote debugging enabled. The pinned `own-chrome` dependency connects to the existing browser; it never launches or logs into a browser. See [connection setup](docs/SETUP.md).

```sh
# Discover connection/account state without reading messages.
gvoice doctor

# Pin the expected account before any conversation read or confirmed send.
export GOOGLE_VOICE_ACCOUNT='your-account@example.com'
gvoice sms --limit 5 --json
gvoice thread --limit 10 --json
gvoice calls --limit 5 --json
gvoice voicemails --limit 5 --json

# Local preview only: no browser interaction, draft change, or send.
gvoice send +12025550123 'Example message'
# Run only after approval of the exact account, recipient, and text:
gvoice send +12025550123 'Example message' --confirm
```

Reads inspect only the currently loaded relevant view; open Messages, Calls, or Voicemail in Voice as appropriate. `sms` returns visible conversation summaries; `thread` reads the currently selected conversation. Results report that they are limited to visible content. They are not a full inbox export. Displayed times remain displayed times; missing IDs, timestamps, and durations are not invented.

Confirmed sends support the already-open one-to-one conversation only. The account, thread URL, and displayed recipient must agree. Existing drafts are not overwritten, group conversations and mismatched recipients are rejected, and a send is clicked at most once. Read-back evidence can establish that the message appeared in the UI, not carrier delivery. An uncertain result must be inspected before any further action; never blindly retry.

## MCP

```json
{
  "mcpServers": {
    "google-voice": {
      "command": "gvoice",
      "args": ["serve"],
      "env": {"GOOGLE_VOICE_ACCOUNT": "your-account@example.com"}
    }
  }
}
```

Tools include connection diagnostics, SMS summaries, the selected thread, calls, voicemails, and `send_sms`. Sending defaults to a local preview; `confirm: true` is execution intent and still requires the user's authorization. Neither installation nor starting the MCP server sends messages. The agent skill is [skills/google-voice/SKILL.md](skills/google-voice/SKILL.md).

## Development

```sh
uv sync --locked --extra dev
uv run pytest --cov=google_voice_mcp --cov-branch --cov-report=term-missing
npm ci --ignore-scripts --no-audit --no-fund
npm test
uv build
```

Python tests exercise the client, browser boundary, CLI, and real MCP stdio protocol. JavaScript tests execute the browser adapter against synthetic DOM pages. No personal inbox or live send is needed in CI. The coverage gate applies to this package's Python runtime; JavaScript behavior is separately tested. Browser UI changes can require selector updates. Live verification evidence and limits belong in the setup document.

## License

MIT
