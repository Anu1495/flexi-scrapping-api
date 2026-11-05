import json
import logging

from fastapi import APIRouter, HTTPException
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.services.sheets import GoogleSheetsService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sheets/data", tags=["sheets"])
def read_sheet_data() -> list[dict[str, str]]:
    """Return configured Google Sheets rows as objects keyed by column headers."""
    settings = get_settings()
    try:
        return GoogleSheetsService(settings).read_records()
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