from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    slack_signing_secret: str
    slack_channel_id: str
    google_sheet_id: str
    google_sheet_range: str = "Alerts!A:H"
    google_service_account_file: str | None = None
    google_service_account_json: str | None = None
    include_bot_messages: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
            slack_channel_id=os.environ.get("SLACK_CHANNEL_ID", ""),
            google_sheet_id=os.environ.get("GOOGLE_SHEET_ID", ""),
            google_sheet_range=os.environ.get("GOOGLE_SHEET_RANGE", "Alerts!A:H"),
            google_service_account_file=os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE"),
            google_service_account_json=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"),
            include_bot_messages=_env_bool("SLACK_INCLUDE_BOT_MESSAGES", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        missing = []
        if not self.slack_signing_secret:
            missing.append("SLACK_SIGNING_SECRET")
        if not self.slack_channel_id:
            missing.append("SLACK_CHANNEL_ID")
        if not self.google_sheet_id:
            missing.append("GOOGLE_SHEET_ID")
        if not self.google_service_account_file and not self.google_service_account_json:
            missing.append("GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON")

        if missing:
            formatted = ", ".join(missing)
            raise RuntimeError(f"Missing required configuration: {formatted}")
