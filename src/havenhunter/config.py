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
    telegram_chat_id: str
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


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


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

    return Settings(
        profiles=profiles,
        telegram_token=_env("TELEGRAM_TOKEN"),
        telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
        sheets_credentials_path=_env("SHEETS_CREDENTIALS_PATH"),
        dedup_url=_env("DEDUP_URL"),
        dedup_key=_env("DEDUP_KEY"),
        scan_interval_minutes=int(_env("SCAN_INTERVAL_MINUTES", "0") or "0"),
    )
