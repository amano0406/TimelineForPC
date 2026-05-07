from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from timeline_for_pc.runner import default_output_root


SETTINGS_EXAMPLE_FILENAME = "settings.example.json"
SETTINGS_FILENAME = "settings.json"


class SettingsError(RuntimeError):
    """Raised when local settings cannot be read or validated."""


@dataclass(frozen=True)
class AppSettings:
    output_root: Path
    redaction_profile: str
    mock_profile: str


@dataclass(frozen=True)
class SettingsInitResult:
    path: Path
    created: bool


@dataclass(frozen=True)
class SettingsSaveResult:
    path: Path
    settings: AppSettings


def product_root() -> Path:
    return Path(__file__).resolve().parents[2]


def settings_example_path(*, root: Path | None = None) -> Path:
    return (root or product_root()) / SETTINGS_EXAMPLE_FILENAME


def settings_path(*, root: Path | None = None) -> Path:
    return (root or product_root()) / SETTINGS_FILENAME


def default_settings() -> AppSettings:
    return AppSettings(
        output_root=default_output_root(),
        redaction_profile="llm_safe",
        mock_profile="baseline",
    )


def load_settings(*, root: Path | None = None) -> AppSettings:
    path = settings_path(root=root)
    if not path.exists():
        return default_settings()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SettingsError(f"Settings file must contain a JSON object: {path}")

    defaults = default_settings()
    return AppSettings(
        output_root=_path_from_setting(raw.get("output_root"), defaults.output_root),
        redaction_profile=_string_from_setting(raw.get("redaction_profile"), defaults.redaction_profile),
        mock_profile=_string_from_setting(raw.get("mock_profile"), defaults.mock_profile),
    )


def init_settings(*, root: Path | None = None) -> SettingsInitResult:
    target = settings_path(root=root)
    if target.exists():
        return SettingsInitResult(path=target, created=False)

    source = settings_example_path(root=root)
    if source.exists():
        content = source.read_text(encoding="utf-8")
    else:
        content = _default_settings_json()

    target.write_text(content, encoding="utf-8")
    return SettingsInitResult(path=target, created=True)


def save_settings(
    *,
    output_root: Path,
    redaction_profile: str,
    mock_profile: str,
    root: Path | None = None,
) -> SettingsSaveResult:
    target = settings_path(root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    settings = AppSettings(
        output_root=output_root,
        redaction_profile=redaction_profile,
        mock_profile=mock_profile,
    )
    payload = {
        "schema_version": 1,
        "output_root": str(settings.output_root),
        "redaction_profile": settings.redaction_profile,
        "mock_profile": settings.mock_profile,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return SettingsSaveResult(path=target, settings=settings)


def _default_settings_json() -> str:
    settings = default_settings()
    payload = {
        "schema_version": 1,
        "output_root": str(settings.output_root),
        "redaction_profile": settings.redaction_profile,
        "mock_profile": settings.mock_profile,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _path_from_setting(value: Any, default: Path) -> Path:
    if value in (None, ""):
        return default
    return _normalize_path(str(value).strip())


def _normalize_path(value: str) -> Path:
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", value)
    if os.name != "nt" and match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path("/mnt") / drive / rest
    return Path(value)


def _string_from_setting(value: Any, default: str) -> str:
    if value in (None, ""):
        return default
    return str(value).strip()
