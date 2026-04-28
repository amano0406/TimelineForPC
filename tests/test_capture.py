from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from timeline_for_pc.cli import main
from timeline_for_pc.doctor import format_doctor_result
from timeline_for_pc.doctor import run_doctor


def test_mock_capture_creates_expected_files(tmp_path: Path) -> None:
    exit_code = main(
        [
            "capture",
            "--mock",
            "--mock-profile",
            "baseline",
            "--output-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0

    run_dirs = sorted(
        (path for path in tmp_path.iterdir() if path.is_dir()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    expected_files = {
        "request.json",
        "status.json",
        "result.json",
        "manifest.json",
        "snapshot.json",
        "snapshot_redacted.json",
        "report.md",
    }
    assert expected_files.issubset({path.name for path in run_dir.iterdir()})
    export_files = sorted((run_dir / "export").iterdir())
    assert len(export_files) == 1
    assert export_files[0].name == "202604200000.md"

    snapshot = json.loads((run_dir / "snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["capture_mode"] == "mock"
    assert snapshot["os"]["product_name"] == "Windows 10 Pro"
    redacted_snapshot = json.loads((run_dir / "snapshot_redacted.json").read_text(encoding="utf-8"))
    assert redacted_snapshot["host"]["name"] == "[redacted-host]"
    assert redacted_snapshot["applications"][0]["publisher"] is None
    assert redacted_snapshot["details"]["platform"]["computer_name"] == "[redacted-host]"

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "11th Gen Intel(R) Core(TM) i7-11700" in report
    assert "Captured at:" in report
    assert "## Network / WSL" in report
    assert "## CPU / Memory / GPU" in report
    assert "PC name:" in report
    assert "Memory layout:" in report
    assert "Running WSL distros:" in report
    assert "## 差分" not in report
    assert "## ネットワーク / WSL" not in report


def test_second_mock_capture_keeps_same_minimal_output_shape(tmp_path: Path) -> None:
    assert main(["capture", "--mock", "--mock-profile", "baseline", "--output-root", str(tmp_path)]) == 0
    assert main(["capture", "--mock", "--mock-profile", "upgraded", "--output-root", str(tmp_path)]) == 0

    run_dirs = sorted(
        (path for path in tmp_path.iterdir() if path.is_dir()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    second_run = run_dirs[-1]

    assert not (second_run / "diff.json").exists()

    report = (second_run / "report.md").read_text(encoding="utf-8")
    assert "## 差分" not in report
    assert "Docker Desktop 4.41.0" not in report
    assert "## Storage" in report
    assert "Total physical capacity:" in report
    assert "total /" in report

    result = json.loads((second_run / "result.json").read_text(encoding="utf-8"))
    assert result["export_markdown_path"].endswith("202605010000.md")
    assert "diff_path" not in result
    assert "previous_snapshot_path" not in result


def test_smoke_test_validates_mock_output(tmp_path: Path, capsys: Any) -> None:
    exit_code = main(["smoke-test", "--output-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "OK"

    run_dirs = sorted(
        (path for path in tmp_path.iterdir() if path.is_dir()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert not (run_dir / "diff.json").exists()

    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    export_path = Path(result["export_markdown_path"])
    assert export_path.exists()
    assert export_path.name == "202604200000.md"

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    export_markdown = export_path.read_text(encoding="utf-8")
    assert report == export_markdown
    assert "## System" in export_markdown
    assert "## Network / WSL" in export_markdown
    assert "## 差分" not in export_markdown


def test_doctor_reports_ok_when_required_tools_exist(tmp_path: Path) -> None:
    def resolve_tool(name: str) -> str | None:
        tools = {
            "powershell.exe": "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            "cmd.exe": "C:/Windows/System32/cmd.exe",
            "wsl.exe": "C:/Windows/System32/wsl.exe",
        }
        return tools.get(name)

    def command_succeeds(args: list[str]) -> bool:
        return args[-1] == "nvidia-smi"

    result = run_doctor(
        output_root=tmp_path / "TimelineForPC",
        tool_resolver=resolve_tool,
        command_checker=command_succeeds,
        python_version=(3, 11, 9),
    )
    lines = format_doctor_result(result)

    assert result.ok
    assert lines[0] == "OK"
    assert any("[OK] PowerShell" in line for line in lines)
    assert any("[OK] nvidia-smi" in line for line in lines)


def test_doctor_reports_ng_when_required_tools_are_missing(tmp_path: Path) -> None:
    result = run_doctor(
        output_root=tmp_path / "TimelineForPC",
        tool_resolver=lambda _name: None,
        command_checker=lambda _args: False,
        python_version=(3, 10, 0),
    )
    lines = format_doctor_result(result)

    assert not result.ok
    assert lines[0] == "NG"
    assert any("[NG] Python" in line for line in lines)
    assert any("[NG] PowerShell" in line for line in lines)
