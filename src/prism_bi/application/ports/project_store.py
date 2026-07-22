"""Project persistence port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from prism_bi.domain.entities.project import Project


@runtime_checkable
class IProjectStore(Protocol):
    """Reads/writes ``.prism`` project packages."""

    def create(self, root: Path, name: str) -> Project:
        """Create a new project directory with ``project.json`` + warehouse."""

    def open(self, root: Path) -> Project:
        """Open an existing project, applying migrations as needed."""

    def save(self, root: Path, project: Project) -> None:
        """Persist ``project.json`` (warehouse managed separately)."""

    def warehouse_path(self, root: Path) -> Path:
        """Return path to ``warehouse.duckdb`` inside the project."""

    def add_recent(self, recent_file: Path, project_root: Path, *, limit: int = 10) -> None:
        """Record a project in the recent list."""

    def list_recent(self, recent_file: Path) -> list[Path]:
        """Return recent project paths."""
