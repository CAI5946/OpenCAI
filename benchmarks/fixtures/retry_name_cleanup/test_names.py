import unittest

from names import normalize_name


class NameTests(unittest.TestCase):
    def test_trims_and_title_cases_name(self) -> None:
        self.assertEqual("Ada Lovelace", normalize_name("  ada lovelace  "))

    def test_collapses_extra_internal_spaces(self) -> None:
        self.assertEqual("Grace Hopper", normalize_name("grace   hopper"))


if __name__ == "__main__":
    unittest.main()
