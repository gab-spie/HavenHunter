"""Configuration loader.

The whole system is config-driven. One YAML file describes every profile
(for example a shared-flat search and a solo search), each with its own
criteria, per-source budgets and message template. Secrets never live here;
they are read from the environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

from .models import Criteria


@dataclass
class Profile:
    name: str
    label: str
    criteria: Criteria
    message_template: str


@dataclass
class Settings:
    profiles: dict[str, Profile]
    telegram_token: str
    telegram_chat_id: int
    telegram_allowed_ids: frozenset[int]
    sheets_credentials_path: str
    dedup_url: str
    dedup_key: str
    scan_interval_minutes: int

    @property
    def has_sheets(self) -> bool:
        return bool(self.sheets_credentials_path)

    @property
    def scheduled(self) -> bool:
        return self.scan_interval_minutes > 0


class ConfigError(ValueError):
    """Raised when required configuration is missing or malformed."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _parse_chat_id(raw: str) -> int:
    """Turn TELEGRAM_CHAT_ID into an int, failing loudly and early.

    This is the sole owner id every command handler checks updates against,
    so an empty or malformed value must stop the boot rather than surface
    later as an obscure AttributeError or a bot that answers strangers.
    """
    raw = raw.strip()
    if not raw:
        raise ConfigError(
            "TELEGRAM_CHAT_ID is not set. Set it to the numeric chat id "
            "allowed to control the bot (see .env.example)."
        )
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(
            f"TELEGRAM_CHAT_ID must be a numeric chat id, got {raw!r}."
        ) from None


def _parse_allowed_ids(raw: str, owner_id: int) -> frozenset[int]:
    """Optional extra allowlist (TELEGRAM_ALLOWED_IDS), always including the owner."""
    ids = {owner_id}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise ConfigError(
                f"TELEGRAM_ALLOWED_IDS must be a comma-separated list of "
                f"numeric ids, got {part!r}."
            ) from None
    return frozenset(ids)


def load(path: str = "config.yaml") -> Settings:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    common = raw.get("common", {})
    profiles: dict[str, Profile] = {}
    for name, block in raw.get("profiles", {}).items():
        criteria = Criteria(
            max_price_per_source=block.get("budgets_per_source", {}),
            default_max_price=block.get("default_max_price", 0),
            min_rooms=block.get("min_rooms", 0),
            furnished_required=common.get("furnished_required", False),
            excluded_areas=common.get("excluded_areas", []),
            excluded_keywords=block.get("excluded_keywords", []),
        )
        profiles[name] = Profile(
            name=name,
            label=block.get("label", name),
            criteria=criteria,
            message_template=block.get("message_template", ""),
        )

    telegram_chat_id = _parse_chat_id(_env("TELEGRAM_CHAT_ID"))
    telegram_allowed_ids = _parse_allowed_ids(_env("TELEGRAM_ALLOWED_IDS"), telegram_chat_id)

    return Settings(
        profiles=profiles,
        telegram_token=_env("TELEGRAM_TOKEN"),
        telegram_chat_id=telegram_chat_id,
        telegram_allowed_ids=telegram_allowed_ids,
        sheets_credentials_path=_env("SHEETS_CREDENTIALS_PATH"),
        dedup_url=_env("DEDUP_URL"),
        dedup_key=_env("DEDUP_KEY"),
        scan_interval_minutes=int(_env("SCAN_INTERVAL_MINUTES", "0") or "0"),
    )
