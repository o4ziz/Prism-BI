"""Import / materialize use case."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi.domain.value_objects.column_schema import ColumnSchema
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor


def import_materialize(
    session: WorkspaceSession,
    *,
    plugin_id: str,
    plan: MaterializePlan,
    alias: str | None = None,
    chunk_rows: int = 50_000,
) -> OperationResult[str]:
    """Execute a plugin MaterializePlan into the warehouse and catalog."""
    try:
        project, _root = session.require_project()
        revision_id = uuid4()
        session.analytics.materialize_revision(revision_id, plan, chunk_rows=chunk_rows)
        columns = _to_column_schemas(plan.columns)
        try:
            physical = session.analytics.columns(revision_id)
            if physical:
                columns = _to_column_schemas(physical)
        except DomainError:
            pass

        revision = DatasetRevision(
            id=revision_id,
            parent_id=None,
            created_at=datetime.now(UTC),
            label="import",
            columns=columns,
        )
        dataset = Dataset(
            alias=alias or plan.suggested_alias or "Dataset",
            source_plugin_id=plugin_id,
            source_entity_id=plan.provenance.get("entity_id", ""),
        )
        dataset.add_revision(revision)
        project.add_dataset(dataset)
        session.save()
        return OperationResult.ok(str(dataset.id))
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "import_failed"),
            message=str(exc),
        )


def _to_column_schemas(
    columns: tuple[ColumnDescriptor, ...] | tuple[ColumnSchema, ...],
) -> tuple[ColumnSchema, ...]:
    result: list[ColumnSchema] = []
    for col in columns:
        if isinstance(col, ColumnSchema):
            result.append(col)
        else:
            result.append(
                ColumnSchema(
                    name=col.name,
                    logical_type=col.logical_type,
                    nullable=col.nullable,
                )
            )
    return tuple(result)
