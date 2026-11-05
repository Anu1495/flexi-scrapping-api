import json
import re
from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class GoogleSheetsService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def read_records(self) -> list[dict[str, str]]:
        if not self.settings.spreadsheet_id:
            raise ValueError("Set GOOGLE_SHEETS_SPREADSHEET_ID to the spreadsheet ID.")
        if not self.settings.sheet_range:
            raise ValueError("Set GOOGLE_SHEETS_RANGE to the worksheet and cells to read.")

        credentials = self._get_credentials()
        sheets_api = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        sheet_range = self._resolve_range(sheets_api)
        response = (
            sheets_api.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.settings.spreadsheet_id,
                range=sheet_range,
            )
            .execute()
        )
        values: list[list[Any]] = response.get("values", [])
        if len(values) < 2:
            return []

        headers = self._normalize_headers(values[0])
        records: list[dict[str, str]] = []
        for row in values[1:]:
            padded_row = row + [""] * max(0, len(headers) - len(row))
            records.append(
                {
                    header: str(padded_row[index]) if index < len(padded_row) else ""
                    for index, header in enumerate(headers)
                }
            )
        return records

    def _resolve_range(self, sheets_api: Any) -> str:
        gid_range = re.fullmatch(r"gid=(\d+)!([^!]+)", self.settings.sheet_range)
        if not gid_range:
            return self.settings.sheet_range

        sheet_id = int(gid_range.group(1))
        cell_range = gid_range.group(2)
        metadata = (
            sheets_api.spreadsheets()
            .get(
                spreadsheetId=self.settings.spreadsheet_id,
                fields="sheets(properties(sheetId,title))",
            )
            .execute()
        )
        for sheet in metadata.get("sheets", []):
            properties = sheet.get("properties", {})
            if properties.get("sheetId") == sheet_id:
                title = str(properties["title"]).replace("'", "''")
                return f"'{title}'!{cell_range}"

        raise ValueError(f"No worksheet with gid {sheet_id} exists in the configured spreadsheet.")

    def _get_credentials(self) -> Credentials:
        if self.settings.service_account_json:
            try:
                service_account_info = json.loads(self.settings.service_account_json)
                return Credentials.from_service_account_info(
                    service_account_info,
                    scopes=[SHEETS_READONLY_SCOPE],
                )
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON must contain valid service-account JSON.") from exc

        credentials_path = Path(self.settings.service_account_file)
        if not credentials_path.is_file():
            raise ValueError(
                "Service-account credentials were not found. Set GOOGLE_SERVICE_ACCOUNT_FILE "
                "or configure GOOGLE_SERVICE_ACCOUNT_JSON."
            )
        return Credentials.from_service_account_file(
            str(credentials_path),
            scopes=[SHEETS_READONLY_SCOPE],
        )

    @staticmethod
    def _normalize_headers(raw_headers: list[Any]) -> list[str]:
        headers: list[str] = []
        counts: dict[str, int] = {}
        for index, raw_header in enumerate(raw_headers):
            base = str(raw_header).strip() or f"column_{index + 1}"
            counts[base] = counts.get(base, 0) + 1
            headers.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
        return headers