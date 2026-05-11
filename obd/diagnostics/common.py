import platform
import subprocess
from typing import Dict

import wmi
from wmi import x_wmi


def is_windows() -> bool:
    return platform.system() == "Windows"


def run_shell_command(command: str, timeout: int = 20) -> str:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.stdout.strip() or completed.stderr.strip()
    except subprocess.SubprocessError as exc:
        return str(exc)


def _parse_wmic_output(output: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip().lower()] = value.strip()
    return result


def _extract_single_value(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]

    for line in lines:
        if "=" in line:
            _, _, value = line.partition("=")
            if value.strip():
                return value.strip()
    for line in lines:
        if not line.lower().startswith("serial") and not line.lower().startswith("manufacturer"):
            return line
    return lines[-1]


def _probe_system_identity_via_wmic() -> Dict[str, str]:
    result = {
        "manufacturer": "",
        "model": "",
        "serial_number": "",
    }

    system_output = run_shell_command(
        "wmic computersystem get manufacturer,model /format:list"
    )
    bios_output = run_shell_command("wmic bios get serialnumber /format:list")
    product_output = run_shell_command("wmic csproduct get identifyingnumber /format:list")

    parsed_system = _parse_wmic_output(system_output)
    parsed_bios = _parse_wmic_output(bios_output)
    parsed_product = _parse_wmic_output(product_output)

    result["manufacturer"] = parsed_system.get("manufacturer", "")
    result["model"] = parsed_system.get("model", "")
    result["serial_number"] = (
        parsed_bios.get("serialnumber", "")
        or parsed_product.get("identifyingnumber", "")
        or _extract_single_value(bios_output)
        or _extract_single_value(product_output)
    )
    return result


def _probe_system_identity_via_powershell() -> Dict[str, str]:
    result = {
        "manufacturer": "",
        "model": "",
        "serial_number": "",
    }
    manufacturer = run_shell_command(
        "powershell -NoProfile -Command \"(Get-CimInstance Win32_ComputerSystem).Manufacturer\""
    )
    model = run_shell_command(
        "powershell -NoProfile -Command \"(Get-CimInstance Win32_ComputerSystem).Model\""
    )
    serial_number = run_shell_command(
        "powershell -NoProfile -Command \"(Get-CimInstance Win32_BIOS).SerialNumber\""
    )
    result["manufacturer"] = manufacturer.strip()
    result["model"] = model.strip()
    result["serial_number"] = serial_number.strip()
    return result


def get_system_identity() -> Dict[str, str]:
    identity = {
        "manufacturer": "Unknown",
        "model": "Unknown",
        "serial_number": "Unknown",
    }

    try:
        visitor = wmi.WMI()
        system = next(visitor.Win32_ComputerSystem(), None)
        bios = next(visitor.Win32_BIOS(), None)
        if system is not None:
            identity["manufacturer"] = getattr(system, "Manufacturer", identity["manufacturer"])
            identity["model"] = getattr(system, "Model", identity["model"])
        if bios is not None:
            identity["serial_number"] = getattr(bios, "SerialNumber", identity["serial_number"])
    except Exception:
        pass

    if identity["serial_number"] == "Unknown" or not identity["serial_number"]:
        wmic_identity = _probe_system_identity_via_wmic()
        identity["manufacturer"] = wmic_identity.get("manufacturer") or identity["manufacturer"]
        identity["model"] = wmic_identity.get("model") or identity["model"]
        identity["serial_number"] = wmic_identity.get("serial_number") or identity["serial_number"]

    if identity["serial_number"] == "Unknown" or not identity["serial_number"]:
        ps_identity = _probe_system_identity_via_powershell()
        identity["manufacturer"] = ps_identity.get("manufacturer") or identity["manufacturer"]
        identity["model"] = ps_identity.get("model") or identity["model"]
        identity["serial_number"] = ps_identity.get("serial_number") or identity["serial_number"]

    return identity
