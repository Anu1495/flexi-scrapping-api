import json
import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.services.sheets import GoogleSheetsService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sheets/data", tags=["sheets"])
def read_sheet_data(
    checkin_date: date | None = Query(
        default=None,
        description="Optional check-in date filter in YYYY-MM-DD format, matched against the Date column.",
    ),
) -> list[dict[str, str]]:
    """Return configured Google Sheets rows as objects keyed by column headers."""
    settings = get_settings()
    try:
        records = GoogleSheetsService(settings).read_records()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HttpError as exc:
        try:
            google_error = json.loads(exc.content).get("error", {})
            message = google_error.get("message", "No error message returned")
            reasons = ", ".join(
                item.get("reason", "")
                for item in google_error.get("errors", [])
                if item.get("reason")
            )
            logger.error(
                "Google Sheets API HTTP %s (reason: %s): %s",
                exc.status_code,
                reasons or "not provided",
                message,
            )
        except (json.JSONDecodeError, AttributeError, TypeError):
            logger.exception("Google Sheets API returned HTTP %s", exc.status_code)
        raise HTTPException(
            status_code=502,
            detail="Google Sheets could not complete the request. Check the spreadsheet ID, range, sharing, and API settings.",
        ) from exc

    if checkin_date is None:
        return records

    date_column = next(
        (column for row in records for column in row if column.strip().casefold() == "date"),
        None,
    )
    if date_column is None:
        raise HTTPException(status_code=502, detail="The configured worksheet does not contain a Date column.")

    requested_date = checkin_date.isoformat()
    matching_records: list[dict[str, str]] = []
    current_sheet_date = ""
    for row in records:
        row_date = row.get(date_column, "").strip()
        if row_date:
            current_sheet_date = row_date[:10]
        if current_sheet_date == requested_date:
            matching_records.append(row)

    return matching_records