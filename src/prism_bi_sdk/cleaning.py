"""Optional custom cleaning step plugin contract."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class ICleaningStepPlugin(IPlugin, Protocol):
    """Extends the cleaning pipeline with a custom step type."""

    @property
    def step_type(self) -> str:
        """Stable step type id used in serialized pipelines."""

    def validate_params(self, params: dict[str, Any]) -> None:
        """Raise ``ValueError`` if params are invalid."""

    def to_sql_fragment(self, params: dict[str, Any], source_relation: str) -> str:
        """Compile this step to a DuckDB SQL fragment (executed by the host)."""
