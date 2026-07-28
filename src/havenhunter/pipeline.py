"""The search pipeline.

For one profile the pipeline runs the same four stages every time:

    1. gather   - fan out across every configured source, concurrently
    2. filter   - keep only listings the profile's criteria accept
    3. dedup    - drop anything already seen, remember the rest
    4. hand off - return the fresh matches for notification and logging

Sources are fetched concurrently and failures are isolated: one source raising
or timing out never takes down the run, it just contributes nothing that pass.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .config import Profile
from .dedup import DedupStore
from .models import Listing
from .ranking import rank
from .sources import Source, build


@dataclass
class RunResult:
    profile: str
    total_seen: int          # everything sources returned, after criteria
    fresh: list[Listing]     # new, never-seen matches, best-first


async def _safe_fetch(source: Source, max_price: int) -> list[Listing]:
    try:
        return await source.fetch(max_price=max_price)
    except Exception as exc:  # one bad source must not sink the run
        print(f"[source {source.name}] failed: {exc}")
        return []


async def gather(profile: Profile, source_names: list[str]) -> list[Listing]:
    sources = [build(name) for name in source_names]
    budgets = [profile.criteria.budget_for(name) for name in source_names]
    batches = await asyncio.gather(
        *(_safe_fetch(src, budget) for src, budget in zip(sources, budgets))
    )
    return [listing for batch in batches for listing in batch]


async def run(profile: Profile, source_names: list[str], store: DedupStore) -> RunResult:
    raw = await gather(profile, source_names)
    accepted = [l for l in raw if profile.criteria.accepts(l)]
    fresh = store.filter_new(accepted)
    fresh = rank(fresh)  # best matches surface first in the review
    return RunResult(profile=profile.name, total_seen=len(accepted), fresh=fresh)
