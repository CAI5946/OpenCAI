"""Web and research tools."""

from __future__ import annotations

from html.parser import HTMLParser
from ipaddress import ip_address
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from OpenCAI.tooling.common import coerce_positive_int
from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result


WEB_USER_AGENT = "OpenCAI/0.0.0-dev (+https://local.opencai)"
WEB_FETCH_MAX_BYTES = 500_000
WEB_SEARCH_ENDPOINT = "https://duckduckgo.com/html/?q="


def _validate_web_url(url: object) -> tuple[str | None, str | None]:
    if not isinstance(url, str) or not url:
        return None, "Missing required string argument: url"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None, "URL must use http or https"
    if not parsed.hostname:
        return None, "URL must include a host"

    hostname = parsed.hostname.lower()
    if hostname in {"localhost"} or hostname.endswith(".local"):
        return None, "Blocked local web host"

    try:
        address = ip_address(hostname.strip("[]"))
    except ValueError:
        address = None

    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    ):
        return None, "Blocked private or local web address"

    return url, None


def _http_get(url: str, timeout: int = 10, max_bytes: int = WEB_FETCH_MAX_BYTES) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": WEB_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # nosec: URL is validated above.
        body = response.read(max_bytes + 1)
        headers = response.headers
        charset = headers.get_content_charset() or "utf-8"
        text = body[:max_bytes].decode(charset, errors="replace")
        return {
            "url": url,
            "final_url": response.geturl(),
            "status": getattr(response, "status", None),
            "content_type": headers.get("content-type", ""),
            "content": text,
            "bytes_read": min(len(body), max_bytes),
            "truncated": len(body) > max_bytes,
        }


def _decode_duckduckgo_url(href: str) -> str:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    uddg = query.get("uddg", [])
    if uddg:
        return unquote(uddg[0])
    return href


def _clean_html_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _ReadableHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks: list[str] = []
        self.links: list[dict[str, str]] = []
        self._current_link: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "a" and attr_map.get("href"):
            self._current_link = attr_map["href"]
            self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
            return
        if tag == "a" and self._current_link:
            text = _clean_html_text(" ".join(self._current_link_text))
            if text:
                self.links.append({"text": text, "url": self._current_link})
            self._current_link = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = _clean_html_text(data)
        if not cleaned:
            return
        if self._in_title:
            self.title = _clean_html_text(f"{self.title} {cleaned}")
            return
        self._chunks.append(cleaned)
        if self._current_link is not None:
            self._current_link_text.append(cleaned)

    def readable_text(self) -> str:
        return _clean_html_text(" ".join(self._chunks))


class _DuckDuckGoSearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._active_result: dict[str, str] | None = None
        self._active_field: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        class_name = attr_map.get("class", "")
        if tag == "a" and "result__a" in class_name:
            self._active_result = {
                "title": "",
                "url": _decode_duckduckgo_url(attr_map.get("href", "")),
                "snippet": "",
            }
            self._active_field = "title"
            self._buffer = []
        elif self._active_result is not None and "result__snippet" in class_name:
            self._active_field = "snippet"
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if self._active_result is None or self._active_field is None:
            return

        if tag in {"a", "div"}:
            value = _clean_html_text(" ".join(self._buffer))
            self._active_result[self._active_field] = value
            if self._active_field == "title":
                self.results.append(self._active_result)
            self._active_field = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._active_field is not None:
            self._buffer.append(data)


def _extract_readable_html(html: str, max_chars: int) -> dict[str, Any]:
    parser = _ReadableHtmlParser()
    parser.feed(html)
    text = parser.readable_text()
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars].rstrip()
    return {
        "title": parser.title,
        "content": text,
        "links": parser.links[:25],
        "truncated": truncated,
    }


def web_search(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    query = arguments.get("query")
    if not isinstance(query, str) or not query:
        return tool_result("web_search", False, error="Missing required string argument: query")

    max_results = coerce_positive_int(arguments.get("max_results"), 5, 1, 10)
    timeout = coerce_positive_int(arguments.get("timeout"), 10, 1, 30)
    search_url = f"{WEB_SEARCH_ENDPOINT}{quote_plus(query)}"

    try:
        response = _http_get(search_url, timeout=timeout)
    except Exception as exc:
        return tool_result("web_search", False, error=f"Web search failed: {exc}")

    parser = _DuckDuckGoSearchParser()
    parser.feed(response["content"])
    results = parser.results[:max_results]
    content = "\n".join(
        f"{index}. {item['title']}\n   {item['url']}\n   {item['snippet']}"
        for index, item in enumerate(results, start=1)
    ) or "No search results found."

    return tool_result(
        "web_search",
        True,
        {
            "query": query,
            "url": search_url,
            "content": content,
            "results": results,
            "truncated": len(parser.results) > max_results,
        },
    )


def web_fetch(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    url, error = _validate_web_url(arguments.get("url"))
    if error:
        return tool_result("web_fetch", False, error=error)

    timeout = coerce_positive_int(arguments.get("timeout"), 10, 1, 30)
    max_chars = coerce_positive_int(arguments.get("max_chars"), 8_000, 1, 50_000)
    assert url is not None

    try:
        response = _http_get(url, timeout=timeout)
    except Exception as exc:
        return tool_result("web_fetch", False, error=f"Web fetch failed: {exc}")

    content = response["content"]
    truncated = response["truncated"] or len(content) > max_chars
    if len(content) > max_chars:
        content = content[:max_chars].rstrip()

    response.update(
        {
            "content": content,
            "truncated": truncated,
        }
    )
    return tool_result("web_fetch", True, response)


def web_extract(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    html = arguments.get("html")
    url = arguments.get("url")
    timeout = coerce_positive_int(arguments.get("timeout"), 10, 1, 30)
    max_chars = coerce_positive_int(arguments.get("max_chars"), 8_000, 1, 50_000)
    source_url = ""

    if isinstance(html, str) and html:
        source_html = html
    else:
        validated_url, error = _validate_web_url(url)
        if error:
            return tool_result("web_extract", False, error="Provide html or a valid url")
        assert validated_url is not None
        try:
            response = _http_get(validated_url, timeout=timeout)
        except Exception as exc:
            return tool_result("web_extract", False, error=f"Web extract failed: {exc}")
        source_url = response["final_url"]
        source_html = response["content"]

    extracted = _extract_readable_html(source_html, max_chars=max_chars)
    extracted["url"] = source_url
    return tool_result("web_extract", True, extracted)


WEB_TOOLS: dict[str, ToolSpec] = {
    "web_search": ToolSpec(
        name="web_search",
        description=(
            "Search the public web and return a compact list of result titles, URLs, and snippets. "
            "Use web_fetch or web_extract to inspect a selected result."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
                "timeout": {"type": "integer"},
            },
            "required": ["query"],
        },
        read_only=True,
        function=web_search,
    ),
    "web_fetch": ToolSpec(
        name="web_fetch",
        description="Fetch a public http/https URL and return response metadata plus bounded text content.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer"},
                "timeout": {"type": "integer"},
            },
            "required": ["url"],
        },
        read_only=True,
        function=web_fetch,
    ),
    "web_extract": ToolSpec(
        name="web_extract",
        description=(
            "Extract readable text, title, and links from provided HTML or from a public http/https URL."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "html": {"type": "string"},
                "max_chars": {"type": "integer"},
                "timeout": {"type": "integer"},
            },
        },
        read_only=True,
        function=web_extract,
    ),
}

