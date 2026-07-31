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
import os
from dataclasses import dataclass

from .config import Profile
from .dedup import DedupStore
from .models import Listing
from .ranking import rank
from .sources import Source, build

# How long a single source gets to answer before it is treated as a failure.
# Configurable via env so a slow connector can be tuned without a code change.
FETCH_TIMEOUT_SECONDS = float(os.environ.get("SOURCE_FETCH_TIMEOUT_SECONDS", "30"))


@dataclass
class RunResult:
    profile: str
    total_seen: int          # everything sources returned, after criteria
    fresh: list[Listing]     # new, never-seen matches, best-first


async def _safe_fetch(
    source: Source, max_price: int, timeout: float = FETCH_TIMEOUT_SECONDS
) -> list[Listing]:
    try:
        return await asyncio.wait_for(source.fetch(max_price=max_price), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"[source {source.name}] failed: timed out after {timeout}s")
        return []
    except Exception as exc:  # one bad source must not sink the run
        # Log the exception type and source only, never str(exc): a
        # connector's error text can carry request URLs, headers or other
        # details that should not end up in shared logs.
        print(f"[source {source.name}] failed: {type(exc).__name__}")
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
