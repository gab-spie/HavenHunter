"""Google Sheets logging.

Validated listings and the actions taken on them are appended to a shared
Google Sheet, which doubles as a lightweight tracker anyone on the team can
read. Authentication uses a Google service account whose credentials path comes
from the environment. No credentials are ever stored in the repository.

The store degrades gracefully: if credentials are absent, logging becomes a
no-op instead of crashing the pipeline, so the rest of the system keeps working
in environments where the sheet is not configured.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import Listing

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetLog:
    def __init__(self, credentials_path: str, spreadsheet: str, worksheet: str = "Log"):
        self._enabled = bool(credentials_path)
        self._sheet = None
        if not self._enabled:
            return
        # Imported lazily so the dependency is only needed when logging is used.
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_file(credentials_path, scopes=_SCOPES)
        client = gspread.authorize(creds)
        self._sheet = client.open(spreadsheet).worksheet(worksheet)

    def append(self, listing: Listing, status: str) -> bool:
        """Append one row. Returns False when logging is disabled or fails."""
        if not self._enabled or self._sheet is None:
            return False
        try:
            self._sheet.append_row(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    listing.source,
                    listing.title,
                    listing.price,
                    listing.area_label,
                    listing.url,
                    status,
                ]
            )
            return True
        except Exception:
            return False

    def mark(self, url: str, status: str) -> bool:
        """Update the status of an existing row found by its URL."""
        if not self._enabled or self._sheet is None:
            return False
        try:
            cell = self._sheet.find(url)
            if cell is None:
                return False
            self._sheet.update_cell(cell.row, 7, status)
            return True
        except Exception:
            return False


def build(credentials_path: str, spreadsheet: Optional[str]) -> Optional["SheetLog"]:
    if not credentials_path or not spreadsheet:
        return None
    return SheetLog(credentials_path, spreadsheet)
