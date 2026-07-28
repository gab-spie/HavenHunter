# Skills

A focused map of what this project demonstrates, for anyone reading the code
with hiring in mind.

## Languages and runtime

- **Python 3.10+**, modern typing (`from __future__ import annotations`,
  dataclasses, `|` unions).
- **asyncio**: concurrent I/O with `asyncio.gather`, async interfaces.

## Software architecture

- Single normalized domain model (`Listing`) with pure acceptance rules
  (`Criteria`) separated from I/O.
- Interface plus registry for pluggable sources: the system extends by adding a
  class, never by editing the pipeline.
- A fixed, readable pipeline of independent stages: gather, filter, dedup, rank,
  deliver.
- Idempotent design: a dedup store guarantees each listing is shown once and
  never lost across runs.

## Product engineering

- Interactive Telegram bot: per-chat sessions, edit-in-place cards, instant
  toast feedback, a guided one-at-a-time review, copy-ready messages.
- A small, transparent ranking heuristic so the strongest matches surface first.
- Defensive orchestration: per-source failure isolation, transient network
  errors handled quietly.

## Integrations and automation

- Google Sheets as a shared tracker via service-account authentication.
- CSV export as a dependency-free companion.
- Unattended scheduling two ways: the bot's in-process job queue, or an
  OS-level agent (launchd example included).

## Engineering discipline

- Secrets kept entirely out of the repository, read from the environment.
- Graceful degradation when optional services are absent.
- Tests exercising the pipeline, ranking and export end to end.
- Continuous integration on every push across three Python versions.
- Documentation of the design and its trade-offs.

## Toolbox

Python, asyncio, python-telegram-bot, gspread, Google service-account auth,
YAML configuration, pytest, GitHub Actions, launchd, Git.
