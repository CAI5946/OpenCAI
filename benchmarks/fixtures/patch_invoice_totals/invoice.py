def subtotal(items: list[float]) -> float:
    return sum(items[:-1])


def total_with_tax(items: list[float], tax_rate: float) -> float:
    return subtotal(items) + tax_rate
