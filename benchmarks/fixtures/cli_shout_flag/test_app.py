import unittest

from app import main


class AppTests(unittest.TestCase):
    def test_greets_name(self) -> None:
        self.assertEqual("Hello, Ada!", main(["--name", "Ada"]))

    def test_shout_uppercases_output(self) -> None:
        self.assertEqual("HELLO, ADA!", main(["--name", "Ada", "--shout"]))


if __name__ == "__main__":
    unittest.main()
