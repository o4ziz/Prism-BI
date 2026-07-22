"""V1 datasource golden fixture tests — core has no extension switches."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from openpyxl import Workbook

from prism_bi.application.use_cases.import_data import import_materialize
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.bootstrap.container import build_container


def _container(tmp_path: Path):
    return build_container(
        user_data_dir=tmp_path / "user",
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )


def _load_plugin(container, plugin_id: str):
    for plugin in container.plugins.active_plugins():
        if plugin.manifest.id == plugin_id and plugin.instance is not None:
            return plugin.instance
    raise AssertionError(f"Plugin not loaded: {plugin_id}")


def test_import_csv_json_sqlite_excel(tmp_path: Path) -> None:
    container = _container(tmp_path)
    try:
        project_root = tmp_path / "proj.prism"
        assert create_project(container.workspace, project_root, "Fixtures").success

        # CSV
        csv_path = tmp_path / "sample.csv"
        csv_path.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
        csv_plugin = _load_plugin(container, "prism.datasource.csv")
        entity = csv_plugin.discover(str(csv_path))[0]
        plan = csv_plugin.materialize(entity)
        assert import_materialize(
            container.workspace, plugin_id=csv_plugin.manifest.id, plan=plan
        ).success

        # JSON
        json_path = tmp_path / "sample.json"
        json_path.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]), encoding="utf-8")
        json_plugin = _load_plugin(container, "prism.datasource.json")
        entity = json_plugin.discover(str(json_path))[0]
        plan = json_plugin.materialize(entity)
        assert import_materialize(
            container.workspace, plugin_id=json_plugin.manifest.id, plan=plan
        ).success

        # SQLite
        sqlite_path = tmp_path / "sample.sqlite"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
        conn.execute("INSERT INTO t VALUES (1,'x'), (2,'y')")
        conn.commit()
        conn.close()
        sqlite_plugin = _load_plugin(container, "prism.datasource.sqlite")
        entity = sqlite_plugin.discover(str(sqlite_path))[0]
        plan = sqlite_plugin.materialize(entity)
        assert import_materialize(
            container.workspace, plugin_id=sqlite_plugin.manifest.id, plan=plan
        ).success

        # Excel
        xlsx_path = tmp_path / "sample.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "Sheet1"
        ws.append(["a", "b"])
        ws.append([1, "x"])
        ws.append([2, "y"])
        wb.save(xlsx_path)
        excel_plugin = _load_plugin(container, "prism.datasource.excel")
        entity = excel_plugin.discover(str(xlsx_path))[0]
        plan = excel_plugin.materialize(entity)
        assert import_materialize(
            container.workspace, plugin_id=excel_plugin.manifest.id, plan=plan
        ).success

        assert len(container.workspace.project.datasets) == 4  # type: ignore[union-attr]
    finally:
        container.workspace.close()
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)


def test_core_has_no_extension_switch() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "prism_bi"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if 'ext == ".csv"' in text or "endswith('.csv')" in text:
            offenders.append(str(path))
    assert not offenders
