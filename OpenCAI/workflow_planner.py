"""Backward-compatible workflow planner module."""

from OpenCAI.workflow.planner import *  # noqa: F403
from OpenCAI.workflow.planner import main


if __name__ == "__main__":
    raise SystemExit(main())
