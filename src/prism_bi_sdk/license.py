"""License provider contract (noop in V1)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class ILicenseProvider(IPlugin, Protocol):
    """Commercial license checks; V1 may ship a permissive noop."""

    def is_licensed(self, feature: str) -> bool:
        """Return whether ``feature`` is licensed for this install."""
