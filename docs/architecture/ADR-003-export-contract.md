# ADR-003: Export Contract & Template Reports

## Status

Accepted (Milestone 4)

## Context

V1 must export CSV/XLSX/JSON/PNG/PDF and support lightweight reports without a full
report designer. Formats must be replaceable without changing application or UI logic.
Reports must not query DuckDB or datasources directly.

## Decision

1. **`ExportArtifact`** — single SDK payload (`tabular` | `image` | `document`) built by
   the application via `IAnalyticsStore` / `IChartDataProvider` / `IChartImageRenderer`.
2. **`IExporterPlugin`** — all formats implement `format_ids()`, `supports()`, and
   `export(artifact, destination, format_id=…)`. Host resolves via `ExporterRegistry`
   and `ContributionKind.EXPORTERS`.
3. **`ReportTemplate`** — template-based reporting (heading/notes/chart/dataset sections).
   Materialization reuses the visualization abstraction; full designer deferred to V1.1.
4. Concrete engines live in plugins: `prism_exporter_tabular`, `prism_exporter_image`,
   `prism_exporter_pdf` (Qt print/PDF pipeline).

## Consequences

- Adding a format is a new plugin (or new `format_ids` entry) — no core app edits.
- Exporters never import DuckDB or datasource plugins.
- PNG for charts is produced through `IChartImageRenderer` + chart plugins, then handed
  to the image exporter as bytes.
