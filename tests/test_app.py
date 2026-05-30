from __future__ import annotations

import hashlib
import hmac
import json

from slack_sheets_alerts.app import create_app
from slack_sheets_alerts.config import Settings
from slack_sheets_alerts.slack import SlackSignatureVerifier


SIGNING_SECRET = "test-secret"
TIMESTAMP = "1717070400"


class FakeSheetsClient:
    def __init__(self) -> None:
        self.rows: list[list[str]] = []

    def append_row(self, row: list[str]) -> None:
        self.rows.append(row)


def make_client(
    *,
    channel_id: str = "C123",
    include_bot_messages: bool = True,
) -> tuple[object, FakeSheetsClient]:
    settings = Settings(
        slack_signing_secret=SIGNING_SECRET,
        slack_channel_id=channel_id,
        google_sheet_id="sheet-id",
        google_service_account_json="{}",
        include_bot_messages=include_bot_messages,
    )
    sheets = FakeSheetsClient()
    verifier = SlackSignatureVerifier(SIGNING_SECRET, now=lambda: int(TIMESTAMP))
    app = create_app(settings=settings, sheets_client=sheets, verifier=verifier)

    return app.test_client(), sheets


def signed_headers(body: bytes) -> dict[str, str]:
    base = b"v0:" + TIMESTAMP.encode("utf-8") + b":" + body
    signature = "v0=" + hmac.new(
        SIGNING_SECRET.encode("utf-8"),
        base,
        hashlib.sha256,
    ).hexdigest()

    return {
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": TIMESTAMP,
        "X-Slack-Signature": signature,
    }


def post_slack_event(client: object, payload: dict[str, object]):
    body = json.dumps(payload).encode("utf-8")
    return client.post("/slack/events", data=body, headers=signed_headers(body))


def test_url_verification_returns_challenge() -> None:
    client, sheets = make_client()
    response = post_slack_event(
        client,
        {"type": "url_verification", "challenge": "challenge-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"challenge": "challenge-token"}
    assert sheets.rows == []


def test_matching_channel_message_appends_alert_row() -> None:
    client, sheets = make_client()
    response = post_slack_event(
        client,
        {
            "type": "event_callback",
            "event_id": "Ev123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "build failed on main",
                "ts": "1717070400.000200",
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "recorded": True}
    assert len(sheets.rows) == 1
    row = sheets.rows[0]
    assert row[2] == "Ev123"
    assert row[3] == "C123"
    assert row[4] == "U123"
    assert row[5] == "build failed on main"


def test_other_channel_message_is_ignored() -> None:
    client, sheets = make_client(channel_id="C999")
    response = post_slack_event(
        client,
        {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "not the alert channel",
                "ts": "1717070400.000200",
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "recorded": False}
    assert sheets.rows == []


def test_bot_messages_are_recorded_by_default() -> None:
    client, sheets = make_client()
    response = post_slack_event(
        client,
        {
            "type": "event_callback",
            "event_id": "EvBot",
            "event": {
                "type": "message",
                "subtype": "bot_message",
                "channel": "C123",
                "bot_id": "B123",
                "text": "alert from monitoring bot",
                "ts": "1717070400.000200",
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "recorded": True}
    assert sheets.rows[0][4] == "B123"
    assert sheets.rows[0][5] == "alert from monitoring bot"


def test_invalid_signature_is_rejected() -> None:
    client, sheets = make_client()
    body = json.dumps({"type": "event_callback"}).encode("utf-8")
    response = client.post(
        "/slack/events",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": TIMESTAMP,
            "X-Slack-Signature": "v0=bad",
        },
    )

    assert response.status_code == 401
    assert response.get_json() == {"ok": False, "error": "invalid_slack_signature"}
    assert sheets.rows == []
