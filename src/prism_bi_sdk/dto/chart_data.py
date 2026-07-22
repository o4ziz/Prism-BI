"""Chart data result — engine-agnostic aggregated series for renderers."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa


@dataclass(frozen=True, slots=True)
class ChartData:
    """Pre-aggregated tabular result for a chart renderer.

    Produced by ``IChartDataProvider`` (application). Chart engines must not
    query warehouses or datasources directly.
    """

    batch: pa.RecordBatch
    category_column: str | None = None
    value_columns: tuple[str, ...] = ()
    truncated: bool = False
