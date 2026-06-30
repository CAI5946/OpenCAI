from __future__ import annotations

import argparse

from config import DEFAULT_GREETING, DEFAULT_PUNCTUATION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="world")
    return parser


def main(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    return f"{DEFAULT_GREETING}, {args.name}."


if __name__ == "__main__":
    print(main())
