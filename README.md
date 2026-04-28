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

## Usage

Create one snapshot:

```bash
python -m timeline_for_pc capture
```

Write to a custom output root:

```bash
python -m timeline_for_pc capture --output-root /mnt/c/Codex/workspaces/TimelineForPC
```

Choose a redaction profile for handoff-facing artifacts:

```bash
python -m timeline_for_pc capture --redaction-profile llm_safe
```

Run deterministic mock captures:

```bash
python -m timeline_for_pc capture --mock --mock-profile baseline
python -m timeline_for_pc capture --mock --mock-profile upgraded
```

Run a quick output-contract check:

```bash
timeline-for-pc smoke-test
```

Run the same check with live Windows collection:

```bash
timeline-for-pc smoke-test --live
```

Check whether this PC has the required local tools for live collection:

```bash
timeline-for-pc doctor
```

Create local persistent settings:

```bash
timeline-for-pc settings init
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

```bash
timeline-for-pc settings init
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

Optional checks such as `nvidia-smi` and `wsl.exe` may show `WARN`. A warning
means that the main report can still be created, but that optional detail will
be skipped.
