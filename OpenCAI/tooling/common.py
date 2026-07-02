"""Shared non-path helpers for tools."""

from __future__ import annotations


def coerce_positive_int(value: object, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, int):
        return default
    return max(minimum, min(value, maximum))

