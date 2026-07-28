"""Deduplication layer.

A listing must never be presented twice, and a listing must never be lost.
The dedup store is the memory that makes the whole system idempotent: rerunning
a search only ever surfaces listings that were not seen before.

`DedupStore` is an interface. `InMemoryStore` is a simple implementation used in
tests and demos. In production the same interface is backed by a hosted
database table keyed on the listing URL, so state survives restarts and is
shared across scheduled runs.
"""
from __future__ import annotations

import abc

from .models import Listing


class DedupStore(abc.ABC):
    @abc.abstractmethod
    def seen(self, listing: Listing) -> bool:
        ...

    @abc.abstractmethod
    def remember(self, listing: Listing) -> None:
        ...

    def filter_new(self, listings: list[Listing]) -> list[Listing]:
        """Return only listings never seen before, and record them.

        Recording happens as we go, so duplicates within the same batch are
        collapsed too.
        """
        fresh: list[Listing] = []
        for listing in listings:
            if self.seen(listing):
                continue
            self.remember(listing)
            fresh.append(listing)
        return fresh


class InMemoryStore(DedupStore):
    """Non-persistent store. Fine for a single process run or tests."""

    def __init__(self) -> None:
        self._keys: set[str] = set()

    def seen(self, listing: Listing) -> bool:
        return listing.key() in self._keys

    def remember(self, listing: Listing) -> None:
        self._keys.add(listing.key())
