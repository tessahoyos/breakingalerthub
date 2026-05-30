from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from .config import Settings
from .sheets import GoogleSheetsClient, SheetsAppender
from .slack import SlackSignatureVerifier, alert_row_from_payload, should_record_event


def create_app(
    settings: Settings | None = None,
    sheets_client: SheetsAppender | None = None,
    verifier: SlackSignatureVerifier | None = None,
) -> Flask:
    settings = settings or Settings.from_env()
    sheets_client = sheets_client or GoogleSheetsClient.from_settings(settings)
    verifier = verifier or SlackSignatureVerifier(settings.slack_signing_secret)

    app = Flask(__name__)

    @app.get("/health")
    def health() -> tuple[dict[str, bool], int]:
        return {"ok": True}, 200

    @app.post("/slack/events")
    def slack_events() -> tuple[Any, int]:
        body = request.get_data()
        if not verifier.is_valid(
            request.headers.get("X-Slack-Request-Timestamp"),
            request.headers.get("X-Slack-Signature"),
            body,
        ):
            return jsonify({"ok": False, "error": "invalid_slack_signature"}), 401

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "invalid_json"}), 400

        if payload.get("type") == "url_verification":
            return jsonify({"challenge": payload.get("challenge", "")}), 200

        if payload.get("type") != "event_callback":
            return jsonify({"ok": True, "recorded": False}), 200

        event = payload.get("event")
        if not isinstance(event, dict):
            return jsonify({"ok": True, "recorded": False}), 200

        if not should_record_event(
            event,
            channel_id=settings.slack_channel_id,
            include_bot_messages=settings.include_bot_messages,
        ):
            return jsonify({"ok": True, "recorded": False}), 200

        try:
            sheets_client.append_row(alert_row_from_payload(payload))
        except Exception:
            app.logger.exception("Failed to append Slack alert to Google Sheets")
            return jsonify({"ok": False, "error": "sheet_append_failed"}), 502

        return jsonify({"ok": True, "recorded": True}), 200

    return app
