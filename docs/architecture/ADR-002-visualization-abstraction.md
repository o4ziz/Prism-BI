# ADR-002: Visualization Abstraction (Data Provider + Chart Engines)

## Status

Accepted (Milestone 3)

## Context

Charts and dashboards must remain schema-agnostic and engine-replaceable. Embedding
DuckDB or datasource plugins inside chart widgets would couple the UI to one warehouse
and one chart library, blocking future engines (web, pyqtgraph, etc.).

## Decision

1. **Viz-as-data:** Persist `ChartSpec` / `DashboardSpec` (SDK DTOs) on the project.
2. **`IChartDataProvider`:** Application port that turns a `ChartSpec` into aggregated
   `ChartData` (Arrow). The host implementation uses `IAnalyticsStore` only; callers
   never import DuckDB.
3. **`IChartPlugin`:** SDK contract for chart engines. Plugins receive
   `(ChartSpec, ChartData)` and return an opaque view widget. They must not query
   warehouses or datasources.
4. **`ChartRendererRegistry`:** Resolves `chart_type` → plugin via
   `ContributionKind.CHARTS`, so engines can be swapped without changing application
   or presentation logic.
5. **`ChartHostWidget`:** Modular presentation binder used by Visualize and Dashboard.

Aggregation and point caps (`chart_max_points`) happen in the provider, not in the UI.

## Consequences

- QtCharts is one plugin (`prism.chart.qtcharts`), not a core dependency of domain/application.
- PNG export is an optional plugin capability (`export_image`) ready for Milestone 4 exporters.
- Dashboard filter linkage mutates `ChartSpec.options["filters"]` before querying the provider.
