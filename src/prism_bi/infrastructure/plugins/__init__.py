"""Plugin host: discovery, registry, activation, soft-fail, lazy activate."""

from __future__ import annotations

import importlib
import logging
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prism_bi.application.jobs import JobOrchestrator
from prism_bi.infrastructure.config import AppConfig
from prism_bi.infrastructure.security import SecretStore
from prism_bi_sdk import API_VERSION_MAJOR
from prism_bi_sdk.contributions import ContributionKind, ContributionRegistration
from prism_bi_sdk.dto.job import JobHandle
from prism_bi_sdk.plugin import IPlugin, PluginManifest

_LOGGER = logging.getLogger("prism_bi.plugins")


class ContributionRegistry:
    """In-memory contribution registry implementing PluginRegistry."""

    def __init__(self) -> None:
        self._items: dict[ContributionKind, dict[str, ContributionRegistration]] = {
            kind: {} for kind in ContributionKind
        }

    def add(self, registration: ContributionRegistration) -> None:
        bucket = self._items[registration.kind]
        if registration.contribution_id in bucket:
            raise ValueError(
                f"Duplicate contribution {registration.kind.value}:{registration.contribution_id}"
            )
        bucket[registration.contribution_id] = registration

    def list_by_kind(self, kind: ContributionKind) -> list[ContributionRegistration]:
        return list(self._items[kind].values())

    def all(self) -> list[ContributionRegistration]:
        result: list[ContributionRegistration] = []
        for bucket in self._items.values():
            result.extend(bucket.values())
        return result


@dataclass
class LoadedPlugin:
    """Runtime record for a discovered plugin."""

    manifest: PluginManifest
    instance: IPlugin | None
    path: Path
    active: bool = False
    error: str | None = None
    trusted_user_plugin: bool = False


@dataclass
class HostPluginContext:
    """Concrete PluginContext for activated plugins."""

    config: AppConfig
    secrets: SecretStore
    jobs: JobOrchestrator
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("prism_bi.plugin"))
    dataset_summaries_provider: Callable[[], tuple[Mapping[str, Any], ...]] = field(
        default_factory=lambda: lambda: ()
    )

    def log(self, level: str, message: str, **fields: Any) -> None:
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        # Never log values that look like secrets.
        safe = {k: ("***" if _looks_secret(k) else v) for k, v in fields.items()}
        if safe:
            log_method("%s | %s", message, safe)
        else:
            log_method("%s", message)

    def get_config(self, namespace: str) -> Mapping[str, Any]:
        return self.config.namespace(namespace)

    def get_secret(self, key: str) -> str | None:
        return self.secrets.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self.secrets.set(key, value)

    def submit_job(
        self,
        name: str,
        worker: Any,
    ) -> JobHandle:
        return self.jobs.submit(name, worker)

    def list_dataset_summaries(self) -> tuple[Mapping[str, Any], ...]:
        return self.dataset_summaries_provider()


def _looks_secret(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("password", "secret", "token", "api_key", "apikey"))


class PluginHost:
    """Discovers, loads, and activates plugins from configured directories."""

    def __init__(
        self,
        config: AppConfig,
        secrets: SecretStore,
        jobs: JobOrchestrator,
        *,
        logger: logging.Logger | None = None,
        dataset_summaries_provider: Callable[[], tuple[Mapping[str, Any], ...]] | None = None,
        trusted_user_plugin_ids: frozenset[str] | None = None,
    ) -> None:
        self._config = config
        self._secrets = secrets
        self._jobs = jobs
        self._logger = logger or logging.getLogger("prism_bi.plugins")
        self._dataset_summaries_provider = dataset_summaries_provider or (lambda: ())
        self.registry = ContributionRegistry()
        self.plugins: list[LoadedPlugin] = []
        self._pending: list[tuple[LoadedPlugin, HostPluginContext]] = []
        self._trusted_user_plugin_ids = trusted_user_plugin_ids or frozenset()
        self._user_plugins_root = (config.user_data_dir / "plugins").resolve()

    def discover_and_load(
        self,
        search_paths: Sequence[Path],
        *,
        activate: bool = True,
    ) -> None:
        """Scan paths for plugin.toml; optionally defer activate (M5.4)."""
        context = HostPluginContext(
            config=self._config,
            secrets=self._secrets,
            jobs=self._jobs,
            logger=self._logger,
            dataset_summaries_provider=self._dataset_summaries_provider,
        )
        for root in search_paths:
            if not root.is_dir():
                continue
            for manifest_path in sorted(root.glob("*/plugin.toml")):
                self._load_one(manifest_path, context, activate=activate)

    def activate_pending(self) -> int:
        """Activate plugins registered with activate=False. Returns count activated."""
        activated = 0
        pending = list(self._pending)
        self._pending.clear()
        for loaded, context in pending:
            if loaded.instance is None:
                continue
            try:
                loaded.instance.activate(context)
                loaded.active = True
                activated += 1
                self._logger.info(
                    "Activated plugin %s (%s)", loaded.manifest.id, loaded.manifest.version
                )
            except Exception as exc:  # noqa: BLE001
                self._logger.exception("Plugin %s failed to activate", loaded.manifest.id)
                loaded.error = str(exc)
                loaded.active = False
                if not self._config.plugins.continue_on_error:
                    raise
        return activated

    def _load_one(
        self,
        manifest_path: Path,
        context: HostPluginContext,
        *,
        activate: bool,
    ) -> None:
        plugin_dir = manifest_path.parent
        try:
            manifest = _read_manifest(manifest_path)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Failed to read %s: %s", manifest_path, exc)
            self.plugins.append(
                LoadedPlugin(
                    manifest=PluginManifest(
                        id=plugin_dir.name,
                        name=plugin_dir.name,
                        version="0",
                        api_version=0,
                        entry_module="",
                        entry_class="",
                    ),
                    instance=None,
                    path=plugin_dir,
                    error=str(exc),
                )
            )
            return

        if manifest.api_version != self._config.plugins.required_api_major:
            message = (
                f"Incompatible api_version {manifest.api_version}; "
                f"host requires major {self._config.plugins.required_api_major} "
                f"(SDK {API_VERSION_MAJOR})"
            )
            self._logger.warning("Skipping plugin %s: %s", manifest.id, message)
            self.plugins.append(
                LoadedPlugin(manifest=manifest, instance=None, path=plugin_dir, error=message)
            )
            return

        # User-folder plugins require prior trust (M5.6).
        try:
            under_user = plugin_dir.resolve().is_relative_to(self._user_plugins_root)
        except (OSError, ValueError):
            under_user = False
        if under_user and manifest.id not in self._trusted_user_plugin_ids:
            message = "Untrusted user plugin — enable in settings/trust list before load"
            self._logger.warning("Skipping untrusted user plugin %s", manifest.id)
            self.plugins.append(
                LoadedPlugin(
                    manifest=manifest,
                    instance=None,
                    path=plugin_dir,
                    error=message,
                    trusted_user_plugin=False,
                )
            )
            return

        try:
            instance = _instantiate(plugin_dir, manifest)
            instance.register(self.registry)
            loaded = LoadedPlugin(
                manifest=manifest,
                instance=instance,
                path=plugin_dir,
                active=False,
                trusted_user_plugin=under_user,
            )
            self.plugins.append(loaded)
            if activate:
                instance.activate(context)
                loaded.active = True
                self._logger.info("Activated plugin %s (%s)", manifest.id, manifest.version)
            else:
                self._pending.append((loaded, context))
                self._logger.info("Registered plugin %s (activation deferred)", manifest.id)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Plugin %s failed to load", manifest.id)
            self.plugins.append(
                LoadedPlugin(manifest=manifest, instance=None, path=plugin_dir, error=str(exc))
            )
            if not self._config.plugins.continue_on_error:
                raise

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def active_plugins(self) -> list[LoadedPlugin]:
        return [plugin for plugin in self.plugins if plugin.active]

    def plugin_summaries(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for plugin in self.plugins:
            summaries.append(
                {
                    "id": plugin.manifest.id,
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "active": plugin.active,
                    "error": plugin.error,
                }
            )
        return summaries

    def deactivate_all(self) -> None:
        for plugin in self.plugins:
            if plugin.instance is not None and plugin.active:
                try:
                    plugin.instance.deactivate()
                except Exception:  # noqa: BLE001
                    self._logger.exception("Deactivate failed for %s", plugin.manifest.id)
                plugin.active = False
        self._pending.clear()


def _read_manifest(path: Path) -> PluginManifest:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return PluginManifest(
        id=str(data["id"]),
        name=str(data["name"]),
        version=str(data["version"]),
        api_version=int(data["api_version"]),
        entry_module=str(data["entry_module"]),
        entry_class=str(data["entry_class"]),
        description=str(data.get("description", "")),
    )


def _instantiate(plugin_dir: Path, manifest: PluginManifest) -> IPlugin:
    plugin_root = str(plugin_dir.resolve())
    if plugin_root not in sys.path:
        sys.path.insert(0, plugin_root)
    module = importlib.import_module(manifest.entry_module)
    cls = getattr(module, manifest.entry_class)
    instance = cls()
    return instance  # type: ignore[no-any-return]


def default_plugin_search_paths(
    config: AppConfig,
    *,
    repo_plugins_dir: Path | None = None,
) -> list[Path]:
    """Built-in repo plugins + user_data/plugins + configured dirs."""
    paths: list[Path] = []
    if repo_plugins_dir is not None:
        paths.append(repo_plugins_dir)
    paths.append(config.user_data_dir / "plugins")
    for raw in config.plugins.plugin_dirs:
        paths.append(Path(raw))
    return paths
