"""Example source connector.

This is a self-contained, offline connector that returns a handful of sample
listings. It exists so the pipeline can run end to end in this public
repository without any private code or network access.

A real connector implements the exact same `fetch` signature: it retrieves
listings from one public origin, normalizes each into a `Listing`, and returns
them. Retrieval details (pagination, rendering, back-off) are the connector's
own business and never leak into the rest of the system.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from ..models import Listing
from .base import Source, register

_SAMPLE = [
    ("Bright two-bedroom near the canal", 1680, "City center", 2, 46.0, True),
    ("Renovated studio, top floor", 820, "Riverside", 0, 24.5, True),
    ("Quiet two-bedroom with balcony", 1720, "Old town", 2, 51.0, True),
    ("Compact furnished studio", 910, "University district", 0, 21.0, True),
]


@register("example")
class ExampleSource(Source):
    """Deterministic offline source used for demos and tests."""

    name = "example"

    async def fetch(self, max_price: int, max_pages: int = 2) -> list[Listing]:
        # A real connector would await network I/O here. We simulate a small
        # latency so the async pipeline behaves realistically.
        await asyncio.sleep(0)
        now = datetime.now()
        listings: list[Listing] = []
        for i, (title, price, area, rooms, surface, furnished) in enumerate(_SAMPLE):
            listings.append(
                Listing(
                    source=self.name,
                    url=f"https://example.invalid/listing/{1000 + i}",
                    title=title,
                    price=price,
                    area_label=area,
                    rooms=rooms,
                    surface=surface,
                    furnished=furnished,
                    published_at=now - timedelta(hours=i * 3),
                    published_at_reliable=True,
                    tags=f"{rooms} bd · {int(surface)} m2",
                    description=title,
                )
            )
        return listings
