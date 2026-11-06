import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, Query
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.core.hotels import HOTELS
from app.services.sheets import GoogleSheetsService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sheets/data", tags=["sheets"])
def read_sheet_data(
    scrape_id: int = Query(
        ..., description="Hotel scrape ID: 3, 4, 6, or 7."
    ),
    checkin_date: date | None = Query(
        default=None,
        description="Optional check-in date filter in YYYY-MM-DD format, matched against the Date column.",
    ),
) -> list[dict[str, object]]:
    """Return normalized rate records from the selected hotel's Google Sheet."""
    hotel = HOTELS.get(scrape_id)
    if hotel is None:
        supported_ids = ", ".join(str(value) for value in sorted(HOTELS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scrape_id {scrape_id}. Supported values are: {supported_ids}.",
        )

    settings = get_settings()
    try:
        records = GoogleSheetsService(settings, hotel).read_records()
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

    if not records:
        return []

    date_column = next(
        (column for row in records for column in row if column.strip().casefold() == "date"),
        None,
    )
    if date_column is None:
        raise HTTPException(status_code=502, detail="The configured worksheet does not contain a Date column.")

    required_columns = ("Room Type", "Rate", "Rate Type", "Availability")
    header_lookup = {column.strip().casefold(): column for row in records for column in row}
    missing_columns = [
        column for column in required_columns if column.casefold() not in header_lookup
    ]
    if missing_columns:
        raise HTTPException(
            status_code=502,
            detail=f"The configured worksheet is missing required columns: {', '.join(missing_columns)}.",
        )

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    transformed_records: list[dict[str, object]] = []
    current_sheet_date = ""
    for row in records:
        row_date = row.get(date_column, "").strip()
        if row_date:
            current_sheet_date = row_date[:10]
        if checkin_date is not None and current_sheet_date != checkin_date.isoformat():
            continue

        rate_type = row[header_lookup["rate type"]].strip()
        rate_type_normalized = " ".join(rate_type.casefold().split())
        transformed_records.append(
            {
                "checkIn": current_sheet_date,
                "timeStamp": timestamp,
                "source": None,
                "ratePlanCode": None,
                "roomType": row[header_lookup["room type"]],
                "price": _parse_number(row[header_lookup["rate"]], "Rate"),
                "adults": 2,
                "children": 0,
                "infants": 0,
                "refundable": rate_type_normalized
                in {"refundable", "refundable with breakfast"},
                "breakfast": rate_type_normalized
                in {"non-refundable with breakfast", "refundable with breakfast"},
                "lunch": False,
                "dinner": False,
                "nights": 1,
                "availability": _parse_number(row[header_lookup["availability"]], "Availability"),
            }
        )

    return transformed_records


def _parse_number(value: str, column_name: str) -> int | float | None:
    cleaned_value = value.strip().replace(",", "")
    if not cleaned_value:
        return None
    try:
        number = Decimal(cleaned_value)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The {column_name} value {value!r} is not numeric.",
        ) from exc
    if not number.is_finite():
        raise HTTPException(status_code=502, detail=f"The {column_name} value must be finite.")
    return int(number) if number == number.to_integral_value() else float(number)