"""Core data model.

Everything that flows through the pipeline is a `Listing`. Sources produce
them, filters accept or reject them, the dedup store remembers them, and the
notifier presents them. Keeping a single normalized shape is what lets the
rest of the system stay agnostic to where a listing came from.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Listing:
    """A normalized housing listing, independent of its origin source."""

    source: str                      # logical source name, e.g. "source-a"
    url: str                         # canonical URL, also the dedup key
    title: str
    price: int                       # monthly rent, currency-agnostic integer
    area_label: str                  # human label, e.g. "Paris 11e"
    rooms: Optional[int] = None      # bedrooms when known
    area_code: Optional[int] = None  # numeric area for exclusion rules, when known
    surface: Optional[float] = None  # square meters when known
    furnished: Optional[bool] = None
    published_at: Optional[datetime] = None
    published_at_reliable: bool = False
    tags: str = ""
    description: str = ""

    def key(self) -> str:
        """Stable identity used by the dedup store."""
        return self.url.strip().rstrip("/").lower()


@dataclass
class Criteria:
    """User-defined acceptance rules for one profile."""

    max_price_per_source: dict[str, int] = field(default_factory=dict)
    default_max_price: int = 0
    min_rooms: int = 0
    furnished_required: bool = False
    excluded_areas: list[int] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)

    def budget_for(self, source: str) -> int:
        return self.max_price_per_source.get(source, self.default_max_price)

    def accepts(self, listing: Listing) -> bool:
        """Pure predicate: does this listing satisfy every rule?"""
        if listing.price > self.budget_for(listing.source):
            return False
        if self.furnished_required and listing.furnished is False:
            return False
        if self.min_rooms and (listing.rooms is None or listing.rooms < self.min_rooms):
            return False
        if listing.area_code is not None and listing.area_code in self.excluded_areas:
            return False
        blob = f"{listing.title} {listing.description}".lower()
        if any(word in blob for word in self.excluded_keywords):
            return False
        return True
