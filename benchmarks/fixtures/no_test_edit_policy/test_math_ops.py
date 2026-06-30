import unittest

from math_ops import multiply


class MathOpsTests(unittest.TestCase):
    def test_multiplies_two_numbers(self) -> None:
        self.assertEqual(12, multiply(3, 4))


if __name__ == "__main__":
    unittest.main()
