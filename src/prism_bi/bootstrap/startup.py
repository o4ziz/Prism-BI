"""Process startup — headless container or full UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from prism_bi.bootstrap.container import AppContainer, build_container


def create_container(*, headless: bool = False) -> AppContainer:
    """Build the composition root container."""
    return build_container(
        use_keyring=not headless,
        console_logging=not headless,
        user_data_dir=_test_data_dir() if headless else None,
        defer_plugin_activation=not headless,
    )


def run_app(*, headless: bool = False) -> int:
    """Start Prism BI. When ``headless``, only build services and exit."""
    if headless or os.environ.get("PRISM_HEADLESS") == "1":
        container = create_container(headless=True)
        container.logger.info("Headless startup complete")
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)
        return 0

    container = create_container(headless=False)
    from prism_bi.presentation.shell.main_window import run_shell

    return run_shell(container)


def _test_data_dir() -> Path | None:
    """Optional override for isolated test user data."""
    raw = os.environ.get("PRISM_USER_DATA")
    return Path(raw) if raw else None


def main(argv: list[str] | None = None) -> int:
    """CLI entry used by ``prism-bi`` console script."""
    args = list(sys.argv[1:] if argv is None else argv)
    headless = "--headless" in args
    return run_app(headless=headless)
