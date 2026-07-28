"""Source layer.

`base` defines the `Source` interface and a small registry. Concrete connectors
register themselves against a logical name and are built at runtime. The
production connectors are private and live outside this repository; importing
this package only wires up the public example connector.
"""
from . import example_source  # noqa: F401  (registers "example")
from .base import Source, available, build, register

__all__ = ["Source", "available", "build", "register"]
