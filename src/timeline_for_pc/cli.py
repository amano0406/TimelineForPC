from __future__ import annotations

import argparse
from pathlib import Path

from timeline_for_pc.redaction import REDACTION_PROFILES
from timeline_for_pc.runner import default_output_root
from timeline_for_pc.runner import run_capture


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "capture":
        run_dir = run_capture(
            output_root=args.output_root,
            mock=args.mock,
            mock_profile=args.mock_profile,
            redaction_profile=args.redaction_profile,
        )
        print(run_dir)
        return 0

    parser.error("A command is required.")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="timeline-for-pc")
    subparsers = parser.add_subparsers(dest="command")

    capture_parser = subparsers.add_parser("capture", help="Collect one machine snapshot and write a run directory.")
    capture_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(),
        help="Directory that will contain TimelineForPC run folders.",
    )
    capture_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic mock data instead of live Windows collection.",
    )
    capture_parser.add_argument(
        "--mock-profile",
        default="baseline",
        choices=("baseline", "upgraded"),
        help="Mock data profile to use when --mock is enabled.",
    )
    capture_parser.add_argument(
        "--redaction-profile",
        default="llm_safe",
        choices=REDACTION_PROFILES,
        help="How much redaction to apply to handoff-facing artifacts.",
    )
    return parser
