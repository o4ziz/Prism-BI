"""Analytics-backed chart data provider (no Qt, no DuckDB imports in callers)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pyarrow as pa

from prism_bi.application.ports.analytics import IAnalyticsStore
from prism_bi.domain.entities.project import Project
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData
from prism_bi_sdk.dto.schema import ColumnDescriptor

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_AGGS = {
    "sum": "SUM",
    "avg": "AVG",
    "mean": "AVG",
    "count": "COUNT",
    "min": "MIN",
    "max": "MAX",
}


def _q(name: str) -> str:
    if not _IDENT.match(name):
        raise ValidationError(f"Invalid field name: {name}", code="invalid_field")
    return '"' + name.replace('"', '""') + '"'


class AnalyticsChartDataProvider:
    """Builds aggregate SQL via ``IAnalyticsStore`` for chart specs."""

    def __init__(
        self,
        store: IAnalyticsStore,
        *,
        project_provider: Callable[[], Project | None],
        max_points: int = 10_000,
        max_categories: int = 500,
    ) -> None:
        self._store = store
        self._project_provider = project_provider
        self._max_points = max_points
        self._max_categories = max_categories

    def list_fields(self, dataset_id: UUID) -> tuple[ColumnDescriptor, ...]:
        project = self._require_project()
        dataset = project.get_dataset(dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            raise DomainError("Dataset revision not found", code="dataset_missing")
        return self._store.columns(dataset.current_revision_id)

    def query(self, spec: ChartSpec) -> ChartData:
        project = self._require_project()
        dataset = project.get_dataset(spec.dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            raise DomainError("Dataset revision not found", code="dataset_missing")
        revision_id = dataset.current_revision_id
        relation = self._store.relation_sql(revision_id)
        where = _filter_clause(spec.options)

        if spec.chart_type == "table":
            return self._table_preview(relation, where)
        if spec.chart_type == "histogram":
            return self._histogram(relation, _encoding(spec, "x") or _encoding(spec, "y"), where)
        if spec.chart_type == "scatter":
            return self._scatter(relation, _encoding(spec, "x"), _encoding(spec, "y"), where)
        # bar / line / area / pie — category x + aggregated y
        return self._categorical_agg(
            relation,
            _encoding(spec, "x"),
            _encoding(spec, "y"),
            _encoding(spec, "series"),
            where,
        )

    def _require_project(self) -> Project:
        project = self._project_provider()
        if project is None:
            raise DomainError("No project open", code="no_project")
        return project

    def _table_preview(self, relation: str, where: str) -> ChartData:
        sql = f"SELECT * FROM {relation}{where} LIMIT {self._max_points}"
        table = self._store.execute_arrow(sql)
        cols = tuple(table.schema.names)
        return ChartData(
            batch=_table_to_batch(table),
            category_column=None,
            value_columns=cols,
            truncated=table.num_rows >= self._max_points,
        )

    def _histogram(
        self,
        relation: str,
        enc: ChartEncoding | None,
        where: str,
        *,
        bins: int = 20,
    ) -> ChartData:
        if enc is None:
            raise ValidationError("histogram requires an x field", code="chart_encoding")
        if bins < 1:
            raise ValidationError("histogram bins must be >= 1", code="chart_histogram")
        field = _q(enc.field)
        # DuckDB has no width_bucket; bin with FLOOR over [lo, hi].
        sql = f"""
            WITH bounds AS (
              SELECT
                MIN(TRY_CAST({field} AS DOUBLE)) AS lo,
                MAX(TRY_CAST({field} AS DOUBLE)) AS hi
              FROM {relation}
              {where}
            ),
            vals AS (
              SELECT TRY_CAST({field} AS DOUBLE) AS v, bounds.lo, bounds.hi
              FROM {relation}, bounds
              WHERE TRY_CAST({field} AS DOUBLE) IS NOT NULL
                AND bounds.lo IS NOT NULL
                AND bounds.hi IS NOT NULL
                {_and_extra(where)}
            ),
            binned AS (
              SELECT
                CASE
                  WHEN lo = hi THEN 1
                  ELSE LEAST(
                    {bins},
                    GREATEST(
                      1,
                      CAST(FLOOR((v - lo) / ((hi - lo) / {bins}.0)) AS INTEGER) + 1
                    )
                  )
                END AS bin_id
              FROM vals
            )
            SELECT CAST(bin_id AS VARCHAR) AS category, COUNT(*) AS value
            FROM binned
            GROUP BY 1
            ORDER BY 1
            LIMIT {self._max_categories}
        """
        table = self._store.execute_arrow(sql)
        if table.num_rows == 0:
            raise ValidationError(
                f"Histogram needs numeric values in '{enc.field}'. "
                "For categories (e.g. City), use a bar chart instead.",
                code="chart_histogram",
            )
        truncated = table.num_rows >= self._max_categories
        return ChartData(
            batch=_table_to_batch(table),
            category_column="category",
            value_columns=("value",),
            truncated=truncated,
        )

    def _scatter(
        self,
        relation: str,
        x_enc: ChartEncoding | None,
        y_enc: ChartEncoding | None,
        where: str,
    ) -> ChartData:
        if x_enc is None or y_enc is None:
            raise ValidationError("scatter requires x and y", code="chart_encoding")
        x = _q(x_enc.field)
        y = _q(y_enc.field)
        extra = f"TRY_CAST({x} AS DOUBLE) IS NOT NULL AND TRY_CAST({y} AS DOUBLE) IS NOT NULL"
        if where:
            sql = f"""
                SELECT TRY_CAST({x} AS DOUBLE) AS x, TRY_CAST({y} AS DOUBLE) AS y
                FROM {relation}
                {where} AND {extra}
                LIMIT {self._max_points}
            """
        else:
            sql = f"""
                SELECT TRY_CAST({x} AS DOUBLE) AS x, TRY_CAST({y} AS DOUBLE) AS y
                FROM {relation}
                WHERE {extra}
                LIMIT {self._max_points}
            """
        table = self._store.execute_arrow(sql)
        return ChartData(
            batch=_table_to_batch(table),
            category_column=None,
            value_columns=("x", "y"),
            truncated=table.num_rows >= self._max_points,
        )

    def _categorical_agg(
        self,
        relation: str,
        x_enc: ChartEncoding | None,
        y_enc: ChartEncoding | None,
        series_enc: ChartEncoding | None,
        where: str,
    ) -> ChartData:
        if x_enc is None:
            raise ValidationError("chart requires an x (category) field", code="chart_encoding")
        cat = _q(x_enc.field)
        if y_enc is None:
            agg_expr = "COUNT(*)"
            value_name = "value"
        else:
            agg = (y_enc.aggregation or "sum").lower()
            fn = _AGGS.get(agg, "SUM")
            if fn == "COUNT":
                agg_expr = f"COUNT({_q(y_enc.field)})"
            else:
                agg_expr = f"{fn}(TRY_CAST({_q(y_enc.field)} AS DOUBLE))"
            value_name = "value"

        if series_enc is not None:
            series = _q(series_enc.field)
            sql = f"""
                SELECT CAST({cat} AS VARCHAR) AS category,
                       CAST({series} AS VARCHAR) AS series,
                       {agg_expr} AS {value_name}
                FROM {relation}
                {where}
                GROUP BY 1, 2
                ORDER BY 1, 2
                LIMIT {self._max_points}
            """
            table = self._store.execute_arrow(sql)
            return ChartData(
                batch=_table_to_batch(table),
                category_column="category",
                value_columns=(value_name,),
                truncated=table.num_rows >= self._max_points,
            )

        sql = f"""
            SELECT CAST({cat} AS VARCHAR) AS category, {agg_expr} AS {value_name}
            FROM {relation}
            {where}
            GROUP BY 1
            ORDER BY 1
            LIMIT {self._max_categories}
        """
        table = self._store.execute_arrow(sql)
        return ChartData(
            batch=_table_to_batch(table),
            category_column="category",
            value_columns=(value_name,),
            truncated=table.num_rows >= self._max_categories,
        )


def _encoding(spec: ChartSpec, role: str) -> ChartEncoding | None:
    for enc in spec.encodings:
        if enc.role == role:
            return enc
    return None


def _filter_clause(options: dict[str, Any]) -> str:
    """Build optional WHERE from ChartSpec.options['filters']."""
    raw = options.get("filters")
    if not raw:
        return ""
    if not isinstance(raw, list):
        raise ValidationError("filters must be a list", code="chart_filter")
    parts: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", ""))
        op = str(item.get("op", "eq")).lower()
        value = item.get("value")
        col = _q(field)
        if op == "eq":
            parts.append(f"CAST({col} AS VARCHAR) = {_sql_literal(value)}")
        elif op == "neq":
            parts.append(f"CAST({col} AS VARCHAR) <> {_sql_literal(value)}")
        elif op == "contains":
            parts.append(f"CAST({col} AS VARCHAR) LIKE {_sql_literal('%' + str(value) + '%')}")
        else:
            raise ValidationError(f"Unsupported filter op: {op}", code="chart_filter")
    if not parts:
        return ""
    return " WHERE " + " AND ".join(parts)


def _and_extra(where: str) -> str:
    if not where:
        return ""
    # where is " WHERE ..." — strip WHERE for AND chaining
    return " AND " + where.removeprefix(" WHERE ")


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _table_to_batch(table: pa.Table) -> pa.RecordBatch:
    if table.num_rows == 0:
        return pa.RecordBatch.from_arrays(
            [pa.array([], type=field.type) for field in table.schema],
            schema=table.schema,
        )
    return table.to_batches()[0]
