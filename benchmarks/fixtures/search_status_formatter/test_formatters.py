import unittest

from formatters import format_status


class FormatterTests(unittest.TestCase):
    def test_formats_status_message(self) -> None:
        self.assertEqual("STATUS: ready", format_status("ready"))


if __name__ == "__main__":
    unittest.main()
