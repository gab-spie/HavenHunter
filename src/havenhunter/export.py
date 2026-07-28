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
                    l.source,
                    l.title,
                    l.price,
                    l.area_label,
                    l.rooms if l.rooms is not None else "",
                    l.surface if l.surface is not None else "",
                    l.url,
                    l.published_at.isoformat() if l.published_at else "",
                ]
            )
    return path
