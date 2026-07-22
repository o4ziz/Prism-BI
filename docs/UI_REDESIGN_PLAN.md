# Prism BI UI Redesign Plan (presentation only)

## Critique (from live capture)

| Issue | Detail |
|-------|--------|
| Outdated | Text-only sidebar, prototype QSS, no icons |
| Unfinished | Home was instructions-only; Logs dock not a real viewer |
| Wasted space | Tall empty Task Center/Logs; empty Home canvas |
| Usability | Menu-heavy; no quick actions; docks always visible |
| Not commercial | Default Qt look; no design system |

## Design identity

- Accent teal `#0D9488` (Prism refraction — not purple)
- Slate neutrals; Segoe UI; Fluent-inspired controls
- Patterns: JetBrains tool windows, Notion cards, Power BI density, Azure Data Studio spacing

## Delivered

- Light + dark themes (`app.qss` / `app_dark.qss`)
- Collapsible SVG icon nav rail (Home…Help)
- Home card dashboard (recent, create/open, sample, plugins, shortcuts)
- Professional toolbar + status project chip
- Docks start hidden (show via Jobs → Task Center)
- Page headers on Data / Prepare / Visualize / Dashboard / Reports
- Settings (theme + paths) and Help modules
- Empty-state panel helper with CTAs

## Constraints honored

No changes to use cases, plugins, domain, infrastructure adapters, or architecture layers.
