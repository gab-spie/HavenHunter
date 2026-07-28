"""Source interface.

A `Source` is anything that can produce normalized `Listing` objects for a
given search. The pipeline only ever talks to this interface, so adding or
removing a source never touches the filtering, dedup, notification or logging
layers.

The concrete connectors used in production are intentionally kept out of this
public repository. They live behind this same interface and are swapped in at
runtime through the registry. `ExampleSource` documents the contract and lets
the pipeline run end to end with sample data.
"""
from __future__ import annotations

import abc
from typing import Callable

from ..models import Listing

# A registry maps a logical source name to a factory. Real deployments register
# their private connectors here at startup; nothing downstream needs to change.
_REGISTRY: dict[str, "Callable[..., Source]"] = {}


def register(name: str):
    """Decorator to register a source factory under a logical name."""
    def wrap(factory: "Callable[..., Source]"):
        _REGISTRY[name] = factory
        return factory
    return wrap


def build(name: str, **kwargs) -> "Source":
    if name not in _REGISTRY:
        raise KeyError(f"no source registered under {name!r}")
    return _REGISTRY[name](**kwargs)


def available() -> list[str]:
    return sorted(_REGISTRY)


class Source(abc.ABC):
    """Async producer of normalized listings for one logical origin."""

    name: str = "source"

    @abc.abstractmethod
    async def fetch(self, max_price: int, max_pages: int = 2) -> list[Listing]:
        """Return listings for the configured search, newest first.

        Implementations are responsible only for retrieving and normalizing
        raw data into `Listing` objects. All acceptance logic (budget, rooms,
        keywords, excluded areas) is applied later by `Criteria`, so a source
        should return everything it can see and let the pipeline decide.
        """
        raise NotImplementedError
