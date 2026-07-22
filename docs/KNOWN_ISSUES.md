# Known Issues — Prism BI 1.0.0 (GA)

| ID | Area | Description | Workaround / plan |
|----|------|-------------|-------------------|
| KI-01 | Performance | 1M-row interactive targets remain hardware-dependent; use `just bench` on reference machines. | Prefer filtered exports for multi-million-row Excel. |
| KI-02 | PDF | Dashboard/report PDF layout is constrained (simple flowing sections). | Acceptable for V1; full designer deferred to V1.1. |
| KI-03 | Excel export | XLSX export loads the selected table into memory up to the export row cap. | Filter/clean first; avoid multi-million-row Excel dumps. |
| KI-04 | Plugins | Stub / null AI plugins ship for SDK demonstrations and appear in About. | Safe to ignore; AI remains feature-flagged off. |
| KI-05 | Installer | Inno Setup compile requires a local Inno 6 install; Authenticode signing is org-operated. | Portable `dist/PrismBI/` is the primary verified artifact; see packaging README for SignTool. |
| KI-06 | Accessibility | Chart widgets still have limited screen-reader semantics beyond titles/truncation. | Keyboard focus rings and empty states landed in M5; deeper chart a11y is post-GA polish. |

Resolved before GA: background import/profile/export jobs, DuckDB memory caps, plugin trust, settings recovery, sample project, Getting Started help, version freeze to `1.0.0`.
