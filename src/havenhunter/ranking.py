"""Ranking.

Once a run has its fresh matches, they are ordered best-first so the guided
review surfaces the strongest listings while attention is highest. The score is
a small, transparent heuristic over the normalized `Listing` fields, not a
black box: two signals, fixed weights, normalized within the batch so the
function needs no external context.

Signals:

* value    - price per square meter. Lower is better. Missing surface falls
             back to a conservative assumption so a listing is never rewarded
             for hiding its size.
* freshness- how recently it was posted, when that date is reliable. Unknown
             dates score neutrally rather than last.

Weights are deliberately explicit and documented so the ordering is auditable.
"""
from __future__ import annotations

from datetime import datetime

from .models import Listing

WEIGHT_VALUE = 0.6
WEIGHT_FRESHNESS = 0.4
_FALLBACK_SURFACE = 20.0  # m2 assumed when a listing hides its size


def _price_per_m2(listing: Listing) -> float:
    surface = listing.surface if listing.surface and listing.surface > 0 else _FALLBACK_SURFACE
    return listing.price / surface


def _age_hours(listing: Listing, now: datetime) -> float | None:
    if not (listing.published_at and listing.published_at_reliable):
        return None
    delta = now - listing.published_at
    return max(delta.total_seconds() / 3600.0, 0.0)


def _normalize_low_is_best(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(hi - v) / (hi - lo) for v in values]


def score_batch(listings: list[Listing]) -> list[tuple[Listing, float]]:
    """Return each listing paired with its 0..1 score, batch-normalized."""
    if not listings:
        return []
    now = datetime.now()

    ppm2 = [_price_per_m2(l) for l in listings]
    value = _normalize_low_is_best(ppm2)

    ages = [_age_hours(l, now) for l in listings]
    known = [a for a in ages if a is not None]
    if known:
        norm_known = _normalize_low_is_best(known)
        it = iter(norm_known)
        freshness = [next(it) if a is not None else 0.5 for a in ages]
    else:
        freshness = [0.5 for _ in ages]

    scored = []
    for listing, v, f in zip(listings, value, freshness):
        scored.append((listing, WEIGHT_VALUE * v + WEIGHT_FRESHNESS * f))
    return scored


def rank(listings: list[Listing]) -> list[Listing]:
    """Return the listings ordered best-first."""
    scored = score_batch(listings)
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [listing for listing, _ in scored]
