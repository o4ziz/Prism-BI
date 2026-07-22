"""Smoke tests — packages install and import cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest

import prism_bi
import prism_bi_sdk
from prism_bi.main import main


def test_sdk_and_host_versions_aligned() -> None:
    assert isinstance(prism_bi_sdk.__version__, str)
    assert prism_bi.__version__ == prism_bi_sdk.__version__ == "1.0.0"


def test_main_headless_returns_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PRISM_HEADLESS", "1")
    monkeypatch.setenv("PRISM_USER_DATA", str(tmp_path))
    assert main() == 0
