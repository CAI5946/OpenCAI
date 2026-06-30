import unittest

from mailers import welcome_subject


class TemplateTests(unittest.TestCase):
    def test_welcome_subject_matches_contract(self) -> None:
        self.assertEqual("Welcome, Ada!", welcome_subject("Ada"))


if __name__ == "__main__":
    unittest.main()
