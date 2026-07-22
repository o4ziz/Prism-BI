"""Authentication provider contract (passthrough in V1)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class IAuthProvider(IPlugin, Protocol):
    """Identity provider; V1 uses a local passthrough implementation later."""

    def current_user_id(self) -> str | None:
        """Return the signed-in user id, or ``None`` if anonymous/local."""

    def is_authenticated(self) -> bool:
        """Return whether a user session is active."""
