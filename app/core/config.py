import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    service_account_file: str
    service_account_json: str


def get_settings() -> Settings:
    return Settings(
        service_account_file=os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            str(Path(__file__).resolve().parents[2] / "google_service_account.json"),
        ),
        service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip(),
    )