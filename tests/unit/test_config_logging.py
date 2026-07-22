"""Unit tests for configuration and logging (Phase 1.3)."""

from __future__ import annotations

from pathlib import Path

from prism_bi.infrastructure.config import load_config
from prism_bi.infrastructure.logging import setup_logging


def test_load_default_config(tmp_path: Path) -> None:
    config = load_config(user_data_dir=tmp_path)
    assert config.app_name == "Prism BI"
    assert config.performance.preview_rows == 200
    assert config.plugins.required_api_major == 1


def test_env_overrides_ai_flag(tmp_path: Path) -> None:
    config = load_config(user_data_dir=tmp_path, env={"PRISM_AI_ENABLED": "true"})
    assert config.features.ai_enabled is True


def test_setup_logging_writes_file(tmp_path: Path) -> None:
    config = load_config(user_data_dir=tmp_path)
    logger = setup_logging(config.logging, log_dir=tmp_path / "logs", console=False)
    logger.info("hello-phase-1")
    log_file = tmp_path / "logs" / "prism-bi.log"
    assert log_file.is_file()
    assert "hello-phase-1" in log_file.read_text(encoding="utf-8")
