# Google Voice browser connection

## Connection choice

This package uses the signed-in Google Voice website. There is no supported public Google Cloud Google Voice messaging API to enable as there is for Sheets. Creating another OAuth client or adding a Sheets scope would not provide SMS access. Cloud Speech-to-Text and Text-to-Speech do not expose the Voice inbox. The app does not use reverse-engineered internal HTTP endpoints.

The previous implementation returned hard-coded demonstration messages and only appended outgoing messages to memory. It was not a Google Voice connection. Version 0.2 replaces that behavior and fixes the recursive MCP startup override by using the SDK's stdio server directly.

## Existing Chrome session

Chrome must be running with local debugging enabled on port 9222. If you already have this session open, reuse it. Do not launch a second copy merely to run this tool.

For initial setup on macOS, when no appropriate session exists:

```sh
open -na 'Google Chrome' --args \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-debug"
```

Sign into the intended account in that profile and open `https://voice.google.com/`. Chrome requires a non-default user-data directory for remote debugging in recent versions. Account URL indices such as `/u/1` are not identities and can change.

Run `gvoice doctor` to inspect the detected account. Set `GOOGLE_VOICE_ACCOUNT` to the expected email before reading or sending. Multiple matching tabs must be explicitly selected; do not guess the account based on the first tab. Use global `--account`, `--port`, and `--tab-id` options before the command, or set `GOOGLE_VOICE_ACCOUNT`, `GOOGLE_VOICE_PORT`, and `GOOGLE_VOICE_TAB_ID`. For example: `gvoice --account your-account@example.com --tab-id TAB_ID sms --limit 5`. Use `gvoice --help` for details. No account address, recipient, token, or conversation contents belong in tracked configuration or test fixtures.

## Operational workflow

1. Check connection and account with `doctor`.
2. Open the desired Voice view/conversation. Read only a bounded relevant portion.
3. Draft the response for user review.
4. Preview the exact recipient and message locally.
5. Only after authorization, run the same operation with confirmation.
6. Inspect the outcome and read-back. Never infer delivery from a DOM click, and never retry an ambiguous submission automatically.

The tool deliberately does not navigate through the inbox, mark batches read, initiate calls, delete/archive messages, or change Voice settings. Opening a thread through the browser UI may mark it read; this adapter reads the view already open.

## Troubleshooting

- No Chrome listener: start the intended debugging-enabled session, then rerun doctor.
- No Voice tab: open Voice in that browser profile.
- Multiple Voice tabs: select a specific tab with the advertised connection option.
- Account mismatch or missing identity: verify the account in the website; do not weaken the check.
- Wrong view or selectors unavailable: open the relevant view and allow it to finish loading. Report UI incompatibility rather than returning invented or apparently empty data.
- Existing draft: resolve it yourself before an automated confirmed send; the tool will not replace it.
- Recipient mismatch/group thread: open the intended one-to-one conversation first.
- Uncertain submission: inspect the actual conversation before considering another send.

## Verification

Synthetic automated checks and a bounded live read-only smoke check are recorded with the implementation. No live SMS is sent as a connectivity test. A successful read-only check does not establish that outbound delivery works.

Read-only live verification on October 13, 2026 succeeded for connection/account identity, one SMS summary, one message in the already-selected thread, one call summary, and one voicemail summary. The original conversation/draft was left untouched; temporary call/voicemail inspection tabs were closed. Only result counts/field names were retained, not message content. Sending was exercised only against synthetic DOM pages, never a live recipient.

An empty/loading view without a verified empty-state selector is reported as an unsupported layout rather than reported as an empty inbox. Voicemail reads expose the displayed transcript preview and duration label, not a guarantee of full transcription or audio retrieval.

Automated verification for this release: 90 Python tests passed with 230/230 statements and 60/60 branches covered, plus 17 executable synthetic DOM tests. The real MCP stdio test initializes the protocol, lists tools, and invokes preview with socket connections forbidden. Invalid confirmation types are rejected. The built wheel includes the browser JavaScript resource. Independent review covered account/recipient checks, draft preservation, the one-click send path, uncertain outcomes, and changed-layout handling.
