from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any, Callable


class SlackSignatureVerifier:
    """Verify Slack request signatures before trusting webhook bodies."""

    def __init__(
        self,
        signing_secret: str,
        *,
        tolerance_seconds: int = 60 * 5,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.signing_secret = signing_secret
        self.tolerance_seconds = tolerance_seconds
        self._now = now or time.time

    def is_valid(self, timestamp: str | None, signature: str | None, body: bytes) -> bool:
        if not timestamp or not signature:
            return False

        try:
            request_time = int(timestamp)
        except ValueError:
            return False

        if abs(self._now() - request_time) > self.tolerance_seconds:
            return False

        signed_body = b"v0:" + timestamp.encode("utf-8") + b":" + body
        digest = hmac.new(
            self.signing_secret.encode("utf-8"),
            signed_body,
            hashlib.sha256,
        ).hexdigest()
        expected_signature = f"v0={digest}"

        return hmac.compare_digest(expected_signature, signature)


def should_record_event(
    event: dict[str, Any],
    *,
    channel_id: str,
    include_bot_messages: bool,
) -> bool:
    if event.get("type") != "message":
        return False
    if event.get("channel") != channel_id:
        return False

    subtype = event.get("subtype")
    if subtype is None:
        return True

    return subtype == "bot_message" and include_bot_messages


def alert_row_from_payload(payload: dict[str, Any]) -> list[str]:
    event = payload["event"]
    event_time = _format_slack_timestamp(event.get("ts") or event.get("event_ts"))
    received_at = datetime.now(UTC).isoformat()
    sender = event.get("user") or event.get("bot_id") or event.get("username") or ""

    return [
        received_at,
        event_time,
        payload.get("event_id", ""),
        event.get("channel", ""),
        sender,
        event.get("text", ""),
        event.get("thread_ts", ""),
        json.dumps(event, sort_keys=True, separators=(",", ":")),
    ]


def _format_slack_timestamp(timestamp: str | None) -> str:
    if not timestamp:
        return ""

    try:
        return datetime.fromtimestamp(float(timestamp), UTC).isoformat()
    except ValueError:
        return ""
