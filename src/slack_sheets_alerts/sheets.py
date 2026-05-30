from __future__ import annotations

import json
from typing import Any, Protocol

from .config import Settings


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class SheetsAppender(Protocol):
    def append_row(self, row: list[str]) -> None:
        """Append one row to the configured sheet."""


class GoogleSheetsClient:
    def __init__(self, service: Any, *, spreadsheet_id: str, value_range: str) -> None:
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._value_range = value_range

    @classmethod
    def from_settings(cls, settings: Settings) -> "GoogleSheetsClient":
        credentials = _credentials_from_settings(settings)
        service = _build_sheets_service(credentials)

        return cls(
            service,
            spreadsheet_id=settings.google_sheet_id,
            value_range=settings.google_sheet_range,
        )

    def append_row(self, row: list[str]) -> None:
        (
            self._service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self._spreadsheet_id,
                range=self._value_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )


def _credentials_from_settings(settings: Settings) -> Any:
    from google.oauth2 import service_account

    if settings.google_service_account_json:
        service_account_info = json.loads(settings.google_service_account_json)
        return service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[SHEETS_SCOPE],
        )

    return service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=[SHEETS_SCOPE],
    )


def _build_sheets_service(credentials: Any) -> Any:
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=credentials, cache_discovery=False)
