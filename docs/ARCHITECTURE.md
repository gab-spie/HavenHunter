# Architecture

This document explains the design decisions behind HavenHunter. The guiding
idea is simple: normalize early, then keep every stage independent.

## The normalized core

Everything that moves through the system is a `Listing` (`models.py`). Sources
produce them, `Criteria` accept or reject them, the dedup store remembers them,
the notifier presents them, the logger records them. Because there is exactly
one shape, no stage past the source needs to know where a listing came from.

`Criteria` is a separate object holding the acceptance rules, and
`Criteria.accepts` is a pure function. Rules are data, evaluation has no side
effects, and both are trivial to unit test.

## Stages

```
sources  ->  filter  ->  dedup  ->  rank  ->  notify + log + export
```

Each stage has one job and one dependency direction. This is what lets the
project grow safely:

- **Sources** implement one async interface (`sources/base.py`) and register
  under a logical name. The pipeline builds them from the registry and never
  imports a concrete connector. Adding a source is additive; nothing downstream
  changes.
- **Filter** applies `Criteria.accepts`. Pure, ordered, cheap.
- **Dedup** (`dedup.py`) is the memory. `filter_new` returns only unseen
  listings and records them as it goes, collapsing duplicates within a batch as
  well as across runs. This is the single mechanism that makes the whole engine
  idempotent.
- **Rank** (`ranking.py`) orders the fresh delta best-first with a small,
  documented heuristic (value and freshness, batch-normalized). It is a pure
  function on a list of listings, so it needs no external context and is trivial
  to test.
- **Notify + log + export** consume only the ranked fresh delta.

## Ranking

Ranking is deliberately not a black box. Two signals, fixed and visible weights:

- **value**: price per square meter, lower is better. A missing surface falls
  back to a conservative assumption so hiding the size is never rewarded.
- **freshness**: how recently the listing was posted, when that date is
  reliable. Unknown dates score neutrally rather than last.

Both signals are normalized within the batch, then combined with documented
weights. The point is auditability: anyone can read `ranking.py` and know
exactly why one listing sits above another.

## Scheduling

Two options, same entry point:

- **In-process**: setting `SCAN_INTERVAL_MINUTES` makes the bot's own job queue
  run a full scan on that interval while it is up. No extra dependency.
- **OS-level**: a `launchd` example (`deploy/`) runs and supervises the process
  outside the bot, restarting it on crash or at login. The Linux equivalent is a
  `systemd` user service.

## Failure isolation

Live sources are unreliable by nature: pages change between requests, a source
can rate-limit or return a partial page, listings get pulled by their owners.
The pipeline treats that as normal.

- Sources are fetched concurrently with `asyncio.gather`.
- Each fetch is wrapped so an exception or timeout in one source yields an empty
  list instead of aborting the run (`pipeline._safe_fetch`).
- The count of listings seen per run therefore varies, and that is expected. It
  reflects live site state, not data loss: anything genuinely new that a source
  misses on one run is caught on the next, because dedup only ever suppresses
  listings already shown.

## The Telegram review flow

The notifier (`notifier.py`) deliberately avoids dumping a batch into the chat.
Instead it runs a guided review, one card at a time, held in a per-chat session
(`Review`).

- The **card** shows the listing, an origin badge, and a live counter, with
  inline buttons: Open, Validate, Skip, Done.
- A **second bubble** holds only a ready-to-copy contact message, wrapped so it
  is a single tap to copy.
- Every button press **answers with a toast first**, then does any bookkeeping.
  The interface never feels dead, even when logging or persistence is slow.
- Inline keyboards only use `http(s)` or `tg://` URLs, because other schemes
  break the entire keyboard on Telegram. The keyboard builder enforces this by
  construction.
- A review can be paused with **Done** and resumed later from the same position.

## Configuration and secrets

One YAML file (`config.py`, `config.example.yaml`) describes every profile: its
label, criteria, per-source budgets and message template. A common block holds
shared rules. The file is deliberately **secret-free**. Tokens, chat ids and
credential paths are read from the environment, and the persistent dedup store
and Sheets logger both degrade to no-ops when their configuration is absent, so
the engine runs in reduced form anywhere without special-casing.

## What is intentionally not here

The production source connectors are private and excluded from the public
repository. They implement the same `Source` interface as the shipped example
connector. Keeping them out means this repository is about the architecture and
the engineering, not about any particular site.
