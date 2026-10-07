# Webhook & API Integration Patterns

Templates for connecting iOS Shortcuts to external services, with emphasis on n8n integration.

## Pattern 1: Simple POST to Webhook

Send data from clipboard/share sheet to an n8n webhook.

```json
{
    "name": "Send to n8n",
    "icon": {"color": "orange", "glyph": "bolt"},
    "input_types": ["text", "url"],
    "share_sheet": true,
    "import_questions": [
        {"prompt": "n8n webhook URL:", "variable": "webhookUrl", "type": "URL"}
    ],
    "actions": [
        {"type": "url", "url": "WEBHOOK_URL_HERE"},
        {"type": "get_url", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_type": "JSON"},
        {"type": "notification", "body": "Sent!", "title": "n8n"}
    ]
}
```

**Key points:**
- `Get Contents of URL` (alias: `get_url`) is the HTTP client
- Always set `Content-Type` header explicitly
- API keys go in headers, never URL params

## Pattern 2: POST with Input Validation

Validate input exists before sending. Prevents silent failures.

```json
{
    "name": "Safe Webhook Send",
    "icon": {"color": "green", "glyph": "bolt"},
    "input_types": ["text"],
    "share_sheet": true,
    "actions": [
        {"type": "if", "condition": "Has any value"},
        {"type": "url", "url": "WEBHOOK_URL"},
        {"type": "get_url", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_type": "JSON"},
        {"type": "notification", "body": "Sent successfully", "title": "Webhook"},
        {"type": "otherwise"},
        {"type": "alert", "message": "No input provided. Copy something to clipboard or share from another app.", "title": "Missing Input", "show_cancel": false},
        {"type": "end_if"}
    ]
}
```

## Pattern 3: Two-Way Communication (n8n Respond to Webhook)

Send data and process the response. Requires n8n workflow with a "Respond to Webhook" node.

```json
{
    "name": "Query n8n",
    "icon": {"color": "blue", "glyph": "search"},
    "actions": [
        {"type": "ask_input", "prompt": "What do you want to look up?", "input_type": "Text"},
        {"type": "set_variable", "name": "query"},
        {"type": "url", "url": "WEBHOOK_URL"},
        {"type": "get_url", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_type": "JSON"},
        {"type": "get_dictionary_value", "key": "result"},
        {"type": "alert", "message": "Response received", "title": "n8n Response"}
    ]
}
```

**n8n side:** Use "Respond to Webhook" node (not just Webhook trigger) to send data back. Set response body as JSON with a `result` key.

## Pattern 4: Authenticated API Call

Use Import Questions to collect API key at install time.

```json
{
    "name": "Authenticated API",
    "icon": {"color": "navy", "glyph": "lock"},
    "import_questions": [
        {"prompt": "API Base URL:", "variable": "baseUrl", "type": "URL"},
        {"prompt": "API Key:", "variable": "apiKey", "type": "Text"}
    ],
    "actions": [
        {"type": "url", "url": "BASE_URL/endpoint"},
        {"type": "get_url", "method": "GET", "headers": {"Authorization": "Bearer API_KEY", "Content-Type": "application/json"}},
        {"type": "quick_look"}
    ]
}
```

**Security note:** Import Question values are stored in the shortcut's action parameters. They're not encrypted. Acceptable for personal use; for shareable shortcuts, document this in the shortcut description.

## Pattern 5: Share Sheet → Process → Respond

Capture from Share Sheet, process, show result. Common for capture-and-upload workflows.

```json
{
    "name": "Process Shared Content",
    "icon": {"color": "teal", "glyph": "share"},
    "input_types": ["text", "url", "web_page"],
    "share_sheet": true,
    "actions": [
        {"type": "if", "condition": "Has any value"},
        {"type": "set_variable", "name": "sharedContent"},
        {"type": "url", "url": "WEBHOOK_URL"},
        {"type": "get_url", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_type": "JSON"},
        {"type": "notification", "body": "Processing complete", "title": "Done"},
        {"type": "otherwise"},
        {"type": "get_clipboard"},
        {"type": "if", "condition": "Has any value"},
        {"type": "set_variable", "name": "sharedContent"},
        {"type": "url", "url": "WEBHOOK_URL"},
        {"type": "get_url", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_type": "JSON"},
        {"type": "notification", "body": "Sent from clipboard", "title": "Done"},
        {"type": "otherwise"},
        {"type": "alert", "message": "Nothing to send. Share from another app or copy to clipboard first.", "title": "No Input"},
        {"type": "end_if"},
        {"type": "end_if"}
    ]
}
```

**Pattern:** Check share sheet input → fall back to clipboard → fail gracefully with alert.

**Note on nesting:** In the JSON definition, If/Otherwise/End_If blocks are listed as a flat action sequence, not nested objects. The generator auto-assigns `GroupingIdentifier` UUIDs to link matched blocks, so nested If blocks work correctly. The flat structure mirrors how Shortcuts stores actions internally.

## n8n Integration Checklist

When building a Shortcut that calls an n8n webhook:

1. **n8n workflow must be active** — inactive workflows don't respond to webhooks
2. **Use production webhook URL** — test URLs only work during manual execution in the editor
3. **Respond immediately for heavy processing** — add an n8n "Respond to Webhook" node early, then process async. Otherwise the Shortcut times out (~30s default)
4. **Rate limiting** — if the Shortcut uses Repeat loops hitting the webhook, add Wait actions between calls. n8n doesn't throttle by default
5. **Document the webhook caller** — add `CALLERS: iOS Shortcut "[name]"` to the n8n workflow's sticky note
6. **URL stability** — editing the n8n Webhook node can change the URL. If that happens, update the Shortcut too. This is a maintenance coupling — document both sides

## Timeout Behavior

- iOS Shortcuts HTTP timeout: ~30 seconds (not configurable)
- If the server doesn't respond in time, the Shortcut silently fails or shows a generic error
- For long operations: have n8n respond 200 immediately, process in background, notify via push notification when done