"""Column schema value object."""

from __future__ import annotations

from dataclasses import dataclass

from prism_bi_sdk.dto.schema import LogicalType


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    """Domain column metadata; names are never hardcoded in core logic."""

    name: str
    logical_type: LogicalType
    nullable: bool = True
    override: bool = False
