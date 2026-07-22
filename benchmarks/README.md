# Benchmarks

Prism BI includes a lightweight NFR harness used for Milestone 5 / GA validation.

## Run

```powershell
# Default: 100,000 rows
just bench

# Custom size
uv run python benchmarks/run_bench.py --rows 10000 --work-dir benchmarks/out
```

## What it measures

| Step | Meaning |
|------|---------|
| `create_project_s` | Create a fresh `.prism` workspace |
| `import_s` | CSV discover + materialize into DuckDB |
| `profile_s` | Profile current dataset revision |
| `chart_query_s` | Aggregated chart query via `IChartDataProvider` |
| `grid_window_s` | Windowed grid fetch (interactive path) |

`import_plus_profile_s` is compared against the aspirational NFR-01 target of ≤5s
for 100k rows on reference hardware (documented; soft threshold — does not fail CI).

## Notes

- Each run uses a unique project root under `--work-dir` so re-runs are safe.
- Interactive UI remains responsive via windowed grids + chart aggregation caps
  (see Milestone 5 hardening).
