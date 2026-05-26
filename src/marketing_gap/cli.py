"""CLI entry point for marketing-gap-analyzer.

The CLI is organised around two pipelines:

1. **Data collection** — ``mgap fetch <platform>`` shells out to a built-in or
   third-party crawler and writes a normalised JSON file ready to be analysed.
2. **Analysis** — ``mgap analyze`` (default) extracts official selling points,
   user voice, builds the GAP matrix, and renders a Feishu-ready Markdown
   report. Each step can also be run in isolation.

Examples::

  mgap fetch weibo --urls urls.txt --cookie weibo_cookie.json -o data/raw_user.json
  mgap fetch bilibili --keywords "Pura X Max" -o data/bili.json
  mgap fetch xiaohongshu --keywords "Pura X Max" -o data/xhs.json
   mgap -c config.yaml verify-official     # (optional) verify URLs + auto-fill verifiable
   mgap -c config.yaml analyze
   mgap -c config.yaml extract-official -o out/points.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .analysis.gap_matrix import run_gap_analysis
from .config import Config
from .crawlers.verify_official import verify_official
from .extractors.official import extract_official
from .extractors.user import extract_user
from .renderers.feishu_md import render as render_feishu
from .renderers.html import render_html


# ---------------------------------------------------------------------------
# Analysis subcommands
# ---------------------------------------------------------------------------

def cmd_extract_official(args: argparse.Namespace) -> None:
    result = extract_official(args.config, output_path=args.output)
    if args.output:
        print(f"Output written to {args.output}")
    elif not _has_outputs_dir(args.config):
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
    fmt = getattr(args, "format", "feishu")
    if fmt in ("feishu", "both"):
        render_feishu(args.config, output_path=args.output)
    if fmt in ("html", "both"):
        out = args.output
        if out and fmt == "both":
            from pathlib import Path
            out = str(Path(out).with_suffix(".html"))
        elif not out:
            out = None
        render_html(args.config, output_path=out)


def cmd_verify_official(args: argparse.Namespace) -> None:
    verify_official(args.config)


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

    print(">>> Step 0/4: Verifying official document URLs...")
    verify_official(args.config)

    print("\n>>> Step 1/4: Extracting official selling points...")
    extract_official(args.config)

    print("\n>>> Step 2/4: Extracting user voice...")
    extract_user(args.config)

    print("\n>>> Step 3/4: Running GAP matrix analysis...")
    run_gap_analysis(args.config)

    print("\n>>> Step 4/4: Rendering Feishu Markdown report...")
    render_feishu(args.config)

    print("\n" + "=" * 60)
    print("  Pipeline complete.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Fetch (data collection) subcommands
# ---------------------------------------------------------------------------

def _read_url_list(arg: str) -> list[str]:
    """Accept either ``--urls a,b,c`` or ``--urls path/to/file.txt``."""
    candidate = Path(arg)
    if candidate.exists():
        return [
            line.strip()
            for line in candidate.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    return [u.strip() for u in arg.split(",") if u.strip()]


def cmd_fetch_weibo(args: argparse.Namespace) -> None:
    from .crawlers.weibo import WeiboCrawlConfig, fetch_many

    urls = _read_url_list(args.urls)
    if not urls:
        raise SystemExit("Error: --urls produced no entries (file empty?).")

    cfg = WeiboCrawlConfig(
        sleep_per_request=args.sleep,
        max_comments_per_post=args.max_comments,
        fetch_second_level=args.replies,
    )
    out_dir = Path(args.work_dir or Path(args.output).with_suffix("") )
    fetch_many(
        urls,
        cookie_path=args.cookie,
        output_dir=out_dir,
        merged_output=args.output,
        config=cfg,
    )


def cmd_fetch_bilibili(args: argparse.Namespace) -> None:
    from .crawlers.bilibili import fetch_search

    fetch_search(
        keywords=args.keywords,
        output_path=args.output,
        start=args.start,
        login_type=args.login,
        mediacrawler_home=args.mediacrawler_home,
    )
    print(f"Output written to {args.output}")


def cmd_fetch_xiaohongshu(args: argparse.Namespace) -> None:
    from .crawlers.xiaohongshu import fetch_search

    fetch_search(
        keywords=args.keywords,
        output_path=args.output,
        start=args.start,
        login_type=args.login,
        mediacrawler_home=args.mediacrawler_home,
    )
    print(f"Output written to {args.output}")


def cmd_fetch_zhihu(args: argparse.Namespace) -> None:
    from .crawlers.zhihu import fetch_search

    fetch_search(
        keywords=args.keywords,
        output_path=args.output,
        start=args.start,
        login_type=args.login,
        mediacrawler_home=args.mediacrawler_home,
    )
    print(f"Output written to {args.output}")


def cmd_fetch_douyin(args: argparse.Namespace) -> None:
    from .crawlers.douyin import fetch_search

    fetch_search(
        keywords=args.keywords,
        output_path=args.output,
        start=args.start,
        login_type=args.login,
        mediacrawler_home=args.mediacrawler_home,
    )
    print(f"Output written to {args.output}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_outputs_dir(config_path: str) -> bool:
    try:
        cfg = Config(config_path)
        return cfg.outputs is not None
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mgap",
        description="marketing-gap-analyzer: end-to-end competitor marketing GAP analysis tool",
    )
    parser.add_argument(
        "--config", "-c", default="config.yaml",
        help="Path to YAML config file (default: config.yaml; not required for `fetch`)",
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- analysis -----------------------------------------------------------
    sub.add_parser("analyze", help="Run full analysis pipeline (default)")

    p1 = sub.add_parser("extract-official", help="Step 1: extract official selling points")
    p1.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p2 = sub.add_parser("extract-user", help="Step 2: extract user voice")
    p2.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p3 = sub.add_parser("gap-matrix", help="Step 3: run GAP matrix analysis")
    p3.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p_vfy = sub.add_parser("verify-official", help="Step 0: verify official document URLs (reachable + content match)")
    p_vfy.add_argument("--output", "-o", help="Output JSON path (overrides config)")

    p4 = sub.add_parser("render", help="Step 4: render Feishu Markdown / HTML report")
    p4.add_argument("--output", "-o", help="Output path (overrides config)")
    p4.add_argument("--format", default="feishu", choices=["feishu", "html", "both"],
                    help="Output format (default: feishu)")

    # --- fetch (data collection) -------------------------------------------
    fetch = sub.add_parser(
        "fetch",
        help="Collect raw user comments from a social platform",
        description="Bundled crawlers for the most common Chinese social platforms.",
    )
    fetch_sub = fetch.add_subparsers(dest="platform", metavar="PLATFORM")

    fw = fetch_sub.add_parser("weibo", help="Fetch first-level comments from Weibo URLs")
    fw.add_argument("--urls", required=True,
                    help="Comma-separated URL list, OR path to a .txt file (one URL per line)")
    fw.add_argument("--cookie", required=True, help="Path to weibo_cookie.json")
    fw.add_argument("--output", "-o", required=True, help="Merged JSON output (raw_user format)")
    fw.add_argument("--work-dir", help="Directory for per-post checkpoint files (default: alongside output)")
    fw.add_argument("--max-comments", type=int, default=800,
                    help="Cap per post (default: 800)")
    fw.add_argument("--sleep", type=float, default=0.6,
                    help="Seconds between requests (default: 0.6)")
    fw.add_argument("--replies", action="store_true", help="Also fetch second-level replies")

    fb = fetch_sub.add_parser("bilibili", help="Search Bilibili and fetch comments (via MediaCrawler)")
    fb.add_argument("--keywords", required=True, help="Comma-separated keywords")
    fb.add_argument("--output", "-o", required=True, help="Output JSON path")
    fb.add_argument("--start", type=int, default=1, help="Page offset for search")
    fb.add_argument("--login", default="qrcode", choices=["qrcode", "phone", "cookie"])
    fb.add_argument("--mediacrawler-home", help="Path to MediaCrawler checkout (or set MEDIACRAWLER_HOME)")

    fx = fetch_sub.add_parser("xiaohongshu", help="Search Xiaohongshu and fetch comments (via MediaCrawler)")
    fx.add_argument("--keywords", required=True)
    fx.add_argument("--output", "-o", required=True)
    fx.add_argument("--start", type=int, default=1)
    fx.add_argument("--login", default="qrcode", choices=["qrcode", "phone", "cookie"])
    fx.add_argument("--mediacrawler-home")

    fz = fetch_sub.add_parser("zhihu", help="Search Zhihu and fetch comments (via MediaCrawler)")
    fz.add_argument("--keywords", required=True)
    fz.add_argument("--output", "-o", required=True)
    fz.add_argument("--start", type=int, default=1)
    fz.add_argument("--login", default="qrcode", choices=["qrcode", "phone", "cookie"])
    fz.add_argument("--mediacrawler-home")

    fd = fetch_sub.add_parser("douyin", help="Search Douyin and fetch comments (via MediaCrawler)")
    fd.add_argument("--keywords", required=True)
    fd.add_argument("--output", "-o", required=True)
    fd.add_argument("--start", type=int, default=1)
    fd.add_argument("--login", default="qrcode", choices=["qrcode", "phone", "cookie"])
    fd.add_argument("--mediacrawler-home")

    return parser


# Map (command, subcommand) → handler.
ANALYSIS_COMMANDS = {
    "analyze": cmd_analyze,
    "verify-official": cmd_verify_official,
    "extract-official": cmd_extract_official,
    "extract-user": cmd_extract_user,
    "gap-matrix": cmd_gap_matrix,
    "render": cmd_render,
}

FETCH_COMMANDS = {
    "weibo": cmd_fetch_weibo,
    "bilibili": cmd_fetch_bilibili,
    "xiaohongshu": cmd_fetch_xiaohongshu,
    "zhihu": cmd_fetch_zhihu,
    "douyin": cmd_fetch_douyin,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        args.command = "analyze"

    if args.command == "fetch":
        platform = getattr(args, "platform", None)
        if not platform:
            parser.parse_args([*(argv or []), "fetch", "--help"])
            return 2
        handler = FETCH_COMMANDS.get(platform)
        if handler is None:
            print(f"Unknown fetch platform: {platform}", file=sys.stderr)
            return 1
        try:
            handler(args)
            return 0
        except Exception as exc:
            print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    # Analysis path: requires config file
    if not hasattr(args, "output"):
        args.output = None

    if not Path(args.config).exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        return 2

    handler = ANALYSIS_COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        handler(args)
        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
