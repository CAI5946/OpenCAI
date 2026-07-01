from __future__ import annotations


def format_output_title(title: str = "") -> str:
    if not title:
        return ""
    if title.startswith("• "):
        return title
    return f"• {title}"
