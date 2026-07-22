"""SDK contract smoke — partner can implement against SDK alone."""

from __future__ import annotations

from prism_bi_sdk import (
    API_VERSION_MAJOR,
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
)
from prism_bi_sdk.ai import AICapability
from prism_bi_sdk.contributions import PluginRegistry


class _FakeRegistry:
    def __init__(self) -> None:
        self.items: list[ContributionRegistration] = []

    def add(self, registration: ContributionRegistration) -> None:
        self.items.append(registration)


class _FakeAIPlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="partner.ai.fake",
            name="Fake",
            version="0.0.1",
            api_version=API_VERSION_MAJOR,
            entry_module="x",
            entry_class="Y",
        )

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
                contribution_id="partner.ai.fake",
                factory=self,
            )
        )

    def activate(self, context: object) -> None:
        _ = context

    def deactivate(self) -> None:
        return None

    def complete(self, prompt: str, *, context: dict[str, object] | None = None) -> str:
        _ = context
        return prompt.upper()


def test_partner_fake_plugin_registers_without_host_imports() -> None:
    plugin = _FakeAIPlugin()
    registry = _FakeRegistry()
    plugin.register(registry)
    assert registry.items[0].kind == ContributionKind.AI_PROVIDERS
    assert plugin.complete("hi") == "HI"
