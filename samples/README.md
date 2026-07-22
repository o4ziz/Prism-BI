# Sample projects

## Sales Demo

Path: [`SalesDemo.prism`](SalesDemo.prism)

A small retail-style dataset (10 rows) with a pre-built bar chart
(**Revenue by region**) so Visualize is non-empty on first open.

### Open in the app

1. Launch Prism BI.
2. **File → Open Project…**
3. Select the `SalesDemo.prism` folder (not a zip — `.prism` is a directory package).

### Rebuild

If the sample is missing or you need to regenerate after schema changes:

```powershell
uv run python scripts/build_sample_project.py
```

Source CSV: [`data/sales_demo.csv`](data/sales_demo.csv).
