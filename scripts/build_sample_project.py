"""Build the GA sample project under samples/SalesDemo.prism."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from prism_bi.application.use_cases.import_data import import_materialize
from prism_bi.application.use_cases.profile_data import profile_revision
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.bootstrap.container import build_container
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
CSV = SAMPLES / "data" / "sales_demo.csv"
PROJECT = SAMPLES / "SalesDemo.prism"


def main() -> int:
    if not CSV.is_file():
        raise SystemExit(f"Missing sample CSV: {CSV}")
    if PROJECT.exists():
        shutil.rmtree(PROJECT)

    userdata = SAMPLES / ".build-userdata"
    if userdata.exists():
        shutil.rmtree(userdata)

    container = build_container(
        user_data_dir=userdata,
        use_keyring=False,
        console_logging=False,
        repo_root=ROOT,
        defer_plugin_activation=False,
    )
    try:
        created = create_project(container.workspace, PROJECT, "Sales Demo")
        if not created.success:
            raise SystemExit(created.message or "create_project failed")

        plugin = None
        for reg in container.plugins.registry.list_by_kind(ContributionKind.DATA_SOURCES):
            extensions = [str(e).lower() for e in (reg.metadata or {}).get("extensions", [])]
            if ".csv" in extensions:
                plugin = reg.factory
                break
        if plugin is None:
            raise SystemExit("CSV datasource plugin not found")

        entities = plugin.discover(str(CSV))
        plan = plugin.materialize(entities[0])
        imported = import_materialize(
            container.workspace,
            plugin_id=plugin.manifest.id,
            plan=plan,
            chunk_rows=container.config.performance.import_chunk_rows,
        )
        if not imported.success:
            raise SystemExit(imported.message or "import failed")

        assert container.workspace.project is not None
        dataset_id = container.workspace.project.datasets[0].id
        profiled = profile_revision(container.workspace, dataset_id)
        if not profiled.success:
            raise SystemExit(profiled.message or "profile failed")

        # Seed one chart so Visualize is non-empty for first-run demos.
        container.workspace.project.charts.append(
            ChartSpec(
                id=uuid4(),
                chart_type="bar",
                dataset_id=dataset_id,
                title="Revenue by region",
                encodings=(
                    ChartEncoding(role="x", field="region"),
                    ChartEncoding(role="y", field="revenue", aggregation="sum"),
                ),
            )
        )
        # Portable provenance (absolute paths would bind the sample to one machine).
        for dataset in container.workspace.project.datasets:
            dataset.source_entity_id = "samples/data/sales_demo.csv"
        container.workspace.save()
        print(f"Sample project ready: {PROJECT}")
        return 0
    finally:
        container.plugins.deactivate_all()
        container.workspace.close()
        container.jobs.shutdown(wait=False)
        if userdata.exists():
            shutil.rmtree(userdata, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
