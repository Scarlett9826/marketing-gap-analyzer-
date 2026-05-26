#!/usr/bin/env python3
"""Validate raw_*.json files against the expected schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_OFFICIAL_FIELDS = {"source", "type", "content"}
REQUIRED_USER_FIELDS = {"source", "post_id", "content"}


def validate(path: Path, kind: str) -> tuple[int, list[str]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        return 1, ["Top-level JSON must be an array"]

    required = REQUIRED_OFFICIAL_FIELDS if kind == "official" else REQUIRED_USER_FIELDS
    errors: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"[{i}] not an object")
            continue
        missing = required - set(item.keys())
        if missing:
            errors.append(f"[{i}] missing fields: {sorted(missing)}")
        if not item.get("content", "").strip():
            errors.append(f"[{i}] empty content")
    return len(items), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--kind", choices=["official", "user"], default="user",
        help="Schema to validate against (default: user)",
    )
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2

    count, errors = validate(args.file, args.kind)
    print(f"Total items: {count}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return 1
    print("OK — schema valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
