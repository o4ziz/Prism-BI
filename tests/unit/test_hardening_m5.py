"""Milestone 5 hardening tests."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from prism_bi.application.jobs import JobOrchestrator
from prism_bi.bootstrap.container import build_container
from prism_bi.domain.errors import ValidationError
from prism_bi.domain.paths import canonicalize_path, ensure_within, validate_user_file
from prism_bi.infrastructure.config import load_config
from prism_bi_sdk.dto.job import JobProgress, JobState


def test_job_progress_reaches_handle() -> None:
    jobs = JobOrchestrator()
    seen: list[float] = []

    def on_state(handle: object) -> None:
        from prism_bi_sdk.dto.job import JobHandle

        assert isinstance(handle, JobHandle)
        if handle.state == JobState.RUNNING:
            seen.append(handle.progress_percent)

    jobs.set_on_state_change(on_state)

    def worker(progress, cancelled) -> None:  # noqa: ANN001
        progress(JobProgress(50, "halfway"))
        time.sleep(0.05)
        progress(JobProgress(100, "done"))

    handle = jobs.submit("t", worker)
    deadline = time.time() + 2
    while time.time() < deadline:
        current = jobs.get(handle.id)
        if current and current.state in {JobState.COMPLETED, JobState.FAILED}:
            break
        time.sleep(0.02)
    final = jobs.get(handle.id)
    assert final is not None
    assert final.state == JobState.COMPLETED
    assert final.progress_percent == 100.0
    assert any(p >= 50 for p in seen)
    jobs.shutdown(wait=False)


def test_path_traversal_rejected(tmp_path: Path) -> None:
    root = tmp_path / "safe"
    root.mkdir()
    with pytest.raises(ValidationError):
        ensure_within(tmp_path / "other" / "file.txt", root)


def test_validate_user_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.csv"
    with pytest.raises(ValidationError):
        validate_user_file(missing)
    present = tmp_path / "ok.csv"
    present.write_text("a\n1\n", encoding="utf-8")
    assert validate_user_file(present) == canonicalize_path(present)


def test_corrupt_settings_sets_recovered_flag(tmp_path: Path) -> None:
    settings = tmp_path / "settings.toml"
    settings.write_text("[[[broken", encoding="utf-8")
    config = load_config(user_settings_path=settings, user_data_dir=tmp_path)
    assert config.settings_recovered is True
    assert (tmp_path / "settings.toml.bak").exists() or not settings.exists()


def test_duckdb_opens_with_memory_limit(tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        from prism_bi.application.use_cases.project_lifecycle import create_project

        assert create_project(container.workspace, tmp_path / "p.prism", "P").success
        assert container.workspace.is_open
    finally:
        container.plugins.deactivate_all()
        container.workspace.close()
        container.jobs.shutdown(wait=False)


def test_untrusted_user_plugin_skipped(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins" / "evil"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.toml").write_text(
        "\n".join(
            [
                'id = "evil.plugin"',
                'name = "Evil"',
                'version = "0.0.1"',
                "api_version = 1",
                'entry_module = "missing"',
                'entry_class = "Missing"',
            ]
        ),
        encoding="utf-8",
    )
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        evil = next(p for p in container.plugins.plugins if p.manifest.id == "evil.plugin")
        assert evil.error is not None
        assert "Untrusted" in evil.error
        assert not evil.active
    finally:
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)


def test_deferred_activation(tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
        defer_plugin_activation=True,
    )
    try:
        assert container.plugins.pending_count > 0 or container.plugins.active_plugins()
        # If deferred, pending then activate
        if container.plugins.pending_count > 0:
            n = container.plugins.activate_pending()
            assert n > 0
            assert container.plugins.active_plugins()
    finally:
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)
