import unittest

from app import article_slug


class SlugTests(unittest.TestCase):
    def test_builds_article_slug(self) -> None:
        self.assertEqual("hello-world", article_slug("Hello, World!"))


if __name__ == "__main__":
    unittest.main()
