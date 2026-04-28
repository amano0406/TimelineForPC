from __future__ import annotations

import argparse
from pathlib import Path

from timeline_for_pc.doctor import format_doctor_result
from timeline_for_pc.doctor import run_doctor
from timeline_for_pc.redaction import REDACTION_PROFILES
from timeline_for_pc.runner import default_output_root
from timeline_for_pc.runner import run_capture
from timeline_for_pc.smoke import run_smoke_test


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

    if args.command == "smoke-test":
        result = run_smoke_test(
            output_root=args.output_root,
            live=args.live,
            redaction_profile=args.redaction_profile,
        )
        print("OK" if result.ok else "NG")
        print(f"run_dir: {result.run_dir}")
        if result.export_path is not None:
            print(f"export: {result.export_path}")
        for issue in result.issues:
            print(f"- {issue}")
        return 0 if result.ok else 1

    if args.command == "doctor":
        result = run_doctor(output_root=args.output_root)
        for line in format_doctor_result(result):
            print(line)
        return 0 if result.ok else 1

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

    smoke_parser = subparsers.add_parser(
        "smoke-test",
        help="Run a capture and verify the output contract.",
    )
    smoke_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root() / "_smoke",
        help="Directory that will contain smoke-test run folders.",
    )
    smoke_parser.add_argument(
        "--live",
        action="store_true",
        help="Use live Windows collection instead of deterministic mock data.",
    )
    smoke_parser.add_argument(
        "--redaction-profile",
        default="llm_safe",
        choices=REDACTION_PROFILES,
        help="How much redaction to apply to handoff-facing artifacts.",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check whether this PC can run live collection.",
    )
    doctor_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(),
        help="Directory that normal capture runs will write under.",
    )
    return parser
