"""Cleaning pipeline domain model and DuckDB SQL compiler."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from prism_bi.domain.errors import ValidationError

_IDENT = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class CleaningStep:
    """One serializable cleaning operation."""

    op: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.op, "params": dict(self.params)}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CleaningStep:
        return CleaningStep(op=str(data["op"]), params=dict(data.get("params") or {}))


@dataclass
class CleaningPipeline:
    """Ordered, replayable cleaning steps."""

    steps: list[CleaningStep] = field(default_factory=list)

    def add(self, step: CleaningStep) -> None:
        self.steps.append(step)

    def to_json(self) -> str:
        return json.dumps([step.to_dict() for step in self.steps])

    @staticmethod
    def from_json(raw: str) -> CleaningPipeline:
        data = json.loads(raw)
        return CleaningPipeline(steps=[CleaningStep.from_dict(item) for item in data])

    def to_list(self) -> list[dict[str, Any]]:
        return [step.to_dict() for step in self.steps]


def _q(name: str) -> str:
    if not _IDENT.match(name):
        raise ValidationError(f"Invalid identifier: {name}", code="invalid_ident")
    return '"' + name.replace('"', '""') + '"'


def compile_pipeline_sql(pipeline: CleaningPipeline, source_relation: str) -> str:
    """Compile built-in cleaning ops to a DuckDB SELECT over ``source_relation``.

    ``source_relation`` must already be a safe quoted relation from the store.
    """
    current = f"SELECT * FROM {source_relation}"
    for step in pipeline.steps:
        current = f"SELECT * FROM ({_compile_step(step, current)}) AS _prism_step"
    return current


def _compile_step(step: CleaningStep, source_sql: str) -> str:
    op = step.op
    params = step.params
    src = f"({source_sql})"

    if op == "drop_columns":
        cols = params.get("columns") or []
        if not cols:
            return f"SELECT * FROM {src} AS s"
        excluded = {str(c) for c in cols}
        # SELECT * EXCEPT — DuckDB supports EXCEPT
        except_list = ", ".join(_q(c) for c in excluded)
        return f"SELECT * EXCLUDE ({except_list}) FROM {src} AS s"

    if op == "rename_column":
        old = str(params["from"])
        new = str(params["to"])
        return f"SELECT * EXCLUDE ({_q(old)}), {_q(old)} AS {_q(new)} FROM {src} AS s"

    if op == "cast_column":
        col = str(params["column"])
        duck_type = str(params["duck_type"])
        allowed = {
            "BIGINT",
            "DOUBLE",
            "BOOLEAN",
            "VARCHAR",
            "TIMESTAMP",
            "DATE",
        }
        if duck_type.upper() not in allowed:
            raise ValidationError(f"Unsupported cast type: {duck_type}", code="bad_cast")
        return (
            f"SELECT * EXCLUDE ({_q(col)}), "
            f"CAST({_q(col)} AS {duck_type.upper()}) AS {_q(col)} FROM {src} AS s"
        )

    if op == "fill_null":
        col = str(params["column"])
        value = params.get("value")
        literal = _sql_literal(value)
        return (
            f"SELECT * EXCLUDE ({_q(col)}), "
            f"COALESCE({_q(col)}, {literal}) AS {_q(col)} FROM {src} AS s"
        )

    if op == "drop_nulls":
        cols = [str(c) for c in (params.get("columns") or [])]
        if not cols:
            raise ValidationError("drop_nulls requires columns", code="drop_nulls_cols")
        predicates = " AND ".join(f"{_q(c)} IS NOT NULL" for c in cols)
        return f"SELECT * FROM {src} AS s WHERE {predicates}"

    if op == "trim_column":
        col = str(params["column"])
        return (
            f"SELECT * EXCLUDE ({_q(col)}), "
            f"TRIM(CAST({_q(col)} AS VARCHAR)) AS {_q(col)} FROM {src} AS s"
        )

    if op == "replace_values":
        col = str(params["column"])
        old = _sql_literal(params.get("old"))
        new = _sql_literal(params.get("new"))
        return (
            f"SELECT * EXCLUDE ({_q(col)}), "
            f"CASE WHEN {_q(col)} = {old} THEN {new} ELSE {_q(col)} END AS {_q(col)} "
            f"FROM {src} AS s"
        )

    if op == "dedupe":
        cols = [str(c) for c in (params.get("columns") or [])]
        if cols:
            partition = ", ".join(_q(c) for c in cols)
            return (
                f"SELECT * EXCLUDE (_prism_rn) FROM ("
                f"SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition}) AS _prism_rn "
                f"FROM {src} AS s) t WHERE _prism_rn = 1"
            )
        return (
            f"SELECT * EXCLUDE (_prism_rn) FROM ("
            f"SELECT *, ROW_NUMBER() OVER () AS _prism_rn FROM {src} AS s) t "
            f"WHERE _prism_rn = 1"
        )

    if op == "filter_rows":
        # Restricted: column op value with allowlisted operators
        col = str(params["column"])
        operator = str(params.get("operator", "="))
        allowed_ops = {"=", "!=", ">", ">=", "<", "<=", "LIKE"}
        if operator not in allowed_ops:
            raise ValidationError(f"Invalid filter operator: {operator}", code="bad_filter")
        value = _sql_literal(params.get("value"))
        return f"SELECT * FROM {src} AS s WHERE {_q(col)} {operator} {value}"

    raise ValidationError(f"Unknown cleaning op: {op}", code="unknown_clean_op")


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"
