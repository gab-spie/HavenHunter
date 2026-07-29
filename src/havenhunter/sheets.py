"""Google Sheets logging.

Validated listings and the actions taken on them are appended to a Google
Sheet that doubles as a lightweight tracker anyone on the team can read. Each
profile writes to its own worksheet tab, so parallel searches (for example a
shared flat and a solo studio) never mix their trails and each keeps a clean,
self-contained history. Authentication uses a Google service account whose
credentials path comes from the environment. No credentials are ever stored in
the repository.

The log degrades gracefully: if credentials are absent, logging becomes a
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

HEADERS = ["timestamp", "source", "title", "price", "area", "url", "status"]
DEFAULT_WORKSHEET = "Log"
_URL_COLUMN = 6     # 1-indexed position of "url" in HEADERS
_STATUS_COLUMN = 7  # 1-indexed position of "status" in HEADERS


def worksheet_title_for(profile: Optional[str]) -> str:
    """Tab title for a profile. One tab per profile keeps trails separate; an
    unset profile falls back to the default tab."""
    return profile or DEFAULT_WORKSHEET


def row_for(listing: Listing, status: str) -> list:
    """Single source of truth for a log row, aligned with HEADERS."""
    return [
        datetime.now().isoformat(timespec="seconds"),
        listing.source,
        listing.title,
        listing.price,
        listing.area_label,
        listing.url,
        status,
    ]


class SheetLog:
    def __init__(self, credentials_path: str, spreadsheet: str):
        self._enabled = bool(credentials_path)
        self._credentials_path = credentials_path
        self._spreadsheet_name = spreadsheet
        self._book = None                         # opened spreadsheet, lazily
        self._worksheets: dict[str, object] = {}  # title -> worksheet cache

    # -- connection ---------------------------------------------------------

    def _open(self):
        """Open the spreadsheet once and cache it."""
        if self._book is None:
            import gspread
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=_SCOPES)
            client = gspread.authorize(creds)
            self._book = client.open(self._spreadsheet_name)
        return self._book

    def _reset(self) -> None:
        """Drop cached handles so the next call reopens cleanly. Used when a tab
        is renamed or removed in the Sheets UI while the bot keeps running."""
        self._book = None
        self._worksheets.clear()

    def _worksheet(self, title: str):
        """Return the profile tab, creating it (with headers) if it is missing."""
        if title in self._worksheets:
            return self._worksheets[title]
        import gspread

        book = self._open()
        try:
            ws = book.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = book.add_worksheet(title=title, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
        self._worksheets[title] = ws
        return ws

    # -- public API ---------------------------------------------------------

    def append(self, listing: Listing, status: str,
               profile: Optional[str] = None) -> bool:
        """Append one row to the profile's tab. Returns False when logging is
        disabled or the write fails after a single reconnect retry."""
        if not self._enabled:
            return False
        from gspread.exceptions import APIError

        title = worksheet_title_for(profile)
        row = row_for(listing, status)
        for attempt in range(2):
            try:
                self._worksheet(title).append_row(row)
                return True
            except APIError:
                if attempt == 0:
                    self._reset()
                    continue
                return False
            except Exception:
                return False
        return False

    def mark(self, url: str, status: str) -> bool:
        """Set the status of the row for `url`, searching every tab so a listing
        is found wherever its profile logged it."""
        if not self._enabled:
            return False
        from gspread.exceptions import APIError

        for attempt in range(2):
            try:
                for ws in self._open().worksheets():
                    cell = ws.find(url, in_column=_URL_COLUMN)
                    if cell is not None:
                        ws.update_cell(cell.row, _STATUS_COLUMN, status)
                        return True
                return False
            except APIError:
                if attempt == 0:
                    self._reset()
                    continue
                return False
            except Exception:
                return False
        return False


def build(credentials_path: str, spreadsheet: Optional[str]) -> Optional["SheetLog"]:
    if not credentials_path or not spreadsheet:
        return None
    return SheetLog(credentials_path, spreadsheet)
