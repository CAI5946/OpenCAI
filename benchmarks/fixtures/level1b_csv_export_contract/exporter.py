def export_orders(rows: list[tuple[str, int]]) -> str:
    return "\n".join(f"{name};{total}" for name, total in rows)
