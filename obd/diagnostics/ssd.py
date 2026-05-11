import re
import subprocess
from typing import Any, Dict, Iterable, List, Mapping

import wmi
from wmi import x_wmi

KNOWN_SSD_ATTRIBUTES = {
    0x09: "Power-on Hours",
    0x0C: "Power Cycle Count",
    0xE8: "Power Cycle Count",
    0xE9: "Media Wearout Indicator / Total Writes",
    0xF1: "Total Host Writes",
    0xF2: "Total Host Reads",
    0xF9: "Total NAND Writes",
}


def _describe_ssd_metric(attr_id: int, raw_value: int) -> str:
    if attr_id == 0x09:
        days = raw_value / 24
        return f"Approx age: {raw_value}h ({days:.1f} days)"
    if attr_id in (0x0C, 0xE8):
        return f"Power cycles: {raw_value}"
    if attr_id == 0xE9:
        if raw_value <= 100:
            return f"Media wear: {raw_value}%"
        return f"Media wear raw: {raw_value}"
    if attr_id in (0xF1, 0xF2, 0xF9):
        tbw = raw_value * 512 / (1024 ** 4)
        if tbw >= 0.01:
            return f"Estimated TB: {tbw:.2f} TB (assuming 512-byte sectors)"
        return f"Raw value: {raw_value}"
    return ""


def _normalize_vendor_specific(data: Any) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, Iterable):
        return bytes(int(value) for value in data)
    raise ValueError("Unsupported vendor-specific SMART payload")


def _parse_smart_attributes(vendor_specific: Any) -> Mapping[int, int]:
    raw = _normalize_vendor_specific(vendor_specific)
    attributes: Dict[int, int] = {}

    for offset in range(0, len(raw) - 12 + 1, 12):
        attr_id = raw[offset]
        if attr_id == 0:
            continue
        raw_value = int.from_bytes(raw[offset + 4 : offset + 10], "little")
        attributes[attr_id] = raw_value

    return attributes


def _parse_powershell_output(output: str) -> List[Dict[str, str]]:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    if any(
        ":" in line and not line.startswith("----")
        for line in lines[2:]
    ):
        items: List[Dict[str, str]] = []
        current: Dict[str, str] = {}
        for line in lines:
            if ":" not in line:
                if current:
                    items.append(current)
                    current = {}
                continue
            key, value = line.split(":", 1)
            current[key.strip()] = value.strip()
        if current:
            items.append(current)
        return items

    if len(lines) < 2:
        return []

    header, separator = lines[0], lines[1]
    columns: List[Dict[str, int]] = []
    for match in re.finditer(r"-+", separator):
        start, end = match.span()
        columns.append({"name": header[start:end].strip(), "start": start, "end": end})

    if not columns:
        return []

    items: List[Dict[str, str]] = []
    for row in lines[2:]:
        entry: Dict[str, str] = {}
        for column in columns:
            start = column["start"]
            end = column["end"]
            entry[column["name"]] = row[start:end].strip() if len(row) > start else ""
        items.append(entry)

    return items


def _get_ssd_age_and_tbw_from_powershell() -> List[Dict[str, Any]]:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            'Get-PhysicalDisk | Get-StorageReliabilityCounter | Select-Object Number,DeviceId,MediaType,PowerOnHours,PercentRemainingLife,RemainingLife,LifeRemaining,AverageEraseCount,WearIndicator,Usage,OperationalStatus | Out-String -Width 4096',
        ],
        capture_output=True,
        text=True,
        shell=False,
        timeout=20,
    )
    if completed.returncode != 0:
        return []

    parsed = _parse_powershell_output((completed.stdout or "").strip())
    if not parsed:
        return []

    def describe_powershell_metric(key: str, value: str) -> str:
        normalized = value.replace("%", "").strip()
        if not normalized:
            return ""
        try:
            number = float(normalized)
        except ValueError:
            return ""

        lower_key = key.lower()
        if "percent" in lower_key or "life" in lower_key:
            return f"Health remaining: {number:.0f}%"
        if "wear" in lower_key:
            return f"Wear indicator: {number:.0f}"
        if "erase" in lower_key:
            return f"Average erase count: {number:.0f}"
        if "usage" in lower_key:
            return f"Usage: {number:.0f}"
        return ""

    results: List[Dict[str, Any]] = []
    for index, item in enumerate(parsed, start=1):
        metrics: Dict[str, str] = {}
        derived: Dict[str, str] = {}
        for key, value in item.items():
            metrics[key] = value
            description = describe_powershell_metric(key, value)
            if description:
                derived[key] = description

        results.append(
            {
                "instance_name": item.get("DeviceId", item.get("Number", f"PhysicalDisk {index}")),
                "metrics": metrics,
                "derived": derived,
                "raw_attributes": item,
            }
        )

    return results


def get_ssd_age_and_tbw() -> List[Dict[str, Any]]:
    results = []

    try:
        visitor = wmi.WMI(namespace="root\\wmi")
        records = visitor.MSStorageDriver_FailurePredictData()
    except x_wmi:
        records = []
    except Exception:
        records = []

    for record in records:
        try:
            attributes = _parse_smart_attributes(record.VendorSpecific)
        except Exception:
            attributes = {}

        metrics: Dict[str, Any] = {}
        derived: Dict[str, str] = {}
        for attr_id, raw_value in attributes.items():
            if attr_id not in KNOWN_SSD_ATTRIBUTES:
                continue
            label = KNOWN_SSD_ATTRIBUTES[attr_id]
            metrics[label] = raw_value
            description = _describe_ssd_metric(attr_id, raw_value)
            if description:
                derived[label] = description

        results.append(
            {
                "instance_name": getattr(record, "InstanceName", "unknown"),
                "metrics": metrics,
                "derived": derived,
                "raw_attributes": attributes,
            }
        )

    if any(item["metrics"] for item in results):
        return results

    return _get_ssd_age_and_tbw_from_powershell()
