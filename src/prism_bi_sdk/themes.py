"""Theme contribution contract (host ships default themes in V1)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class IThemeContribution(IPlugin, Protocol):
    """Optional QSS theme contribution from a plugin."""

    @property
    def theme_id(self) -> str:
        """Stable theme id."""

    def stylesheet(self) -> str:
        """Return QSS stylesheet text."""
