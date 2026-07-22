"""Contribution kinds and registry protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class ContributionKind(StrEnum):
    """Extension points plugins may register."""

    DATA_SOURCES = "data_sources"
    CHARTS = "charts"
    EXPORTERS = "exporters"
    CLEANING_STEPS = "cleaning_steps"
    AI_PROVIDERS = "ai_providers"
    AUTH_PROVIDERS = "auth_providers"
    COMMANDS = "commands"
    SETTINGS_PAGES = "settings_pages"
    WIZARDS = "wizards"
    WIDGETS = "widgets"
    THEMES = "themes"


@dataclass(frozen=True, slots=True)
class ContributionRegistration:
    """A single contribution declared during ``register``."""

    kind: ContributionKind
    contribution_id: str
    factory: Any
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PluginRegistry(Protocol):
    """Host registry accepting contribution declarations."""

    def add(self, registration: ContributionRegistration) -> None:
        """Register a contribution; duplicate ids for the same kind raise."""
