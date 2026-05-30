# Breaking Alert Hub

Breaking Alert Hub is a small webhook service that listens for Slack channel
message events and appends each alert to a Google Sheet.

## What it records

Create a sheet tab named `Alerts` with these columns:

| Column | Value |
| --- | --- |
| A | Time the webhook received the event |
| B | Slack message timestamp |
| C | Slack event ID |
| D | Slack channel ID |
| E | Slack user ID, bot ID, or username |
| F | Message text |
| G | Slack thread timestamp |
| H | Raw Slack event JSON |

## Configuration

Copy `.env.example` and set these environment variables:

```sh
SLACK_SIGNING_SECRET=replace-with-slack-signing-secret
SLACK_CHANNEL_ID=C0123456789
SLACK_INCLUDE_BOT_MESSAGES=true

GOOGLE_SHEET_ID=replace-with-google-sheet-id
GOOGLE_SHEET_RANGE=Alerts!A:H

# Use either a credentials file path or an inline service-account JSON string.
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/google-service-account.json
# GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account", "...":"..."}
```

## Slack setup

1. Create a Slack app for the workspace.
2. Under **Basic Information**, copy the signing secret into
   `SLACK_SIGNING_SECRET`.
3. Under **Event Subscriptions**, enable events and point the request URL to:

   ```text
   https://your-domain.example/slack/events
   ```

4. Subscribe to the `message.channels` bot event.
5. Install the app to the workspace and invite it to the alert channel.
6. Copy the Slack channel ID into `SLACK_CHANNEL_ID`.

The service verifies Slack's request signature before processing the body.

## Google Sheets setup

1. Create a Google Cloud service account.
2. Enable the Google Sheets API for the project.
3. Download the service-account JSON key.
4. Share the destination spreadsheet with the service account's
   `client_email` address using editor access.
5. Set `GOOGLE_SHEET_ID` to the spreadsheet ID from its URL.

## Run locally

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
flask --app wsgi run --port 8000
```

Expose the local server to Slack with a tunnel such as ngrok:

```sh
ngrok http 8000
```

Then configure Slack's event request URL to the tunnel URL plus
`/slack/events`.

## Run in production

```sh
gunicorn 'wsgi:app' --bind 0.0.0.0:${PORT:-8000}
```

## Tests

```sh
pip install -r requirements-dev.txt
python3 -m pytest
```
