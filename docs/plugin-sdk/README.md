# Prism BI Plugin SDK

Stable public contracts for first-party and third-party plugins.

**Host / SDK version (GA):** `1.0.0` · **API major:** `prism_bi_sdk.API_VERSION_MAJOR`

## Rules

- Depend only on `prism_bi_sdk` (and optional PySide6 for UI contributions).
- Never import `prism_bi.infrastructure`, `prism_bi.application`, or `prism_bi.bootstrap`.
- Match `api_version` to the SDK major (`prism_bi_sdk.API_VERSION_MAJOR`).
- Datasource plugins return `MaterializePlan`; the **application** writes the warehouse.
- Chart plugins receive aggregated `ChartData` — never query DuckDB.
- Exporter plugins serialize `ExportArtifact` only — never query DuckDB or datasources.

## Packages

| Module | Contents |
|--------|----------|
| `plugin` | `IPlugin`, `PluginManifest` |
| `context` | `PluginContext` |
| `contributions` | Contribution kinds + registry protocol |
| `datasources` | `IDataSourcePlugin`, `IQueryableSource`, capabilities |
| `charts` | `IChartPlugin` |
| `exporters` | `IExporterPlugin` |
| `cleaning` / `ai` / `auth` / `license` / `themes` | Extension protocols (AI/auth reserved) |
| `dto` | Schema, preview, materialize, chart, export, report, job DTOs |

## First-party examples

See repository `plugins/`:

- Datasources: `prism_datasource_csv`, `_excel`, `_json`, `_sqlite` (+ stub)
- Charts: `prism_chart_qtcharts`
- Exporters: `prism_exporter_tabular`, `_image`, `_pdf`
- AI placeholder: `prism_ai_null` (feature-flagged off in V1)
