"""Open-project workspace session shared by use cases and UI."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prism_bi.application.ports.analytics import IAnalyticsStore
from prism_bi.application.ports.project_store import IProjectStore
from prism_bi.domain.entities.project import Project
from prism_bi.domain.profiling import ProfileReport

_MAX_PROFILE_CACHE = 32


@dataclass
class WorkspaceSession:
    """Mutable session for the currently open project."""

    project_store: IProjectStore
    analytics: IAnalyticsStore
    recent_file: Path
    memory_budget_mb: int = 4096
    project: Project | None = None
    project_root: Path | None = None
    profile_cache: OrderedDict[str, ProfileReport] = field(default_factory=OrderedDict)

    @property
    def is_open(self) -> bool:
        return self.project is not None and self.project_root is not None

    def require_project(self) -> tuple[Project, Path]:
        if self.project is None or self.project_root is None:
            raise RuntimeError("No project is open")
        return self.project, self.project_root

    def dataset_summaries(self) -> tuple[dict[str, Any], ...]:
        if self.project is None:
            return ()
        return self.project.dataset_summaries()

    def save(self) -> None:
        project, root = self.require_project()
        self.project_store.save(root, project)

    def cache_profile(self, revision_key: str, report: ProfileReport) -> None:
        self.profile_cache[revision_key] = report
        self.profile_cache.move_to_end(revision_key)
        while len(self.profile_cache) > _MAX_PROFILE_CACHE:
            self.profile_cache.popitem(last=False)

    def open_warehouse(self, warehouse: Path) -> None:
        # Cap DuckDB at ~60% of configured budget (NFR-02 / M5.2).
        duck_mb = max(256, int(self.memory_budget_mb * 0.6))
        self.analytics.open(warehouse, memory_limit_mb=duck_mb)

    def close(self) -> None:
        self.analytics.close()
        self.project = None
        self.project_root = None
        self.profile_cache.clear()
