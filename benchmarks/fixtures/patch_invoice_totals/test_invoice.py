import unittest

from invoice import subtotal, total_with_tax


class InvoiceTests(unittest.TestCase):
    def test_subtotal_includes_all_items(self) -> None:
        self.assertEqual(35.0, subtotal([10.0, 20.0, 5.0]))

    def test_total_applies_percentage_tax(self) -> None:
        self.assertEqual(38.5, total_with_tax([10.0, 20.0, 5.0], 0.1))


if __name__ == "__main__":
    unittest.main()
