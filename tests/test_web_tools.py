from __future__ import annotations

from email.message import Message
from pathlib import Path
import unittest
from unittest.mock import patch

from OpenCAI.tools import TOOLS, run_tool


class FakeHttpResponse:
    def __init__(
        self,
        body: str,
        url: str = "https://example.com/page",
        content_type: str = "text/html; charset=utf-8",
        status: int = 200,
    ) -> None:
        self._body = body.encode("utf-8")
        self._url = url
        self.status = status
        self.headers = Message()
        self.headers["content-type"] = content_type

    def __enter__(self) -> FakeHttpResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            return self._body
        return self._body[:amount]

    def geturl(self) -> str:
        return self._url


class WebToolsTest(unittest.TestCase):
    def test_web_search_returns_compact_results(self) -> None:
        html = """
        <html><body>
          <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fone">One</a>
          <a class="result__snippet">First snippet</a>
          <a class="result__a" href="https://example.com/two">Two</a>
          <a class="result__snippet">Second snippet</a>
        </body></html>
        """

        with patch("OpenCAI.tooling.web_tools.urlopen", return_value=FakeHttpResponse(html)):
            result = run_tool("web_search", {"query": "opencai", "max_results": 1}, Path.cwd())

        self.assertTrue(result["ok"])
        self.assertEqual("opencai", result["result"]["query"])
        self.assertEqual(
            [{"title": "One", "url": "https://example.com/one", "snippet": "First snippet"}],
            result["result"]["results"],
        )
        self.assertTrue(result["result"]["truncated"])
        self.assertIn("https://example.com/one", result["result"]["content"])

    def test_web_fetch_returns_bounded_content_and_metadata(self) -> None:
        with patch("OpenCAI.tooling.web_tools.urlopen", return_value=FakeHttpResponse("abcdef")):
            result = run_tool(
                "web_fetch",
                {"url": "https://example.com/page", "max_chars": 3},
                Path.cwd(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual("https://example.com/page", result["result"]["final_url"])
        self.assertEqual(200, result["result"]["status"])
        self.assertEqual("abc", result["result"]["content"])
        self.assertTrue(result["result"]["truncated"])

    def test_web_extract_cleans_html_and_collects_links(self) -> None:
        html = """
        <html>
          <head><title>Demo title</title><script>ignore()</script></head>
          <body><h1>Hello</h1><p>World</p><a href="https://example.com/a">Read more</a></body>
        </html>
        """

        result = run_tool("web_extract", {"html": html}, Path.cwd())

        self.assertTrue(result["ok"])
        self.assertEqual("Demo title", result["result"]["title"])
        self.assertIn("Hello World Read more", result["result"]["content"])
        self.assertEqual(
            [{"text": "Read more", "url": "https://example.com/a"}],
            result["result"]["links"],
        )

    def test_web_tools_reject_non_public_urls(self) -> None:
        for tool_name in ["web_fetch", "web_extract"]:
            with self.subTest(tool_name=tool_name):
                file_result = run_tool(tool_name, {"url": "file:///etc/passwd"}, Path.cwd())
                local_result = run_tool(tool_name, {"url": "http://localhost:8000"}, Path.cwd())
                private_result = run_tool(tool_name, {"url": "http://192.168.1.2"}, Path.cwd())

                self.assertFalse(file_result["ok"])
                self.assertFalse(local_result["ok"])
                self.assertFalse(private_result["ok"])

    def test_web_tools_are_registered_as_read_only(self) -> None:
        self.assertTrue(TOOLS["web_search"].read_only)
        self.assertTrue(TOOLS["web_fetch"].read_only)
        self.assertTrue(TOOLS["web_extract"].read_only)


if __name__ == "__main__":
    unittest.main()
