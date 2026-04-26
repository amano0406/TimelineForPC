from __future__ import annotations

from typing import Any

from timeline_for_pc.models import Snapshot


CHASSIS_LABELS = {
    3: "Desktop",
    4: "Low Profile Desktop",
    6: "Mini Tower",
    7: "Tower",
    13: "All-in-One",
    23: "Rack Mount",
}


def render_report(snapshot: Snapshot) -> str:
    details = snapshot.details
    platform = _dict(details, "platform")
    bios = _dict(details, "bios")
    chassis = _dict(details, "chassis")
    os_details = _dict(details, "os_details")
    memory_details = _dict(details, "memory_details")
    display = _dict(details, "display")
    storage_details = _dict(details, "storage_details")
    network = _dict(details, "network")
    wsl = _dict(details, "wsl")
    gpu_runtime = _list(details, "gpu_runtime")

    lines = [
        "# TimelineForPC",
        "",
        f"Captured at: {snapshot.captured_at_utc}",
        "",
        "## System",
        f"- PC name: {_or(platform.get('computer_name'), snapshot.host.name, 'unknown')}",
        f"- Manufacturer / model: {_join_non_empty(snapshot.host.manufacturer, snapshot.host.model, separator=' / ')}",
        f"- Motherboard: {_join_non_empty(snapshot.host.motherboard.manufacturer if snapshot.host.motherboard else None, snapshot.host.motherboard.product if snapshot.host.motherboard else None)}",
        f"- BIOS: {_join_non_empty(bios.get('vendor'), bios.get('version'), separator=' / ')}",
        f"- Chassis: {_chassis_label(chassis)}",
        "",
        "## OS",
        f"- Windows: {_join_non_empty(snapshot.os.product_name, 'Build ' + str(snapshot.os.build_number) if snapshot.os.build_number else None, _normalize_architecture(snapshot.os.architecture), separator=' / ')}",
        f"- Installed at: {_or(os_details.get('install_date_local'), 'unknown')}",
        f"- Last boot: {_or(os_details.get('last_boot_local'), 'unknown')}",
        "",
        "## CPU / Memory / GPU",
        f"- CPU: {_cpu_label(snapshot)}",
        f"- RAM: {_format_bytes(snapshot.host.total_memory_bytes)}",
        f"- Memory layout: {_memory_modules_label(memory_details)}",
        f"- Memory speed: {_or(_optional_mt_s(memory_details.get('configured_speed_mt_s')), 'unknown')}",
        f"- GPU: {_gpu_summary(snapshot, gpu_runtime)}",
        "",
        "## Display",
        f"- Monitor: {_or(display.get('monitor_name'), 'unknown')}",
        f"- Output: {_join_non_empty(display.get('resolution'), _optional_hz(display.get('refresh_hz')), separator=' / ')}",
        "",
        "## Storage",
    ]

    for disk in snapshot.physical_disks:
        disk_bits = [disk.name]
        if disk.bus_type or disk.media_type:
            disk_bits.append(_join_non_empty(disk.bus_type, disk.media_type))
        if disk.size_bytes is not None:
            disk_bits.append(_format_bytes(disk.size_bytes))
        lines.append(f"- Physical disk: {' / '.join(bit for bit in disk_bits if bit)}")
    if storage_details.get("physical_total_bytes") is not None:
        lines.append(f"- Total physical capacity: {_format_bytes(storage_details.get('physical_total_bytes'))}")
    for volume in snapshot.volumes:
        lines.append(f"- {volume.name}: {_volume_summary(volume.total_bytes, volume.free_bytes)}")

    lines.extend(
        [
            "",
            "## Network / WSL",
        ]
    )

    adapters = _list(network, "adapters")
    for adapter in adapters[:8]:
        if not isinstance(adapter, dict):
            continue
        prefix = {
            "physical": "Ethernet NIC",
            "wifi": "Wi-Fi",
            "virtual": "Virtual NIC",
        }.get(adapter.get("kind"), "NIC")
        summary = _join_non_empty(
            adapter.get("description"),
            adapter.get("link_speed"),
            separator=" / ",
        )
        lines.append(f"- {prefix}: {_or(summary, adapter.get('name'), 'unknown')}")

    wsl_summary = _join_non_empty(
        _optional_pair("Default distro", wsl.get("default_distribution")),
        _optional_pair("Default version", wsl.get("default_version")),
        separator=", ",
    )
    if wsl_summary:
        lines.append(f"- WSL: {wsl_summary}")
    running = _list(wsl, "running_distributions")
    if running:
        lines.append(f"- Running WSL distros: {', '.join(str(item) for item in running)}")
    if wsl.get("linux_release"):
        lines.append(f"- Linux release: {wsl.get('linux_release')}")
    if wsl.get("kernel"):
        lines.append(f"- WSL kernel: {wsl.get('kernel')}")

    lines.append("")
    return "\n".join(lines)


def _cpu_label(snapshot: Snapshot) -> str:
    if not snapshot.processors:
        return "Unknown CPU"
    processor = snapshot.processors[0]
    parts = [processor.name]
    if processor.cores is not None and processor.logical_processors is not None:
        parts.append(f"{processor.cores} cores / {processor.logical_processors} threads")
    return " / ".join(parts)


def _gpu_summary(snapshot: Snapshot, gpu_runtime: list[Any]) -> str:
    if gpu_runtime and isinstance(gpu_runtime[0], dict):
        runtime = gpu_runtime[0]
        if runtime.get("name"):
            parts = [str(runtime.get("name"))]
            if runtime.get("vram_total_mib") is not None:
                parts.append(f"VRAM {_format_mib(runtime.get('vram_total_mib'))}")
            if runtime.get("driver_version_display"):
                parts.append(f"driver {runtime.get('driver_version_display')}")
            if runtime.get("temperature_c") is not None:
                parts.append(f"{runtime.get('temperature_c')}°C")
            return " / ".join(parts)
    if snapshot.gpus:
        gpu = snapshot.gpus[0]
        return _join_non_empty(gpu.name, f"driver {gpu.driver_version}" if gpu.driver_version else None, separator=" / ")
    return "Unknown GPU"


def _memory_modules_label(memory_details: dict[str, Any]) -> str:
    modules = [item for item in _list(memory_details, "modules") if isinstance(item, dict)]
    if not modules:
        return "unknown"
    size_labels = [_format_bytes(item.get("size_bytes")) for item in modules]
    part_numbers = [str(item.get("part_number")) for item in modules if item.get("part_number")]
    label = " + ".join(size_labels)
    if part_numbers:
        label = f"{label} / {' / '.join(part_numbers[:2])}"
    return label


def _format_bytes(value: Any) -> str:
    if value is None:
        return "unknown"
    size = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit in {"GiB", "TiB"}:
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def _format_mib(value: Any) -> str:
    if value is None:
        return "unknown"
    try:
        gib = float(value) / 1024.0
        return f"{gib:.1f} GiB"
    except (TypeError, ValueError):
        return str(value)


def _optional_pair(label: str, value: Any) -> str | None:
    if value is None or value == "":
        return None
    return f"{label}: {value}"


def _optional_hz(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return f"{value} Hz"


def _optional_mt_s(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return f"{value} MT/s"


def _chassis_label(chassis: dict[str, Any]) -> str:
    types = [item for item in _list(chassis, "types") if isinstance(item, int)]
    if not types:
        return "unknown"
    primary = types[0]
    base = CHASSIS_LABELS.get(primary, f"Type {primary}")
    return f"{base}-class (ChassisTypes={{{', '.join(str(item) for item in types)}}})"


def _volume_summary(total_bytes: Any, free_bytes: Any) -> str:
    return f"{_format_bytes(total_bytes)} total / {_format_bytes(free_bytes)} free"


def _normalize_architecture(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    replacements = {
        "64 ビット": "64-bit",
        "32 ビット": "32-bit",
        "64-bit": "64-bit",
        "32-bit": "32-bit",
    }
    return replacements.get(text, text)


def _join_non_empty(*parts: Any, separator: str = " ") -> str:
    values = [str(part) for part in parts if part not in (None, "")]
    return separator.join(values) if values else "unknown"


def _or(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _list(container: dict[str, Any], key: str) -> list[Any]:
    value = container.get(key)
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if value is not None:
        return [value]
    return []
