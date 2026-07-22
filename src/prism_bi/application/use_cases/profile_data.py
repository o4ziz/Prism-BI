"""Profiling use case — computes ProfileReport via analytics store SQL."""

from __future__ import annotations

from uuid import UUID

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.errors import DomainError
from prism_bi.domain.profiling import ColumnProfile, ProfileReport
from prism_bi.domain.value_objects.column_schema import ColumnSchema
from prism_bi_sdk.dto.schema import LogicalType

SAMPLE_THRESHOLD = 500_000


def profile_revision(
    session: WorkspaceSession,
    dataset_id: UUID,
    *,
    force_full: bool = False,
) -> OperationResult[ProfileReport]:
    try:
        project, _ = session.require_project()
        dataset = project.get_dataset(dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            return OperationResult.fail(
                error_code="dataset_missing",
                message="Dataset or revision not found",
            )
        revision_id = dataset.current_revision_id
        cache_key = str(revision_id)
        if cache_key in session.profile_cache and not force_full:
            return OperationResult.ok(session.profile_cache[cache_key])

        store = session.analytics
        relation = store.relation_sql(revision_id)
        row_count = store.row_count(revision_id)
        sampled = row_count > SAMPLE_THRESHOLD and not force_full
        sample_clause = f"(SELECT * FROM {relation} USING SAMPLE 100000)" if sampled else relation

        columns = store.columns(revision_id)
        col_profiles: list[ColumnProfile] = []
        for col in columns:
            name = col.name
            q = '"' + name.replace('"', '""') + '"'
            stats_sql = f"""
                SELECT
                  COUNT(*) FILTER (WHERE {q} IS NULL) AS nulls,
                  COUNT(DISTINCT {q}) AS distincts,
                  CAST(MIN({q}) AS VARCHAR) AS min_v,
                  CAST(MAX({q}) AS VARCHAR) AS max_v
                FROM {sample_clause} AS s
            """
            table = store.execute_arrow(stats_sql)
            nulls = int(table.column("nulls")[0].as_py() or 0)
            distincts = int(table.column("distincts")[0].as_py() or 0)
            min_v = table.column("min_v")[0].as_py()
            max_v = table.column("max_v")[0].as_py()
            denom = max(row_count if not sampled else 100_000, 1)
            null_ratio = nulls / float(denom)
            is_key = (
                distincts == (row_count if not sampled else distincts)
                and nulls == 0
                and distincts > 0
            )

            outlier_count = 0
            if col.logical_type in {LogicalType.INTEGER, LogicalType.FLOAT}:
                outlier_sql = f"""
                    WITH stats AS (
                      SELECT
                        AVG(TRY_CAST({q} AS DOUBLE)) AS mu,
                        STDDEV_SAMP(TRY_CAST({q} AS DOUBLE)) AS sigma
                      FROM {sample_clause} AS s
                    )
                    SELECT COUNT(*) AS outliers
                    FROM {sample_clause} AS s, stats
                    WHERE stats.sigma IS NOT NULL AND stats.sigma > 0
                      AND ABS(TRY_CAST({q} AS DOUBLE) - stats.mu) > 3 * stats.sigma
                """
                out_table = store.execute_arrow(outlier_sql)
                outlier_count = int(out_table.column("outliers")[0].as_py() or 0)

            samples_sql = f"""
                SELECT CAST({q} AS VARCHAR) AS v
                FROM {sample_clause} AS s
                WHERE {q} IS NOT NULL
                LIMIT 5
            """
            sample_table = store.execute_arrow(samples_sql)
            samples = tuple(
                str(sample_table.column("v")[i].as_py()) for i in range(sample_table.num_rows)
            )

            # Respect user overrides from revision schema
            logical = col.logical_type
            for schema_col in _revision_columns(dataset, revision_id):
                if schema_col.name == name and schema_col.override:
                    logical = schema_col.logical_type
                    break

            col_profiles.append(
                ColumnProfile(
                    name=name,
                    logical_type=logical,
                    null_count=nulls,
                    null_ratio=null_ratio,
                    distinct_count=distincts,
                    is_candidate_key=bool(is_key and distincts == row_count),
                    min_value=None if min_v is None else str(min_v),
                    max_value=None if max_v is None else str(max_v),
                    outlier_count=outlier_count,
                    sample_values=samples,
                )
            )

        # Duplicate heuristic via row hashes
        dup_count = 0
        try:
            hash_sql = f"""
                SELECT COUNT(*) - COUNT(DISTINCT hash(COLUMNS(*))) AS dups
                FROM {sample_clause} AS s
            """
            dup_table = store.execute_arrow(hash_sql)
            dup_count = int(dup_table.column("dups")[0].as_py() or 0)
        except Exception:  # noqa: BLE001
            dup_count = 0

        # Relationship hints: shared column names across datasets
        hints: list[dict[str, object]] = []
        names = {c.name.lower() for c in columns}
        for other in project.datasets:
            if other.id == dataset_id or other.current_revision_id is None:
                continue
            other_cols = {c.name.lower() for c in store.columns(other.current_revision_id)}
            shared = sorted(names & other_cols)
            if shared:
                hints.append(
                    {
                        "left_dataset_id": str(dataset_id),
                        "right_dataset_id": str(other.id),
                        "shared_columns": shared,
                    }
                )

        report = ProfileReport(
            revision_id=revision_id,
            row_count=row_count,
            duplicate_row_count=max(dup_count, 0),
            columns=tuple(col_profiles),
            relationship_hints=tuple(hints),
            sampled=sampled,
        )
        session.cache_profile(cache_key, report)
        project.profiles[cache_key] = report.to_dict()
        session.save()
        return OperationResult.ok(report)
    except (DomainError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "profile_failed"),
            message=str(exc),
        )


def _revision_columns(dataset: object, revision_id: UUID) -> tuple[ColumnSchema, ...]:
    for rev in getattr(dataset, "revisions", []):
        if rev.id == revision_id:
            return tuple(rev.columns)
    return ()
