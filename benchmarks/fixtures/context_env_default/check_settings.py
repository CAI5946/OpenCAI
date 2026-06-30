from pathlib import Path

from settings import DEFAULT_ENVIRONMENT


readme = Path("README.md").read_text(encoding="utf-8")

if "default deployment environment is `production`" not in readme:
    raise SystemExit("README no longer documents the expected environment")

if DEFAULT_ENVIRONMENT != "production":
    raise SystemExit(
        f"DEFAULT_ENVIRONMENT should be production, got {DEFAULT_ENVIRONMENT}"
    )
