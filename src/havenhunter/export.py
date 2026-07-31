"""CSV export.

A run's matches can be written to a flat CSV, handy for a quick spreadsheet
review or for feeding another tool. The Google Sheets logger stays the live
tracker; this is the offline, dependency-free companion.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Listing

_HEADER = ["source", "title", "price", "area", "rooms", "surface", "url", "published_at"]

# Leading characters a spreadsheet reads as "this cell is a formula".
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value):
    """Defuse formula injection from scraped, untrusted listing text.

    A title or area label comes straight from a source connector, not from
    us. Excel (and most spreadsheet apps) treats a CSV cell starting with =,
    +, -, @ or a leading tab/CR as a formula to execute on open, so a crafted
    listing could run arbitrary formulas in whoever's spreadsheet imports this
    file. Prefixing a single quote forces text interpretation.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_TRIGGER_CHARS):
        return "'" + value
    return value


def to_csv(listings: list[Listing], path: str | Path) -> Path:
    """Write listings to a CSV file and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(_HEADER)
        for l in listings:
            writer.writerow(
                [
                    _sanitize_cell(l.source),
                    _sanitize_cell(l.title),
                    l.price,
                    _sanitize_cell(l.area_label),
                    l.rooms if l.rooms is not None else "",
                    l.surface if l.surface is not None else "",
                    _sanitize_cell(l.url),
                    l.published_at.isoformat() if l.published_at else "",
                ]
            )
    return path
