"""HavenHunter: a source-agnostic housing-search aggregation and alerting engine.

The package is organized around a single normalized `Listing` model and a small
set of composable stages:

    sources  ->  filter  ->  dedup  ->  notify  ->  log

Each stage is independent. Sources are pluggable behind one interface, so the
filtering, deduplication, notification and logging layers never need to know
where a listing came from.
"""

__version__ = "1.0.0"
