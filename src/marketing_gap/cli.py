"""CLI entry point for marketing-gap-analyzer.

Usage:
  mgap analyze --config config.yaml              # Full pipeline
  mgap extract-official --config config.yaml      # Step 1
  mgap extract-user --config config.yaml          # Step 2
  mgap gap-matrix --config config.yaml            # Step 3
  mgap render --config config.yaml                # Step 4 (Feishu MD)
"""

from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path

from .config import Config
from .extractors.official import extract_official
from .extractors.user import extract_user
from .analysis.gap_matrix import run_gap_analysis
from .renderers.feishu_md import render


def cmd_extract_official(args):
    result = extract_official(args.config)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Output written to {args.output}")


def cmd_extract_user(args):
    result = extract_user(args.config)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Output written to {args.output}")


def cmd_gap_matrix(args):
    run_gap_analysis(args.config)


def cmd_render(args):
    render(args.config)


def cmd_analyze(args):
    """Run full pipeline: extract-official → extract-user → gap-matrix → render."""
    print("=" * 60)
    print("  marketing-gap-analyzer — Full Analysis Pipeline")
    print("=" * 60)
    print(f"  Config: {args.config}")
    print()

    cfg = Config(args.config)
    print(f"  Product: {cfg.project_name}")
    print(f"  Official docs: {cfg.raw_official}")
    print(f"  User comments: {cfg.raw_user}")
    print(f"  Outputs: {cfg.outputs}")
    print()

    # Step 1: Extract official
    print(">>> Step 1/4: Extracting official selling points...")
    extract_official(args.config)

    # Step 2: Extract user
    print("\n>>> Step 2/4: Extracting user voice...")
    extract_user(args.config)

    # Step 3: GAP matrix
    print("\n>>> Step 3/4: Running GAP matrix analysis...")
    run_gap_analysis(args.config)

    # Step 4: Render
    print("\n>>> Step 4/4: Rendering Feishu Markdown report...")
    render(args.config)

    print("\n" + "=" * 60)
    print("  ✅  Pipeline complete!")
    print("=" * 60)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="mgap", description="marketing-gap-analyzer")
    parser.add_argument("--config", "-c", default="config.yaml",
                        help="Path to YAML config file (default: config.yaml)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("analyze", help="Run full pipeline")
    p_extract_official = sub.add_parser("extract-official", help="Extract official selling points only")
    p_extract_official.add_argument("--output", "-o", help="Output JSON path")

    p_extract_user = sub.add_parser("extract-user", help="Extract user voice only")
    p_extract_user.add_argument("--output", "-o", help="Output JSON path")

    sub.add_parser("gap-matrix", help="Run GAP matrix analysis only")
    sub.add_parser("render", help="Render Feishu Markdown report only")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    if args.command == "extract-official":
        cmd_extract_official(args)
    elif args.command == "extract-user":
        cmd_extract_user(args)
    elif args.command == "gap-matrix":
        cmd_gap_matrix(args)
    elif args.command == "render":
        cmd_render(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
