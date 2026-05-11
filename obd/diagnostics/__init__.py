"""Diagnostics helpers for the Laptop Open Box Delivery Checker."""

from .common import get_system_identity, is_windows, run_shell_command
from .ssd import get_ssd_age_and_tbw
from .wifi import detect_wifi_standard, measure_download_speed

__all__ = [
    "get_system_identity",
    "is_windows",
    "run_shell_command",
    "detect_wifi_standard",
    "measure_download_speed",
    "get_ssd_age_and_tbw",
]
