import unittest

from discount import apply_discount


class DiscountTests(unittest.TestCase):
    def test_applies_percentage_discount(self) -> None:
        self.assertEqual(80.0, apply_discount(100.0, 20.0))

    def test_keeps_price_when_discount_is_zero(self) -> None:
        self.assertEqual(50.0, apply_discount(50.0, 0.0))


if __name__ == "__main__":
    unittest.main()
