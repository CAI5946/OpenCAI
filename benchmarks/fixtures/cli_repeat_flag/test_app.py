import unittest

from app import main


class AppTests(unittest.TestCase):
    def test_default_word(self) -> None:
        self.assertEqual("hello", main([]))

    def test_repeats_word(self) -> None:
        self.assertEqual("go go go", main(["--word", "go", "--times", "3"]))


if __name__ == "__main__":
    unittest.main()
