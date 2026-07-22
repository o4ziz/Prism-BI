"""Profiling domain models and pure helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from prism_bi_sdk.dto.schema import LogicalType


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Per-column profiling metrics."""

    name: str
    logical_type: LogicalType
    null_count: int
    null_ratio: float
    distinct_count: int
    is_candidate_key: bool
    min_value: str | None = None
    max_value: str | None = None
    outlier_count: int = 0
    sample_values: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileReport:
    """Cached profile for a dataset revision."""

    revision_id: UUID
    row_count: int
    duplicate_row_count: int
    columns: tuple[ColumnProfile, ...]
    relationship_hints: tuple[dict[str, Any], ...] = ()
    sampled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": str(self.revision_id),
            "row_count": self.row_count,
            "duplicate_row_count": self.duplicate_row_count,
            "sampled": self.sampled,
            "columns": [
                {
                    "name": col.name,
                    "logical_type": col.logical_type.value,
                    "null_count": col.null_count,
                    "null_ratio": col.null_ratio,
                    "distinct_count": col.distinct_count,
                    "is_candidate_key": col.is_candidate_key,
                    "min_value": col.min_value,
                    "max_value": col.max_value,
                    "outlier_count": col.outlier_count,
                    "sample_values": list(col.sample_values),
                }
                for col in self.columns
            ],
            "relationship_hints": list(self.relationship_hints),
        }


def infer_logical_type_from_name_and_samples(
    name: str,
    samples: list[str],
) -> LogicalType:
    """Heuristic type inference from string samples (used when Arrow type is weak)."""
    lowered = name.lower()
    if any(token in lowered for token in ("date", "time", "timestamp")):
        return LogicalType.DATETIME
    if not samples:
        return LogicalType.UNKNOWN
    boolish = {"true", "false", "0", "1", "yes", "no"}
    if all(s.lower() in boolish for s in samples if s != ""):
        return LogicalType.BOOLEAN
    try:
        for sample in samples:
            if sample == "":
                continue
            int(sample)
        return LogicalType.INTEGER
    except ValueError:
        pass
    try:
        for sample in samples:
            if sample == "":
                continue
            float(sample)
        return LogicalType.FLOAT
    except ValueError:
        pass
    distinct = {s for s in samples if s != ""}
    if 0 < len(distinct) <= max(10, len(samples) // 5):
        return LogicalType.CATEGORICAL
    return LogicalType.TEXT
