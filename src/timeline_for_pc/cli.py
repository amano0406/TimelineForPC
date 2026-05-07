from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from timeline_for_pc.doctor import doctor_result_payload
from timeline_for_pc.doctor import format_doctor_result
from timeline_for_pc.doctor import run_doctor
from timeline_for_pc.items import download_items
from timeline_for_pc.items import download_result_payload
from timeline_for_pc.items import list_items
from timeline_for_pc.redaction import REDACTION_PROFILES
from timeline_for_pc.runner import run_capture
from timeline_for_pc.settings import SettingsError
from timeline_for_pc.settings import init_settings
from timeline_for_pc.settings import load_settings
from timeline_for_pc.settings import save_settings
from timeline_for_pc.settings import settings_path
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
        if args.settings_command == "status":
            try:
                settings = load_settings()
            except SettingsError as exc:
                print(_json_payload({"schema_version": 1, "ok": False, "error": {"message": str(exc)}}))
                return 1
            payload = _settings_payload(path=_settings_path(), settings=settings)
            if args.json:
                print(_json_payload(payload))
            else:
                print("OK")
                print(f"output_root: {settings.output_root}")
                print(f"redaction_profile: {settings.redaction_profile}")
                print(f"mock_profile: {settings.mock_profile}")
            return 0
        if args.settings_command == "save":
            try:
                current = load_settings()
                result = save_settings(
                    output_root=args.output_root or current.output_root,
                    redaction_profile=args.redaction_profile or current.redaction_profile,
                    mock_profile=args.mock_profile or current.mock_profile,
                )
            except SettingsError as exc:
                if args.json:
                    print(_json_payload({"schema_version": 1, "ok": False, "error": {"message": str(exc)}}))
                else:
                    print("NG")
                    print(f"- {exc}")
                return 1
            payload = _settings_payload(path=result.path, settings=result.settings)
            if args.json:
                print(_json_payload(payload))
            else:
                print("OK")
                print(f"settings_path: {result.path}")
                print(f"output_root: {result.settings.output_root}")
                print(f"redaction_profile: {result.settings.redaction_profile}")
                print(f"mock_profile: {result.settings.mock_profile}")
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
        if getattr(args, "json", False):
            print(_json_payload({"schema_version": 1, "ok": False, "error": {"message": str(exc)}}))
        else:
            print("NG")
            print(f"- {exc}")
        return 1
    except ValueError as exc:
        if getattr(args, "json", False):
            print(_json_payload({"schema_version": 1, "ok": False, "error": {"message": str(exc)}}))
        else:
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
        if getattr(args, "json", False):
            print(_json_payload(_capture_payload(run_dir)))
        else:
            print(run_dir)
        return 0

    if args.command == "items":
        if args.items_command == "refresh":
            run_dir = run_capture(
                output_root=args.output_root or settings.output_root,
                mock=args.mock,
                mock_profile=mock_profile,
                redaction_profile=redaction_profile,
            )
            if args.json:
                print(_json_payload(_capture_payload(run_dir)))
            else:
                print(run_dir)
            return 0
        if args.items_command == "list":
            payload = list_items(
                output_root=args.output_root or settings.output_root,
                page=args.page,
                page_size=args.page_size,
            )
            if args.json:
                print(_json_payload(payload))
            else:
                _print_items_text(payload)
            return 0
        if args.items_command == "download":
            try:
                result = download_items(
                    output_root=args.output_root or settings.output_root,
                    output_path=args.output,
                    to_dir=args.to,
                    overwrite=args.overwrite,
                )
            except OSError as exc:
                if args.json:
                    print(_json_payload({"schema_version": 1, "ok": False, "error": {"message": str(exc)}}))
                else:
                    print("NG")
                    print(f"- {exc}")
                return 1
            payload = download_result_payload(result)
            if args.json:
                print(_json_payload(payload))
            else:
                print(result.archive_path)
            return 0
        parser.error("An items subcommand is required.")
        return 2

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
        output_root = args.output_root or settings.output_root
        result = run_doctor(output_root=output_root)
        if args.json:
            print(_json_payload(doctor_result_payload(result, output_root=output_root)))
        else:
            for line in format_doctor_result(result):
                print(line)
        return 0 if result.ok else 1

    parser.error("A command is required.")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="timeline-for-pc")
    subparsers = parser.add_subparsers(dest="command")

    capture_parser = subparsers.add_parser("capture", help="Collect one machine snapshot and write a run directory.")
    _add_capture_options(capture_parser)

    items_parser = subparsers.add_parser(
        "items",
        help="Timeline-compatible item operations.",
    )
    items_subparsers = items_parser.add_subparsers(dest="items_command")
    items_refresh_parser = items_subparsers.add_parser(
        "refresh",
        help="Collect one PC snapshot and append one timeline event.",
    )
    _add_capture_options(items_refresh_parser)
    items_list_parser = items_subparsers.add_parser(
        "list",
        help="List captured PC timeline items.",
    )
    items_list_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory that contains TimelineForPC item artifacts.",
    )
    items_list_parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="1-based page number.",
    )
    items_list_parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Number of items to return.",
    )
    _add_json_output_option(items_list_parser)

    items_download_parser = items_subparsers.add_parser(
        "download",
        help="Create a ZIP containing TimelineForPC item artifacts.",
    )
    items_download_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory that contains TimelineForPC item artifacts.",
    )
    items_download_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="ZIP file path to create.",
    )
    items_download_parser.add_argument(
        "--to",
        type=Path,
        default=None,
        help="Directory where a timestamped ZIP will be created.",
    )
    items_download_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the target ZIP if it already exists.",
    )
    _add_json_output_option(items_download_parser)

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
    _add_json_output_option(doctor_parser)

    settings_parser = subparsers.add_parser(
        "settings",
        help="Manage local persistent settings.",
    )
    settings_subparsers = settings_parser.add_subparsers(dest="settings_command")
    settings_subparsers.add_parser(
        "init",
        help="Create settings.json from settings.example.json if it does not exist.",
    )
    settings_status_parser = settings_subparsers.add_parser(
        "status",
        help="Show resolved local settings.",
    )
    settings_status_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    settings_save_parser = settings_subparsers.add_parser(
        "save",
        help="Save local persistent settings.",
    )
    settings_save_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Default output root for capture runs.",
    )
    settings_save_parser.add_argument(
        "--redaction-profile",
        default=None,
        choices=REDACTION_PROFILES,
        help="Default redaction profile.",
    )
    settings_save_parser.add_argument(
        "--mock-profile",
        default=None,
        choices=MOCK_PROFILES,
        help="Default mock profile.",
    )
    _add_json_output_option(settings_save_parser)
    return parser


def _add_capture_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory that will contain TimelineForPC run folders.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic mock data instead of live Windows collection.",
    )
    parser.add_argument(
        "--mock-profile",
        default=None,
        choices=MOCK_PROFILES,
        help="Mock data profile to use when --mock is enabled.",
    )
    parser.add_argument(
        "--redaction-profile",
        default=None,
        choices=REDACTION_PROFILES,
        help="How much redaction to apply to handoff-facing artifacts.",
    )
    _add_json_output_option(parser)


def _require_choice(name: str, value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}; got {value!r}.")
    return value


def _add_json_output_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )


def _json_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _settings_payload(*, path: Path, settings: Any) -> dict[str, object]:
    return {
        "schema_version": 1,
        "ok": True,
        "settings_path": str(path),
        "output_root": str(settings.output_root),
        "redaction_profile": settings.redaction_profile,
        "mock_profile": settings.mock_profile,
    }


def _settings_path() -> Path:
    return settings_path()


def _capture_payload(run_dir: Path) -> dict[str, object]:
    result = _read_json_object(run_dir / "result.json")
    payload: dict[str, object] = {
        "schema_version": 1,
        "ok": True,
        "run_dir": str(run_dir),
        "runDir": str(run_dir),
    }
    if result:
        payload.update(result)
    payload["ok"] = True
    payload["run_dir"] = str(run_dir)
    payload["runDir"] = str(run_dir)
    return payload


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _print_items_text(payload: dict[str, object]) -> None:
    print("OK")
    print(f"item_count: {payload.get('item_count', 0)}")
    items = payload.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        print(
            "- "
            + f"{item.get('item_id', '')} "
            + f"{item.get('latest_update_status', '')} "
            + f"{item.get('updated_at_utc', '')}"
        )
