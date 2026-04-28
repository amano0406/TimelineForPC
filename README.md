# TimelineForPC

`TimelineForPC` is a local-first CLI for capturing the current state of a Windows PC and writing one readable markdown report.

The first MVP stays intentionally small:

- CLI only
- Python 3.11+
- no production dependencies beyond the standard library
- mock mode for tests and offline validation

## What It Produces

Each capture writes one run directory with:

- `request.json`
- `status.json`
- `result.json`
- `manifest.json`
- `snapshot.json`
- `snapshot_redacted.json`
- `report.md`
- `export/YYYYMMDDHHMM.md`

The default output root is:

- Windows: `C:\Codex\workspaces\TimelineForPC`
- WSL: `/mnt/c/Codex/workspaces/TimelineForPC`

This product currently preserves that existing root instead of the shared
Timeline baseline of `data/output/runs/timeline-for-pc/`. Moving the default
root would be an output contract change and needs an explicit decision.

## What It Captures

Current snapshot coverage:

- Windows product name, version, build number, architecture
- system manufacturer and model
- BIOS and chassis details
- Windows install/boot times and hotfix IDs
- CPU summary
- memory modules, slots, maximum capacity, and current recognized speed
- GPU names, driver versions, and NVIDIA runtime stats when available
- display summary
- physical disks
- filesystem volumes
- network adapter summary
- WSL summary
- audio devices and hypervisor presence
- installed apps from standard uninstall registry paths

## Environment Requirements

This product is a Windows host-inspection CLI. The standard entry point is
PowerShell on the Windows host. WSL can still be used as a backdoor for
development or emergency operation, but it is not the primary user path.

It intentionally runs directly on the Windows host instead of Docker, because
the main job is to read the actual PC state.

Required for normal live capture:

| Item | Reason |
| --- | --- |
| Windows host | The product captures Windows PC state. |
| Python 3.11+ | Runs the CLI. |
| PowerShell | Runs the local Windows collection script. |
| CIM / WMI | Reads OS, CPU, RAM, BIOS, GPU, disk, audio, and system details. |
| Writable output root | Stores run folders and `export/YYYYMMDDHHMM.md`. |

Optional:

| Item | Reason if available |
| --- | --- |
| `cmd.exe` | Helps run Windows command-line tools from the collector. |
| `nvidia-smi` | Adds NVIDIA runtime details such as VRAM, temperature, power, VBIOS, and PCIe link. |
| `wsl.exe` | Adds WSL distribution, Linux release, and WSL kernel details. WSL is also a non-primary backdoor entry point. |
| `settings.json` | Stores local defaults for output root, redaction profile, and mock profile. |
| `pytest` | Runs the development test suite. Not needed for normal capture. |

Not required:

| Item | Reason |
| --- | --- |
| Docker Desktop | Docker would see a container, not the full Windows host. |
| npm / Node.js | The product has no JavaScript runtime dependency. |
| Web UI / browser | The product is CLI-only. |
| External API keys | The product does not call cloud APIs. |
| Network access | Capture uses local machine information. |

## Usage

Windows PowerShell is the front door. Run commands from `C:\apps\TimelineForPC`.

Check this PC before capture:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 doctor
```

Create one live Windows snapshot:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 capture
```

Write to a custom output root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 capture --output-root C:\Codex\workspaces\TimelineForPC
```

Choose a redaction profile for handoff-facing artifacts:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 capture --redaction-profile llm_safe
```

Run deterministic mock captures:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 capture --mock --mock-profile baseline
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 capture --mock --mock-profile upgraded
```

Run a quick output-contract check:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 smoke-test
```

Run the same check with live Windows collection:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 smoke-test --live
```

Check whether this PC has the required and optional local tools for live collection:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 doctor
```

Create local persistent settings:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 settings init
```

If the Python package is already installed, the console command still works:

```powershell
timeline-for-pc doctor
```

WSL backdoor usage:

```bash
cd /mnt/c/apps/TimelineForPC
PYTHONPATH=src python -m timeline_for_pc doctor
```

## Output Shape

`report.md` is the main human-readable record inside the run directory.

- a compact main-info summary
- OS / BIOS / CPU / memory / GPU / display / storage / network / WSL / audio / virtualization / installed apps sections
- current machine state only

`export/YYYYMMDDHHMM.md` is the final deliverable for sharing or handing to an LLM.

It keeps the report as one markdown file instead of splitting it into timeline / handoff / ZIP artifacts.
The product responsibility is limited to exporting the current machine state.

`snapshot_redacted.json` and `export/YYYYMMDDHHMM.md` use the selected redaction profile.

Current profiles:

- `llm_safe`
  - redacts the host name
  - removes app publishers from the redacted snapshot
- `none`
  - keeps the structured redacted snapshot unmodified

## Settings

Persistent local settings live at the product root:

- `settings.example.json` is tracked by Git.
- `settings.json` is local-only and ignored by Git.

Initialize local settings:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\timeline-for-pc.ps1 settings init
```

`settings init` creates `settings.json` only when it does not already exist. It
does not overwrite local settings.

Supported settings:

- `output_root`: default run output directory when `--output-root` is omitted
- `redaction_profile`: default redaction profile when `--redaction-profile` is omitted
- `mock_profile`: default mock profile when `--mock-profile` is omitted

CLI arguments still take priority over `settings.json`.

## Development

Full test execution requires `pytest`. The project declares it in the optional
`test` extra:

```bash
python -m pip install -e ".[test]"
```

Then run tests:

```bash
python -m pytest
```

Some local operator environments may not have `pip` or `pytest` installed. In
that case, use the deterministic mock capture and bytecode compilation as
alternate checks until the test dependency is available:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m timeline_for_pc capture --mock --mock-profile baseline --output-root /tmp/timeline-for-pc-smoke
PYTHONPYCACHEPREFIX=/tmp/timeline-for-pc-pycache python -m compileall -q src tests
```

Mock mode is the test baseline and should stay stable.

## Smoke Test

`smoke-test` is the user-facing health check for this CLI. It runs one capture,
checks that the expected files exist, verifies that exactly one
`export/YYYYMMDDHHMM.md` file was created, and confirms that the markdown report
uses the current English output shape without diff artifacts.

The first line is the machine-readable result:

- `OK` means the output contract is valid.
- `NG` means the command found one or more output problems.

By default, `smoke-test` uses deterministic mock data so it is safe and stable.
Use `--live` when you want to verify the real Windows collection path.

## Doctor

`doctor` is the preflight check for live collection. It does not collect or
export PC information. It only checks whether the local command-line tools and
output directory needed by `capture` are available.

The first line is the machine-readable result:

- `OK` means required checks passed.
- `NG` means at least one required check failed.

Each detail line includes `[required]` or `[optional]`. Optional checks such as
`nvidia-smi` and `wsl.exe` may show `WARN`. A warning means that the main report
can still be created, but that optional detail will be skipped.
