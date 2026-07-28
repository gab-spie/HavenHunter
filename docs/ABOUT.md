# About this project

## Why it exists

Renting in a competitive market rewards whoever reaches a new listing first.
The listings are scattered across many sites and the good ones disappear within
hours. HavenHunter was built to remove the manual refreshing: it watches
several public sources, filters to what actually fits, and alerts on the new
matches through a phone-friendly review flow.

It started as a personal tool and grew into a small but real piece of software
with a clean architecture, tests, and a proper separation between the engine
and the sources it plugs into.

## What it demonstrates

This project is a compact showcase of end-to-end engineering, from data
retrieval to a usable product surface.

**Software design**
- A source-agnostic architecture built on a single normalized model and a fixed
  pipeline of independent stages.
- Interface-and-registry pattern for pluggable sources, so the system extends
  without modification.
- Pure, testable business rules separated from I/O.

**Asynchronous Python**
- Concurrent I/O with `asyncio` and `asyncio.gather`.
- Failure isolation so one slow or failing source never sinks a run.

**Product and UX**
- A stateful, interactive Telegram bot: per-chat sessions, edit-in-place cards,
  instant feedback, a guided one-at-a-time review, and copy-ready messages.
- Attention to the small details that make a tool pleasant to use rather than
  just functional.

**Integrations and automation**
- Google Sheets as a shared, human-readable tracker via service-account auth.
- Scheduled, unattended runs with state that survives restarts.

**Engineering discipline**
- Secrets kept entirely out of the repository and read from the environment.
- Graceful degradation when optional services are not configured.
- Tests that exercise the pipeline end to end.
- Clear documentation of the design and its trade-offs.

## Skills summary

Python · asyncio · software architecture · API and service integration ·
Telegram bot development · Google Sheets automation · scheduling · YAML-driven
configuration · testing · secret management · technical writing.

## About the author

Gabin Spiewak, graduate student in finance, comfortable moving between
quantitative work and building real software. This project reflects a habit of
turning a concrete problem into a well-structured, maintainable tool.
