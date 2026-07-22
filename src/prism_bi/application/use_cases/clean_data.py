"""Apply cleaning pipeline → new dataset revision."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.cleaning import CleaningPipeline, compile_pipeline_sql
from prism_bi.domain.entities.dataset import DatasetRevision
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi.domain.value_objects.column_schema import ColumnSchema


def apply_cleaning(
    session: WorkspaceSession,
    dataset_id: UUID,
    pipeline: CleaningPipeline,
) -> OperationResult[str]:
    try:
        project, _ = session.require_project()
        dataset = project.get_dataset(dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            return OperationResult.fail(
                error_code="dataset_missing",
                message="Dataset or revision not found",
            )
        parent_id = dataset.current_revision_id
        source = session.analytics.relation_sql(parent_id)
        sql = compile_pipeline_sql(pipeline, source)
        new_id = uuid4()
        session.analytics.create_revision_as_table(new_id, sql_select=sql)
        physical = session.analytics.columns(new_id)
        columns = tuple(
            ColumnSchema(name=c.name, logical_type=c.logical_type, nullable=c.nullable)
            for c in physical
        )
        revision = DatasetRevision(
            id=new_id,
            parent_id=parent_id,
            created_at=datetime.now(UTC),
            label="clean",
            columns=columns,
        )
        dataset.add_revision(revision)
        project.pipelines[str(dataset_id)] = pipeline.to_list()
        session.profile_cache.pop(str(parent_id), None)
        session.save()
        return OperationResult.ok(str(new_id))
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "clean_failed"),
            message=str(exc),
        )
