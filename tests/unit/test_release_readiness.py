"""Release-readiness tests (config resilience, version identity)."""

from __future__ import annotations

from pathlib import Path

from prism_bi import __version__ as host_version
from prism_bi.infrastructure.config import load_config
from prism_bi_sdk import __version__ as sdk_version


def test_versions_are_ga_aligned() -> None:
    assert host_version == "1.0.0"
    assert sdk_version == "1.0.0"


def test_sample_project_ships() -> None:
    root = Path(__file__).resolve().parents[2]
    sample = root / "samples" / "SalesDemo.prism" / "project.json"
    csv = root / "samples" / "data" / "sales_demo.csv"
    assert sample.is_file(), "GA sample project missing — run scripts/build_sample_project.py"
    assert csv.is_file()
    text = sample.read_text(encoding="utf-8")
    assert "Sales Demo" in text
    assert "C:\\\\Users" not in text and "C:/Users" not in text


def test_first_party_plugin_versions_aligned() -> None:
    root = Path(__file__).resolve().parents[2] / "plugins"
    for toml in root.glob("*/plugin.toml"):
        text = toml.read_text(encoding="utf-8")
        assert 'version = "1.0.0"' in text, toml
        pkg_dirs = [p for p in toml.parent.iterdir() if p.is_dir() and p.name.startswith("prism_")]
        for pkg in pkg_dirs:
            init = pkg / "__init__.py"
            if init.is_file() and "__version__" in init.read_text(encoding="utf-8"):
                assert '__version__ = "1.0.0"' in init.read_text(encoding="utf-8"), init


def test_pyproject_is_production_stable() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in text
    assert "Development Status :: 5 - Production/Stable" in text


def test_corrupt_settings_toml_does_not_crash(tmp_path: Path) -> None:
    settings = tmp_path / "settings.toml"
    settings.write_text("this is not = valid toml [[[", encoding="utf-8")
    config = load_config(user_settings_path=settings, user_data_dir=tmp_path)
    assert config.app_name == "Prism BI"
    assert config.logging.level.upper() == "INFO"
