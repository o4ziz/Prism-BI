# Milestone 5 Completion Report — Performance & Hardening

**Date:** 2026-07-22  
**Status:** Complete — awaiting approval before Milestone 6 (GA)  
**Version baseline:** 1.0.0rc1 + M5 hardening (no new product features)

## Summary of implemented work

### Blueprint phases

| Phase | Work | Status |
|-------|------|--------|
| 5.1 Benchmark harness | `benchmarks/run_bench.py`, `just bench` | Done |
| 5.2 Import streaming & DuckDB tuning | Jobs for import/profile/export; DuckDB `memory_limit` (~60% of budget) + threads=2 | Done |
| 5.3 Chart aggregation caps | Existing caps retained; truncation banner + a11y text | Done |
| 5.4 Startup + lazy activate | `defer_plugin_activation` + `activate_pending()` after QApplication | Done |
| 5.5 Memory/leak pass | Job retention cap (50); profile cache LRU (32); DuckDB budget | Done |
| 5.6 Security pass | Path helpers; user-plugin trust; secret log redaction; checklist signed | Done |

### Cross-cutting polish

- Task Center: progress %, cancel selected job
- Data workspace: empty states, background jobs, path validation
- Stylesheet: focus rings, empty-state typography
- Config: corrupt `settings.toml` → `.bak` + recovery flag + toast
- Known issues / CHANGELOG updated

## Quality gates

| Check | Result |
|-------|--------|
| Ruff | Pass |
| MyPy | Pass |
| Pytest | Pass (**50**) |
| Import-linter | Pass (3 contracts; ADRs respected) |

## Performance observations

10k-row bench (this machine):

| Step | Seconds |
|------|---------|
| create_project | ~0.01 |
| import | ~0.05 |
| profile | ~0.01 |
| chart_query | &lt;0.01 |
| grid_window | &lt;0.01 |
| import+profile | ~0.06 (≪ 5s NFR-01 target) |

100k-row bench (this machine, re-runnable harness):

| Step | Seconds |
|------|---------|
| create_project | ~0.01 |
| import | ~0.08 |
| profile | ~0.02 |
| chart_query | ~0.001 |
| grid_window | ~0.001 |
| import+profile | ~0.10 (≪ 5s NFR-01 target) |

Interactive grid remains windowed (`grid_window_rows`); charts stay aggregated with caps. Harness uses a unique `.prism` root per run so re-runs do not collide.

## Architecture verification

| ADR | Still respected? |
|-----|------------------|
| ADR-001 DuckDB serialized access | Yes — single connection + RLock; memory_limit is SET on that connection |
| ADR-002 Visualization abstraction | Yes — no DuckDB in chart plugins/UI |
| ADR-003 Export contract | Yes — exporters still serialize `ExportArtifact` only |

Application layer does not import infrastructure (path helpers live in `domain/paths.py`).

## Production readiness checklist

- [x] Long-running import/profile/export report progress and can be cancelled
- [x] Plugin failures soft-fail; user plugins require trust list
- [x] Corrupt settings do not brick startup
- [x] Logging includes job ids; secret-like fields redacted in plugin context logs
- [x] Large datasets: windowed grid + chart caps + DuckDB memory budget
- [x] Security checklist signed (`docs/architecture/security-checklist-m5.md`)
- [x] RC portable packaging still valid (M6 adds signing)
- [ ] Code-signed GA installer (Milestone 6)
- [ ] Sample projects / deep help (Milestone 6)

## Intentionally deferred (future versions / M6)

- AI, authentication, cloud sync, collaboration
- Full report designer (V1.1)
- Live DB connectors
- Code signing & GA sample projects (Milestone 6)
- Process sandboxing for plugins (accepted V1 risk)

## How to verify locally

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
just check
just bench
uv run prism-bi
```
