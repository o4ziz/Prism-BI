"""Configuration loading and typed settings."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PerformanceSettings:
    preview_rows: int = 200
    import_chunk_rows: int = 50_000
    grid_window_rows: int = 500
    chart_max_points: int = 10_000
    memory_budget_mb: int = 4096


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    max_bytes: int = 10_485_760
    backup_count: int = 5
    level: str = "INFO"


@dataclass(frozen=True, slots=True)
class PluginSettings:
    continue_on_error: bool = True
    required_api_major: int = 1
    plugin_dirs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    ai_enabled: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable application configuration."""

    app_name: str = "Prism BI"
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    plugins: PluginSettings = field(default_factory=PluginSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    user_data_dir: Path = field(default_factory=lambda: Path.home() / ".prism-bi")
    settings_recovered: bool = False

    def namespace(self, name: str) -> Mapping[str, Any]:
        """Expose a read-only config slice for PluginContext."""
        if name == "performance":
            return {
                "preview_rows": self.performance.preview_rows,
                "import_chunk_rows": self.performance.import_chunk_rows,
                "grid_window_rows": self.performance.grid_window_rows,
                "chart_max_points": self.performance.chart_max_points,
                "memory_budget_mb": self.performance.memory_budget_mb,
            }
        if name == "features":
            return {"ai_enabled": self.features.ai_enabled}
        if name == "app":
            return {"name": self.app_name}
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_default_toml() -> dict[str, Any]:
    """Load packaged default_config.toml."""
    root = resources.files("prism_bi.infrastructure.config")
    raw = root.joinpath("default_config.toml").read_bytes()
    return tomllib.loads(raw.decode("utf-8"))


def load_config(
    *,
    user_settings_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    user_data_dir: Path | None = None,
) -> AppConfig:
    """Load config with precedence: env PRISM_* → user settings → defaults.

    Corrupt or unreadable user settings are skipped (defaults remain) so a bad
    ``settings.toml`` cannot prevent startup.
    """
    data = load_default_toml()
    data_dir = user_data_dir or Path.home() / ".prism-bi"
    settings_path = user_settings_path or (data_dir / "settings.toml")
    settings_recovered = False
    if settings_path.is_file():
        try:
            with settings_path.open("rb") as handle:
                data = _deep_merge(data, tomllib.load(handle))
        except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
            settings_recovered = True
            try:
                backup = settings_path.with_suffix(".toml.bak")
                settings_path.replace(backup)
            except OSError:
                pass

    env_map = dict(env or {})
    log_level = env_map.get("PRISM_LOG_LEVEL")
    if log_level:
        data.setdefault("app", {})["log_level"] = log_level
        data.setdefault("logging", {})
        # Keep app.log_level as source of truth for LoggingSettings below.

    ai_flag = env_map.get("PRISM_AI_ENABLED")
    if ai_flag is not None:
        data.setdefault("features", {})["ai_enabled"] = ai_flag.lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    app = data.get("app", {})
    perf = data.get("performance", {})
    logging_cfg = data.get("logging", {})
    plugins_cfg = data.get("plugins", {})
    features_cfg = data.get("features", {})
    paths_cfg = data.get("paths", {})

    plugin_dirs = tuple(paths_cfg.get("plugin_dirs") or ())
    extra_dirs = plugins_cfg.get("plugin_dirs")
    if extra_dirs:
        plugin_dirs = plugin_dirs + tuple(extra_dirs)

    level = str(app.get("log_level", logging_cfg.get("level", "INFO")))

    return AppConfig(
        app_name=str(app.get("name", "Prism BI")),
        performance=PerformanceSettings(
            preview_rows=int(perf.get("preview_rows", 200)),
            import_chunk_rows=int(perf.get("import_chunk_rows", 50_000)),
            grid_window_rows=int(perf.get("grid_window_rows", 500)),
            chart_max_points=int(perf.get("chart_max_points", 10_000)),
            memory_budget_mb=int(perf.get("memory_budget_mb", 4096)),
        ),
        logging=LoggingSettings(
            max_bytes=int(logging_cfg.get("max_bytes", 10_485_760)),
            backup_count=int(logging_cfg.get("backup_count", 5)),
            level=level,
        ),
        plugins=PluginSettings(
            continue_on_error=bool(plugins_cfg.get("continue_on_error", True)),
            required_api_major=int(plugins_cfg.get("required_api_major", 1)),
            plugin_dirs=plugin_dirs,
        ),
        features=FeatureFlags(ai_enabled=bool(features_cfg.get("ai_enabled", False))),
        user_data_dir=data_dir,
        settings_recovered=settings_recovered,
    )
