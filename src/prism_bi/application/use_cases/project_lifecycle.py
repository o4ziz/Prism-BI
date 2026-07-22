"""Project create/open/save use cases."""

from __future__ import annotations

from pathlib import Path

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi.domain.paths import canonicalize_path


def create_project(session: WorkspaceSession, root: Path, name: str) -> OperationResult[Path]:
    try:
        session.close()
        resolved = canonicalize_path(root)
        project = session.project_store.create(resolved, name)
        warehouse = session.project_store.warehouse_path(resolved)
        session.open_warehouse(warehouse)
        session.project = project
        session.project_root = resolved
        session.project_store.add_recent(session.recent_file, resolved)
        session.save()
        return OperationResult.ok(resolved)
    except (DomainError, ValidationError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "project_create_failed"), message=str(exc)
        )


def open_project(session: WorkspaceSession, root: Path) -> OperationResult[Path]:
    try:
        session.close()
        resolved = canonicalize_path(root)
        project = session.project_store.open(resolved)
        warehouse = session.project_store.warehouse_path(resolved)
        session.open_warehouse(warehouse)
        session.project = project
        session.project_root = resolved
        session.project_store.add_recent(session.recent_file, resolved)
        return OperationResult.ok(resolved)
    except (DomainError, ValidationError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "project_open_failed"), message=str(exc)
        )


def save_project(session: WorkspaceSession) -> OperationResult[bool]:
    try:
        session.save()
        return OperationResult.ok(True)
    except (DomainError, ValidationError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "project_save_failed"), message=str(exc)
        )
