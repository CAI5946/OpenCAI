import unittest

from exporter import export_orders


class ExporterTests(unittest.TestCase):
    def test_exports_header_and_comma_rows(self) -> None:
        rows = [("Ada", 12), ("Grace", 9)]
        self.assertEqual("name,total\nAda,12\nGrace,9", export_orders(rows))


if __name__ == "__main__":
    unittest.main()
