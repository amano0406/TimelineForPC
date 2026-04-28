from __future__ import annotations

import argparse
from pathlib import Path

from timeline_for_pc.doctor import format_doctor_result
from timeline_for_pc.doctor import run_doctor
from timeline_for_pc.redaction import REDACTION_PROFILES
from timeline_for_pc.runner import run_capture
from timeline_for_pc.settings import SettingsError
from timeline_for_pc.settings import init_settings
from timeline_for_pc.settings import load_settings
from timeline_for_pc.smoke import run_smoke_test


MOCK_PROFILES = ("baseline", "upgraded")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.error("A command is required.")
        return 2

    if args.command == "settings":
        if args.settings_command == "init":
            result = init_settings()
            print("OK")
            print(f"settings_path: {result.path}")
            print(f"created: {str(result.created).lower()}")
            return 0
        parser.error("A settings subcommand is required.")
        return 2

    try:
        settings = load_settings()
        redaction_profile = _require_choice(
            "redaction_profile",
            getattr(args, "redaction_profile", None) or settings.redaction_profile,
            REDACTION_PROFILES,
        )
        mock_profile = _require_choice(
            "mock_profile",
            getattr(args, "mock_profile", None) or settings.mock_profile,
            MOCK_PROFILES,
        )
    except SettingsError as exc:
        print("NG")
        print(f"- {exc}")
        return 1
    except ValueError as exc:
        print("NG")
        print(f"- {exc}")
        return 1

    if args.command == "capture":
        run_dir = run_capture(
            output_root=args.output_root or settings.output_root,
            mock=args.mock,
            mock_profile=mock_profile,
            redaction_profile=redaction_profile,
        )
        print(run_dir)
        return 0

    if args.command == "smoke-test":
        output_root = args.output_root or (settings.output_root / "_smoke")
        result = run_smoke_test(
            output_root=output_root,
            live=args.live,
            redaction_profile=redaction_profile,
        )
        print("OK" if result.ok else "NG")
        print(f"run_dir: {result.run_dir}")
        if result.export_path is not None:
            print(f"export: {result.export_path}")
        for issue in result.issues:
            print(f"- {issue}")
        return 0 if result.ok else 1

    if args.command == "doctor":
        result = run_doctor(output_root=args.output_root or settings.output_root)
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
        default=None,
        help="Directory that will contain TimelineForPC run folders.",
    )
    capture_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic mock data instead of live Windows collection.",
    )
    capture_parser.add_argument(
        "--mock-profile",
        default=None,
        choices=MOCK_PROFILES,
        help="Mock data profile to use when --mock is enabled.",
    )
    capture_parser.add_argument(
        "--redaction-profile",
        default=None,
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
        default=None,
        help="Directory that will contain smoke-test run folders.",
    )
    smoke_parser.add_argument(
        "--live",
        action="store_true",
        help="Use live Windows collection instead of deterministic mock data.",
    )
    smoke_parser.add_argument(
        "--redaction-profile",
        default=None,
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
        default=None,
        help="Directory that normal capture runs will write under.",
    )

    settings_parser = subparsers.add_parser(
        "settings",
        help="Manage local persistent settings.",
    )
    settings_subparsers = settings_parser.add_subparsers(dest="settings_command")
    settings_subparsers.add_parser(
        "init",
        help="Create settings.json from settings.example.json if it does not exist.",
    )
    return parser


def _require_choice(name: str, value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}; got {value!r}.")
    return value
