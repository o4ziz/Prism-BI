"""Filesystem ``.prism`` project store."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from prism_bi.domain.entities.project import Project
from prism_bi.domain.errors import ValidationError
from prism_bi.infrastructure.persistence.project_store.schema import (
    CURRENT_FORMAT_VERSION,
    load_project_json,
    save_project_json,
)

PROJECT_JSON = "project.json"
WAREHOUSE = "warehouse.duckdb"
ARTIFACTS = "artifacts"


class PrismProjectStore:
    """Creates/opens/saves ``.prism`` directory packages."""

    def create(self, root: Path, name: str) -> Project:
        root = root.resolve()
        if root.exists() and any(root.iterdir()):
            raise ValidationError(
                f"Project directory is not empty: {root}",
                code="project_dir_not_empty",
            )
        root.mkdir(parents=True, exist_ok=True)
        (root / ARTIFACTS).mkdir(exist_ok=True)
        project = Project(name=name, format_version=CURRENT_FORMAT_VERSION, id=uuid4())
        save_project_json(root / PROJECT_JSON, project)
        # Touch warehouse path by creating empty parent; DuckDB creates file on open.
        return project

    def open(self, root: Path) -> Project:
        root = root.resolve()
        path = root / PROJECT_JSON
        if not path.is_file():
            raise ValidationError(f"Missing {PROJECT_JSON} in {root}", code="project_missing")
        project = load_project_json(path)
        (root / ARTIFACTS).mkdir(exist_ok=True)
        return project

    def save(self, root: Path, project: Project) -> None:
        root = root.resolve()
        save_project_json(root / PROJECT_JSON, project)

    def warehouse_path(self, root: Path) -> Path:
        return root.resolve() / WAREHOUSE

    def add_recent(self, recent_file: Path, project_root: Path, *, limit: int = 10) -> None:
        """Maintain a simple recent-projects list under user data."""
        recent_file.parent.mkdir(parents=True, exist_ok=True)
        entries: list[str] = []
        if recent_file.is_file():
            try:
                entries = list(json.loads(recent_file.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                entries = []
        path_str = str(project_root.resolve())
        entries = [item for item in entries if item != path_str]
        entries.insert(0, path_str)
        recent_file.write_text(json.dumps(entries[:limit], indent=2), encoding="utf-8")

    def list_recent(self, recent_file: Path) -> list[Path]:
        if not recent_file.is_file():
            return []
        try:
            entries = json.loads(recent_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return [Path(item) for item in entries if isinstance(item, str)]
