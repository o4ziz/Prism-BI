# Milestone 5 — Security checklist (signed for V1 gate)

Date: 2026-07-22  
Build: Prism BI 1.0.0 (GA) — Milestone 5 security controls retained  
Reviewer: Engineering (automated checklist)

| # | Control | Status | Notes |
|---|---------|--------|-------|
| 1 | Path canonicalization on import/export | Pass | `prism_bi.domain.paths` |
| 2 | Path traversal rejection helper | Pass | `ensure_within` available for rooted ops |
| 3 | `.prism` is directory package (no zip-slip) | Pass | Documented; no zip open path |
| 4 | Plugin soft-fail | Pass | `continue_on_error` default true |
| 5 | User-folder plugin trust gate | Pass | Requires `plugins.trusted_ids` in settings.toml |
| 6 | Secrets via OS keyring | Pass | Never written to project.json |
| 7 | Secret-like keys redacted in plugin logs | Pass | HostPluginContext.log |
| 8 | Excel values-only import | Pass | python-calamine |
| 9 | DuckDB memory_limit applied | Pass | ~60% of `memory_budget_mb` |
| 10 | Temp/export parent creation validated | Pass | `validate_export_destination` |
| 11 | No plaintext secrets in logs by default | Pass | Structured logging without secret dumps |
| 12 | Accepted plugins run as user (no sandbox) | Accepted risk | Documented for V1 |

**Sign-off:** Milestone 5 security pass complete for V1 gate. GA signing remains Milestone 6.
