"""Project store round-trip and migration tests."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from prism_bi.domain.entities.project import Project
from prism_bi.domain.errors import ValidationError
from prism_bi.infrastructure.persistence.project_store import PrismProjectStore
from prism_bi.infrastructure.persistence.project_store.schema import (
    CURRENT_FORMAT_VERSION,
    project_from_dict,
)


def test_create_open_save_round_trip(tmp_path: Path) -> None:
    store = PrismProjectStore()
    root = tmp_path / "demo.prism"
    project = store.create(root, "Demo")
    assert (root / "project.json").is_file()
    project.name = "Demo Renamed"
    store.save(root, project)
    loaded = store.open(root)
    assert loaded.name == "Demo Renamed"
    assert loaded.format_version == CURRENT_FORMAT_VERSION


def test_reject_future_format(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(
        json.dumps({"format_version": 99, "id": str(uuid4()), "name": "x", "datasets": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        project_from_dict(json.loads(path.read_text(encoding="utf-8")))


def test_additive_v1_defaults_for_missing_keys() -> None:
    data = {
        "format_version": 1,
        "id": str(uuid4()),
        "name": "Legacy",
        "datasets": [],
    }
    project = project_from_dict(data)
    assert isinstance(project, Project)
    assert project.format_version == 1
    assert project.charts == []
    assert project.dashboards == []
    assert project.reports == []


def test_reject_pre_v1_format() -> None:
    with pytest.raises(ValidationError):
        project_from_dict({"format_version": 0, "id": str(uuid4()), "name": "x", "datasets": []})
