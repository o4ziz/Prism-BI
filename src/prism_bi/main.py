"""Prism BI process entrypoint."""

from __future__ import annotations

from prism_bi.bootstrap.startup import main as startup_main


def main() -> int:
    """Delegate to the composition root startup."""
    return startup_main()


if __name__ == "__main__":
    raise SystemExit(main())
