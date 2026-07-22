"""Explicit composition root — no DI framework."""

from __future__ import annotations

import logging
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from prism_bi.application.export import ExportArtifactBuilder, ExporterRegistry
from prism_bi.application.jobs import JobOrchestrator
from prism_bi.application.visualization import AnalyticsChartDataProvider, ChartRendererRegistry
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.infrastructure.config import AppConfig, load_config
from prism_bi.infrastructure.logging import setup_logging
from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi.infrastructure.persistence.project_store import PrismProjectStore
from prism_bi.infrastructure.plugins import PluginHost, default_plugin_search_paths
from prism_bi.infrastructure.security import InMemorySecretStore, KeyringSecretStore, SecretStore
from prism_bi.presentation.export.chart_image_renderer import QtChartImageRenderer


@dataclass
class AppContainer:
    """Wired application services for host and tests."""

    config: AppConfig
    logger: logging.Logger
    secrets: SecretStore
    jobs: JobOrchestrator
    plugins: PluginHost
    repo_root: Path
    workspace: WorkspaceSession
    chart_data: AnalyticsChartDataProvider
    chart_renderers: ChartRendererRegistry
    exporters: ExporterRegistry
    export_builder: ExportArtifactBuilder


def _default_install_root() -> Path:
    """Repository root in source trees; executable directory when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def build_container(
    *,
    repo_root: Path | None = None,
    user_data_dir: Path | None = None,
    use_keyring: bool = True,
    console_logging: bool = True,
    defer_plugin_activation: bool = False,
) -> AppContainer:
    """Construct the application container with explicit wiring.

    Pass ``defer_plugin_activation=True`` for UI startup so ``activate()`` runs
    after QApplication is up (Milestone 5.4). Tests should keep the default.
    """
    root = repo_root or _default_install_root()
    config = load_config(user_data_dir=user_data_dir)
    config.user_data_dir.mkdir(parents=True, exist_ok=True)
    (config.user_data_dir / "plugins").mkdir(parents=True, exist_ok=True)

    logger = setup_logging(
        config.logging,
        log_dir=config.user_data_dir / "logs",
        console=console_logging,
    )
    if config.settings_recovered:
        logger.warning(
            "User settings were corrupt and reset to defaults "
            "(backup may exist as settings.toml.bak under %s)",
            config.user_data_dir,
        )

    secrets: SecretStore = KeyringSecretStore() if use_keyring else InMemorySecretStore()
    jobs = JobOrchestrator()
    analytics = DuckDBAnalyticsStore()
    project_store = PrismProjectStore()
    workspace = WorkspaceSession(
        project_store=project_store,
        analytics=analytics,
        recent_file=config.user_data_dir / "recent_projects.json",
        memory_budget_mb=config.performance.memory_budget_mb,
    )

    plugin_host = PluginHost(
        config,
        secrets,
        jobs,
        logger=logger,
        dataset_summaries_provider=workspace.dataset_summaries,
        trusted_user_plugin_ids=_load_trusted_plugin_ids(config.user_data_dir),
    )

    search = default_plugin_search_paths(config, repo_plugins_dir=root / "plugins")
    plugin_host.discover_and_load(search, activate=not defer_plugin_activation)

    chart_data = AnalyticsChartDataProvider(
        analytics,
        project_provider=lambda: workspace.project,
        max_points=config.performance.chart_max_points,
        max_categories=min(500, max(50, config.performance.chart_max_points // 20)),
    )
    chart_renderers = ChartRendererRegistry(plugin_host.registry)
    exporters = ExporterRegistry(plugin_host.registry)
    export_builder = ExportArtifactBuilder(
        analytics,
        chart_data,
        project_provider=lambda: workspace.project,
        image_renderer=QtChartImageRenderer(chart_renderers),
    )

    logger.info(
        "Container ready — plugins active=%s pending=%s failed=%s chart_types=%s formats=%s",
        len(plugin_host.active_plugins()),
        plugin_host.pending_count,
        sum(1 for plugin in plugin_host.plugins if plugin.error),
        chart_renderers.available_types(),
        exporters.available_formats(),
    )
    return AppContainer(
        config=config,
        logger=logger,
        secrets=secrets,
        jobs=jobs,
        plugins=plugin_host,
        repo_root=root,
        workspace=workspace,
        chart_data=chart_data,
        chart_renderers=chart_renderers,
        exporters=exporters,
        export_builder=export_builder,
    )


def _load_trusted_plugin_ids(user_data_dir: Path) -> frozenset[str]:
    """Read optional trusted user-plugin ids from settings.toml."""
    path = user_data_dir / "settings.toml"
    if not path.is_file():
        return frozenset()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        raw = data.get("plugins", {}).get("trusted_ids", [])
        if isinstance(raw, list):
            return frozenset(str(item) for item in raw)
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
        return frozenset()
    return frozenset()
