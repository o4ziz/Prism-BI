"""Benchmark harness for Milestone 5 (100k / interactive path)."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from uuid import uuid4

from prism_bi.application.use_cases.import_data import import_materialize
from prism_bi.application.use_cases.profile_data import profile_revision
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.bootstrap.container import build_container
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec


def _write_csv(path: Path, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "region", "amount"])
        regions = ["N", "S", "E", "W"]
        for i in range(rows):
            writer.writerow([i, regions[i % 4], (i % 100) + 0.5])


def run_benchmark(*, rows: int, work_dir: Path) -> dict[str, float]:
    work_dir.mkdir(parents=True, exist_ok=True)
    csv_path = work_dir / f"bench_{rows}.csv"
    _write_csv(csv_path, rows)
    # Unique project root so re-runs do not collide with a prior bench.prism.
    project_root = work_dir / f"bench_{rows}_{uuid4().hex[:8]}.prism"

    container = build_container(
        user_data_dir=work_dir / "userdata",
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[1],
        defer_plugin_activation=False,
    )
    timings: dict[str, float] = {}
    try:
        t0 = time.perf_counter()
        created = create_project(container.workspace, project_root, "Bench")
        assert created.success, created.message
        timings["create_project_s"] = time.perf_counter() - t0

        plugin = None
        for reg in container.plugins.registry.list_by_kind(ContributionKind.DATA_SOURCES):
            if ".csv" in [str(e).lower() for e in (reg.metadata or {}).get("extensions", [])]:
                plugin = reg.factory
                break
        assert plugin is not None

        t0 = time.perf_counter()
        entities = plugin.discover(str(csv_path))
        plan = plugin.materialize(entities[0])
        result = import_materialize(
            container.workspace,
            plugin_id=plugin.manifest.id,
            plan=plan,
            chunk_rows=container.config.performance.import_chunk_rows,
        )
        assert result.success, result.message
        timings["import_s"] = time.perf_counter() - t0

        assert container.workspace.project is not None
        dataset_id = container.workspace.project.datasets[0].id

        t0 = time.perf_counter()
        profile = profile_revision(container.workspace, dataset_id)
        assert profile.success, profile.message
        timings["profile_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        spec = ChartSpec(
            id=uuid4(),
            chart_type="bar",
            dataset_id=dataset_id,
            title="bench",
            encodings=(
                ChartEncoding(role="x", field="region"),
                ChartEncoding(role="y", field="amount", aggregation="sum"),
            ),
        )
        data = container.chart_data.query(spec)
        assert data.batch.num_rows > 0
        timings["chart_query_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        rev = container.workspace.project.datasets[0].current_revision_id
        assert rev is not None
        _ = container.workspace.analytics.fetch_window(rev, offset=0, limit=500)
        timings["grid_window_s"] = time.perf_counter() - t0
    finally:
        container.plugins.deactivate_all()
        container.workspace.close()
        container.jobs.shutdown(wait=False)
    return timings


def main() -> int:
    parser = argparse.ArgumentParser(description="Prism BI M5 benchmark harness")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--work-dir", type=Path, default=Path("benchmarks") / "out")
    args = parser.parse_args()
    timings = run_benchmark(rows=args.rows, work_dir=args.work_dir)
    print(f"rows={args.rows}")
    for key, value in timings.items():
        print(f"{key}={value:.4f}")
    # Soft thresholds for 100k (document; do not fail CI hard on slow agents).
    if args.rows <= 100_000:
        total = timings["import_s"] + timings["profile_s"]
        print(f"import_plus_profile_s={total:.4f}")
        print("target_import_plus_profile_s<=5.0 (NFR-01 aspirational on reference hardware)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
