"""Null AI provider — proves the AI extension slot without network calls."""

from __future__ import annotations

from typing import Any

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.ai import AICapability
from prism_bi_sdk.context import PluginContext


class NullAIPlugin:
    """IAIProvider implementation that returns a deterministic stub response."""

    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.ai.null",
            name="Null AI Provider",
            version="1.0.0",
            api_version=1,
            entry_module="prism_ai_null.plugin",
            entry_class="NullAIPlugin",
            description="No-op AI provider proving the AI extension slot.",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    @property
    def capabilities(self) -> AICapability:
        return AICapability.COMPLETE

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.AI_PROVIDERS,
                contribution_id="prism.ai.null",
                factory=self,
                display_name="Null AI Provider",
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context
        context.log("info", "Null AI provider activated")

    def deactivate(self) -> None:
        self._context = None

    def complete(self, prompt: str, *, context: dict[str, Any] | None = None) -> str:
        _ = context
        return f"[null-ai] No model configured. Prompt length={len(prompt)}."
