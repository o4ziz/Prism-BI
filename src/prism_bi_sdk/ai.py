"""AI provider plugin contract."""

from __future__ import annotations

from enum import Flag, auto
from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.plugin import IPlugin


class AICapability(Flag):
    """Capabilities declared by an AI provider."""

    COMPLETE = auto()
    STRUCTURED_OUTPUT = auto()
    EMBED = auto()


@runtime_checkable
class IAIProvider(IPlugin, Protocol):
    """Pluggable AI backend (null provider ships in V1)."""

    @property
    def capabilities(self) -> AICapability:
        """Return supported AI capabilities."""

    def complete(self, prompt: str, *, context: dict[str, Any] | None = None) -> str:
        """Return a completion string; may raise if unsupported."""
