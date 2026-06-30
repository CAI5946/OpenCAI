import unittest

from app import main
from config import DEFAULT_PUNCTUATION


class GreetingTests(unittest.TestCase):
    def test_default_punctuation_is_exclamation(self) -> None:
        self.assertEqual("!", DEFAULT_PUNCTUATION)

    def test_greeting_uses_configured_punctuation(self) -> None:
        self.assertEqual("Hello, Ada!", main(["--name", "Ada"]))


if __name__ == "__main__":
    unittest.main()
