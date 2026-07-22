"""Plugin lifecycle contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.contributions import PluginRegistry


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Declarative plugin identity loaded from ``plugin.toml``."""

    id: str
    name: str
    version: str
    api_version: int
    entry_module: str
    entry_class: str
    description: str = ""


@runtime_checkable
class IPlugin(Protocol):
    """Base lifecycle for every Prism BI plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Return identity metadata for this plugin instance."""

    def register(self, registry: PluginRegistry) -> None:
        """Declare contributions before activation."""

    def activate(self, context: PluginContext) -> None:
        """Activate the plugin with a host-provided context."""

    def deactivate(self) -> None:
        """Release resources; safe to call multiple times."""
