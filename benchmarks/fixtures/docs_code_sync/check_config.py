from pathlib import Path

from config import DEFAULT_TIMEOUT_SECONDS


readme = Path("README.md").read_text(encoding="utf-8")
expected = "The default request timeout is 30 seconds."

if expected not in readme:
    raise SystemExit("README no longer documents the expected timeout")

if DEFAULT_TIMEOUT_SECONDS != 30:
    raise SystemExit(
        f"DEFAULT_TIMEOUT_SECONDS should be 30, got {DEFAULT_TIMEOUT_SECONDS}"
    )
