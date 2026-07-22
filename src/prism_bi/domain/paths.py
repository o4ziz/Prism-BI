"""Path safety helpers (no infrastructure dependencies)."""

from __future__ import annotations

from pathlib import Path

from prism_bi.domain.errors import ValidationError


def canonicalize_path(path: Path) -> Path:
    """Resolve symlinks/relative segments to an absolute path."""
    try:
        return path.expanduser().resolve(strict=False)
    except OSError as exc:
        raise ValidationError(f"Invalid path: {path}", code="path_invalid") from exc


def ensure_within(path: Path, root: Path) -> Path:
    """Ensure ``path`` resolves under ``root`` (no path traversal escape)."""
    resolved = canonicalize_path(path)
    root_resolved = canonicalize_path(root)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValidationError(
            f"Path escapes allowed root: {resolved}",
            code="path_traversal",
        ) from exc
    return resolved


def validate_user_file(path: Path) -> Path:
    """Validate an existing user-selected file for import."""
    resolved = canonicalize_path(path)
    if not resolved.is_file():
        raise ValidationError(f"File not found: {resolved}", code="file_missing")
    return resolved


def validate_export_destination(path: Path) -> Path:
    """Validate an export destination path (parent must exist or be creatable)."""
    resolved = canonicalize_path(path)
    parent = resolved.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValidationError(
                f"Cannot create export directory: {parent}",
                code="export_path_invalid",
            ) from exc
    if resolved.exists() and resolved.is_dir():
        raise ValidationError("Export destination is a directory", code="export_path_invalid")
    return resolved
