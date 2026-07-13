"""Shared path helpers for local tools."""

from __future__ import annotations

from pathlib import Path


def display_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def resolve_child_path(cwd: Path, path: str) -> Path | None:
    resolved_cwd = cwd.resolve()
    normalized_path = path.replace("\\", "/")
    resolved_target = (resolved_cwd / normalized_path).resolve()
    try:
        resolved_target.relative_to(resolved_cwd)
    except ValueError:
        return None
    return resolved_target

