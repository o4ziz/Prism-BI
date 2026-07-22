"""Domain entities package."""

from __future__ import annotations

from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.entities.project import Project

__all__ = ["Dataset", "DatasetRevision", "Project"]
