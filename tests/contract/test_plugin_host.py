"""Plugin host discovery and soft-fail (Phase 1.4)."""

from __future__ import annotations

from pathlib import Path

from prism_bi.application.jobs import JobOrchestrator
from prism_bi.infrastructure.config import load_config
from prism_bi.infrastructure.plugins import PluginHost
from prism_bi.infrastructure.security import InMemorySecretStore
from prism_bi_sdk.contributions import ContributionKind


def _host(tmp_path: Path, plugins_root: Path) -> PluginHost:
    config = load_config(user_data_dir=tmp_path)
    jobs = JobOrchestrator()
    host = PluginHost(config, InMemorySecretStore(), jobs)
    host.discover_and_load([plugins_root])
    return host


def test_loads_first_party_plugins(tmp_path: Path) -> None:
    repo_plugins = Path(__file__).resolve().parents[2] / "plugins"
    host = _host(tmp_path, repo_plugins)
    try:
        active_ids = {plugin.manifest.id for plugin in host.active_plugins()}
        assert "prism.ai.null" in active_ids
        assert "prism.datasource.stub" in active_ids
        assert host.registry.list_by_kind(ContributionKind.AI_PROVIDERS)
        assert host.registry.list_by_kind(ContributionKind.DATA_SOURCES)
    finally:
        host.deactivate_all()
        host._jobs.shutdown(wait=False)  # noqa: SLF001


def test_incompatible_api_version_does_not_abort_boot(tmp_path: Path) -> None:
    broken = tmp_path / "plugins" / "broken_plugin"
    broken.mkdir(parents=True)
    (broken / "plugin.toml").write_text(
        "\n".join(
            [
                'id = "broken.plugin"',
                'name = "Broken"',
                'version = "0.0.1"',
                "api_version = 99",
                'entry_module = "missing"',
                'entry_class = "Missing"',
            ]
        ),
        encoding="utf-8",
    )
    # Also include a good plugin beside it
    repo_plugins = Path(__file__).resolve().parents[2] / "plugins"
    config = load_config(user_data_dir=tmp_path)
    jobs = JobOrchestrator()
    host = PluginHost(config, InMemorySecretStore(), jobs)
    try:
        host.discover_and_load([repo_plugins, tmp_path / "plugins"])
        assert any(
            plugin.manifest.id == "broken.plugin" and plugin.error for plugin in host.plugins
        )
        assert host.active_plugins(), "Good plugins must still activate"
    finally:
        host.deactivate_all()
        jobs.shutdown(wait=False)
