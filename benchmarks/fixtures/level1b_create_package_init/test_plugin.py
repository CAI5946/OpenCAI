import unittest

from plugins import run


class PluginTests(unittest.TestCase):
    def test_package_exports_run(self) -> None:
        self.assertEqual("plugin ok", run())


if __name__ == "__main__":
    unittest.main()
