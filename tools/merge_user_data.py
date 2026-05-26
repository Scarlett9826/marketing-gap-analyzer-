#!/usr/bin/env python3
"""Merge multiple raw_user.json files, de-duplicating by (source, post_id)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def merge(files: list[Path]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for f in files:
        items = json.loads(f.read_text(encoding="utf-8"))
        for it in items:
            key = (it.get("source", ""), it.get("post_id", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)

    merged = merge(args.files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Merged {len(merged)} unique entries from {len(args.files)} files → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
