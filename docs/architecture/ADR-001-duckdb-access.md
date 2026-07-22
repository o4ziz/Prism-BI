# ADR-001: DuckDB Access Serialization

## Status

Accepted (Milestone 2)

## Context

Prism BI uses an embedded DuckDB warehouse per `.prism` project. DuckDB connections
are not freely shareable across threads without a clear policy. The UI, job workers,
profiling, and cleaning all need warehouse access.

## Decision

Use a **single DuckDB connection per open project**, guarded by a **`threading.RLock`**
inside `DuckDBAnalyticsStore` (serialized facade). All reads and writes go through
this facade. Physical revision tables are named `rev_<uuid_hex>` and never use
user-facing aliases.

## Consequences

- Correctness and simplicity over parallel query throughput in V1.
- Job workers and the UI share one store instance safely.
- Future parallelism requires an explicit ADR change (e.g. read-only secondary connections).
