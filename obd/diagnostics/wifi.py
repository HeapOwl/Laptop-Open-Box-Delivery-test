import ssl
import time
import urllib.request
from typing import Tuple

DOWNLOAD_TEST_URL = "https://nbg1-speed.hetzner.com/100MB.bin"


def detect_wifi_standard(output: str) -> Tuple[str, str]:
    normalized = output.lower()
    if "802.11ax" in normalized or "ax" in normalized:
        return "WiFi 6 (802.11ax)", "Excellent"
    if "802.11ac" in normalized:
        return "WiFi 5 (802.11ac)", "Good"
    if "802.11n" in normalized:
        return "WiFi 4 (802.11n)", "Basic"
    return "Unknown or legacy adapter", "Unknown"


def measure_download_speed(
    url: str = DOWNLOAD_TEST_URL,
    bytes_to_read: int = 5 * 1024 * 1024,
    timeout: int = 30,
) -> float:
    ssl_context = ssl._create_unverified_context()
    start = time.perf_counter()
    with urllib.request.urlopen(url, context=ssl_context, timeout=timeout) as response:
        response.read(bytes_to_read)
    elapsed = max(time.perf_counter() - start, 1e-6)
    return bytes_to_read * 8 / (1024 ** 2) / elapsed
