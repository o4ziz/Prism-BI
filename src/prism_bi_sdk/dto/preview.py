"""Preview interchange (Arrow-backed)."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from prism_bi_sdk.dto.schema import ColumnDescriptor


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Capped preview for import wizards and live query samples."""

    columns: tuple[ColumnDescriptor, ...]
    batch: pa.RecordBatch
    row_count_estimate: int | None = None
