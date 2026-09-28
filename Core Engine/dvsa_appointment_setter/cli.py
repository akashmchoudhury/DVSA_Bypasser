from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .browser_bot import run_assistant
from .config import load_config
from .logger import MarkdownProcessLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dvsa-appointment-setter",
        description="Headful DVSA appointment assistant with logging and optional proxy support.",
    )
    parser.add_argument(
        "--config",
        default="config.example.json",
        help="Path to the JSON config file.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one page-text check and exit after the browser is prepared.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        logger = MarkdownProcessLogger(config.logging.process_log_path)
        run_assistant(config, logger, once=args.once)
        return 0
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
