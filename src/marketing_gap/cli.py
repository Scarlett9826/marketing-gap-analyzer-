"""CLI entry point for marketing-gap-analyzer.

Usage:
  mgap -c config.yaml analyze              # Full pipeline
  mgap -c config.yaml extract-official     # Step 1
  mgap -c config.yaml extract-user         # Step 2
  mgap -c config.yaml gap-matrix           # Step 3
  mgap -c config.yaml render               # Step 4 (Feishu MD)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .analysis.gap_matrix import run_gap_analysis
from .config import Config
from .extractors.official import extract_official
from .extractors.user import extract_user
from .renderers.feishu_md import render


def cmd_extract_official(args: argparse.Namespace) -> None:
    result = extract_official(args.config, output_path=args.output)
    if args.output:
        print(f"Output written to {args.output}")
    elif not _has_outputs_dir(args.config):
        # Print summary to stdout when no output configured
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


def cmd_extract_user(args: argparse.Namespace) -> None:
    result = extract_user(args.config, output_path=args.output)
    if args.output:
        print(f"Output written to {args.output}")
    elif not _has_outputs_dir(args.config):
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


def cmd_gap_matrix(args: argparse.Namespace) -> None:
    run_gap_analysis(args.config, output_path=args.output)


def cmd_render(args: argparse.Namespace) -> None:
    render(args.config, output_path=args.output)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run full pipeline: extract-official → extract-user → gap-matrix → render."""
    print("=" * 60)
    print("  marketing-gap-analyzer — Full Analysis Pipeline")
    print("=" * 60)
    print(f"  Config: {args.config}")

    cfg = Config(args.config)
    print(f"  Product: {cfg.project_name}")
    print(f"  Official docs: {cfg.raw_official}")
    print(f"  User comments: {cfg.raw_user}")
    print(f"  Outputs: {cfg.outputs}")
    print()

    print(">>> Step 1/4: Extracting official selling points...")
    extract_official(args.config)

    print("\n>>> Step 2/4: Extracting user voice...")
    extract_user(args.config)

    print("\n>>> Step 3/4: Running GAP matrix analysis...")
    run_gap_analysis(args.config)

    print("\n>>> Step 4/4: Rendering Feishu Markdown report...")
    render(args.config)

    print("\n" + "=" * 60)
    print("  Pipeline complete.")
    print("=" * 60)


def _has_outputs_dir(config_path: str) -> bool:
    try:
        cfg = Config(config_path)
        return cfg.outputs is not None
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mgap",
        description="marketing-gap-analyzer: competitor marketing GAP analysis tool",
    )
    parser.add_argument(
        "--config", "-c", default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("analyze", help="Run full pipeline (default)")

    p1 = sub.add_parser("extract-official", help="Step 1: extract official selling points")
    p1.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p2 = sub.add_parser("extract-user", help="Step 2: extract user voice")
    p2.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p3 = sub.add_parser("gap-matrix", help="Step 3: run GAP matrix analysis")
    p3.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p4 = sub.add_parser("render", help="Step 4: render Feishu Markdown report")
    p4.add_argument("--output", "-o", help="Output Markdown path (overrides config)")

    return parser


COMMANDS = {
    "analyze": cmd_analyze,
    "extract-official": cmd_extract_official,
    "extract-user": cmd_extract_user,
    "gap-matrix": cmd_gap_matrix,
    "render": cmd_render,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to "analyze" when no subcommand given
    if args.command is None:
        args.command = "analyze"

    # Inject default attributes for subcommands without them
    if not hasattr(args, "output"):
        args.output = None

    if not Path(args.config).exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        return 2

    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        handler(args)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
