import ctypes
import platform
import time
from typing import Any, Callable, Dict, List

import numpy as np
import psutil
import sounddevice as sd
import wmi
from PyQt6.QtWidgets import QApplication

from .camera_recorder import CameraRecorder
from obd.diagnostics import (
    detect_wifi_standard,
    get_ssd_age_and_tbw,
    get_system_identity,
    is_windows,
    measure_download_speed,
    run_shell_command,
)


class DiagnosticRunner:
    def __init__(self, log_callback: Callable[[str], None], window_opener: Callable[..., None] = None) -> None:
        self.log = log_callback
        self.window_opener = window_opener

    def require_windows(self) -> bool:
        if not is_windows():
            self.log("This tool is designed for Windows environments only.")
            return False
        return True

    def startup_report(self) -> None:
        identity = get_system_identity()
        self.log("===== STARTUP REPORT =====")
        if identity:
            self.log(f"Manufacturer: {identity.get('manufacturer', 'Unknown')}")
            self.log(f"Model: {identity.get('model', 'Unknown')}")
            self.log(f"Serial Number: {identity.get('serial_number', 'Unknown')}")
        else:
            self.log("System identity unavailable via WMI.")
        self.log("===== STARTUP REPORT COMPLETE =====")

    def open_box_summary(self) -> None:
        if not self.require_windows():
            return

        self.log("===== OPEN BOX SUMMARY =====")
        self.startup_report()
        self.system_info()
        self.refresh_rate()
        self.battery_wear()
        self.ssd_health()
        self.wifi6_detection()
        self.log("===== OPEN BOX SUMMARY COMPLETE =====")

    def system_info(self) -> None:
        self.log("===== System Info =====")
        self.log(f"OS: {platform.system()} {platform.release()}")
        self.log(f"Machine: {platform.machine()}")
        self.log(f"Processor: {platform.processor()}")
        self.log(f"Python: {platform.python_version()}")
        self.log(
            f"CPU cores: {psutil.cpu_count(logical=False)} physical / {psutil.cpu_count(logical=True)} logical"
        )
        self.log(f"RAM: {round(psutil.virtual_memory().total / (1024 ** 3), 2)} GB")
        self.log(f"CPU usage: {psutil.cpu_percent(interval=0.5)}%")
        try:
            visitor = wmi.WMI()
            for gpu in visitor.Win32_VideoController():
                self.log(f"GPU: {gpu.Name}")
        except Exception as error:
            self.log(f"GPU detection error: {error}")
        self.log("=======================")

    def refresh_rate(self) -> None:
        if not self.require_windows():
            return

        self.log("===== Display Info =====")

        class DEVMODE(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong),
                ("dmOrientation", ctypes.c_short),
                ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short),
                ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short),
                ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short),
                ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong),
                ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong),
            ]

        devmode = DEVMODE()
        devmode.dmSize = ctypes.sizeof(DEVMODE)
        ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode))
        self.log(f"Resolution: {devmode.dmPelsWidth} x {devmode.dmPelsHeight}")
        self.log(f"Refresh rate: {devmode.dmDisplayFrequency} Hz")
        self.log("==========================")

    def stress_test(self) -> None:
        self.log("===== 2-Minute Stress Test =====")
        start = time.perf_counter()
        while time.perf_counter() - start < 120:
            _ = sum(i * i for i in range(500_000))
            self.log(f"CPU usage: {psutil.cpu_percent(interval=0.5)}%")
            QApplication.processEvents()
        self.log("Stress test completed.")
        self.log("===============================")

    def speaker_test(self) -> None:

        self.log("===== Speaker Test =====")

        fs = 44100
        duration = 2.0

        t = np.linspace(0, duration, int(fs * duration), False)

        tone = 0.5 * np.sin(2 * np.pi * 440 * t)

        try:
            # =========================
            # LEFT SPEAKER ONLY
            # =========================
            self.log("Testing LEFT speaker...")

            left_only = np.column_stack((tone, np.zeros_like(tone)))

            sd.play(left_only, fs)
            sd.wait()

            time.sleep(0.5)

            # =========================
            # RIGHT SPEAKER ONLY
            # =========================
            self.log("Testing RIGHT speaker...")

            right_only = np.column_stack((np.zeros_like(tone), tone))

            sd.play(right_only, fs)
            sd.wait()

            time.sleep(0.5)

            # =========================
            # STEREO TEST
            # =========================
            self.log("Testing STEREO output...")

            stereo = np.column_stack((tone, tone))

            sd.play(stereo, fs)
            sd.wait()

            self.log("Speaker test completed.")

            self.log("Check:")
            self.log("- Left sound only from left side")
            self.log("- Right sound only from right side")
            self.log("- Stereo centered properly")

        except Exception as error:

            self.log(f"Speaker test failed: {error}")

        self.log("========================")
    def battery_wear(self) -> None:
        if not self.require_windows():
            return

        self.log("===== Battery Health =====")
        try:
            visitor = wmi.WMI(namespace="root\\WMI")
            full_charge = None
            design_capacity = None
            for item in visitor.BatteryFullChargedCapacity():
                full_charge = item.FullChargedCapacity
            for item in visitor.BatteryStaticData():
                design_capacity = item.DesignedCapacity
            if full_charge and design_capacity:
                wear = 100 - (full_charge / design_capacity * 100)
                self.log(f"Design capacity: {design_capacity} mWh")
                self.log(f"Full charge capacity: {full_charge} mWh")
                self.log(f"Battery wear: {wear:.2f}%")
                status = "Excellent" if wear < 5 else "Good" if wear < 10 else "Used"
                self.log(f"Status: {status}")
            else:
                self.log("Battery data unavailable.")
        except Exception as error:
            self.log(f"Battery health error: {error}")
        self.log("==========================")

    def ssd_health(self) -> None:
        if not self.require_windows():
            return

        self.log("===== SSD Info =====")
        try:
            visitor = wmi.WMI()
            for disk in visitor.Win32_DiskDrive():
                size_gb = round(int(disk.Size) / (1024 ** 3), 2) if disk.Size else 0
                self.log(f"Model: {disk.Model}")
                self.log(f"Interface: {disk.InterfaceType}")
                self.log(f"Size: {size_gb} GB")
                self.log(f"Media type: {getattr(disk, 'MediaType', 'Unknown')}")
                if "SSD" in str(disk.Model).upper():
                    self.log("Drive type: SSD")
                self.log("Status: Detected")
        except Exception as error:
            self.log(f"SSD health error: {error}")
        self.log("====================")

    def ssd_age_tbw_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== SSD AGE / TBW =====")
        try:
            drives = get_ssd_age_and_tbw()
            if not drives:
                self.log(
                    "SSD age/TBW unavailable via WMI or PowerShell. "
                    "This may require administrator privileges; run the tool as admin or check Get-PhysicalDisk | Get-StorageReliabilityCounter manually."
                )
            for drive in drives:
                self.log(f"Drive: {drive['instance_name']}")
                if drive["metrics"]:
                    for label, value in drive["metrics"].items():
                        self.log(f"  {label}: {value}")
                        derived = drive.get("derived", {}).get(label)
                        if derived:
                            self.log(f"    {derived}")
                else:
                    self.log("  No recognized SSD age/TBW SMART attributes.")
        except Exception as error:
            self.log(f"SSD Age/TBW error: {error}")
        self.log("==========================")

    def ram_integrity_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== RAM INTEGRITY TEST =====")
        try:
            total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
            available_mb = round(psutil.virtual_memory().available / (1024 ** 2), 2)
            test_size = min(int(psutil.virtual_memory().available * 0.15), 180 * 1024 ** 2)
            self.log(f"Installed RAM: {total_gb} GB")
            self.log(f"Available RAM: {available_mb} MB")
            self.log(f"Allocating {round(test_size / (1024 ** 2), 1)} MB for a memory verify sweep")
            block = bytearray(test_size)
            for i in range(0, len(block), 4096):
                block[i] = (i // 4096) & 0xFF
            for i in range(0, len(block), 4096):
                expected = (i // 4096) & 0xFF
                if block[i] != expected:
                    raise ValueError(f"Memory mismatch at page {i // 4096}")
            self.log("RAM integrity test passed.")
        except MemoryError as error:
            self.log(f"RAM test memory allocation failed: {error}")
        except Exception as error:
            self.log(f"RAM integrity error: {error}")
        self.log("==============================")

    def display_verification(self) -> None:
        if not self.require_windows():
            return

        self.log("===== Display Verification =====")
        try:
            class DEVMODE(ctypes.Structure):
                _fields_ = [
                    ("dmDeviceName", ctypes.c_wchar * 32),
                    ("dmSpecVersion", ctypes.c_ushort),
                    ("dmDriverVersion", ctypes.c_ushort),
                    ("dmSize", ctypes.c_ushort),
                    ("dmDriverExtra", ctypes.c_ushort),
                    ("dmFields", ctypes.c_ulong),
                    ("dmOrientation", ctypes.c_short),
                    ("dmPaperSize", ctypes.c_short),
                    ("dmPaperLength", ctypes.c_short),
                    ("dmPaperWidth", ctypes.c_short),
                    ("dmScale", ctypes.c_short),
                    ("dmCopies", ctypes.c_short),
                    ("dmDefaultSource", ctypes.c_short),
                    ("dmPrintQuality", ctypes.c_short),
                    ("dmColor", ctypes.c_short),
                    ("dmDuplex", ctypes.c_short),
                    ("dmYResolution", ctypes.c_short),
                    ("dmTTOption", ctypes.c_short),
                    ("dmCollate", ctypes.c_short),
                    ("dmFormName", ctypes.c_wchar * 32),
                    ("dmLogPixels", ctypes.c_ushort),
                    ("dmBitsPerPel", ctypes.c_ulong),
                    ("dmPelsWidth", ctypes.c_ulong),
                    ("dmPelsHeight", ctypes.c_ulong),
                    ("dmDisplayFlags", ctypes.c_ulong),
                    ("dmDisplayFrequency", ctypes.c_ulong),
                ]

            devmode = DEVMODE()
            devmode.dmSize = ctypes.sizeof(DEVMODE)
            ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode))
            self.log(f"Resolution: {devmode.dmPelsWidth} x {devmode.dmPelsHeight}")
            self.log(f"Refresh rate: {devmode.dmDisplayFrequency} Hz")
            hdc = ctypes.windll.user32.GetDC(None)
            bits_per_pixel = ctypes.windll.gdi32.GetDeviceCaps(hdc, 12)
            ctypes.windll.user32.ReleaseDC(None, hdc)
            self.log(f"Color depth: {bits_per_pixel} bits")
            self.log("Run Dead Pixel Test next for a visual screen check.")
        except Exception as error:
            self.log(f"Display verification error: {error}")
        self.log("==============================")

    def camera_microphone_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== Camera / Microphone Check =====")
        
        # Check for devices via PowerShell
        camera_info = run_shell_command(
            'powershell -NoProfile -Command "Get-PnpDevice -Class Camera | Select-Object FriendlyName,Status | Format-Table -AutoSize"'
        )
        mic_info = run_shell_command(
            'powershell -NoProfile -Command "Get-PnpDevice -Class AudioEndpoint | Select-Object FriendlyName,Status | Format-Table -AutoSize"'
        )
        self.log("Cameras:")
        self.log(camera_info or "No camera devices found.")
        self.log("Microphones:")
        self.log(mic_info or "No microphone devices found.")
        
        # Open camera recorder if window_opener is available
        if self.window_opener:
            self.log("Opening camera & audio recorder...")
            try:
                self.window_opener(CameraRecorder)
            except Exception as error:
                self.log(f"Failed to open camera recorder: {error}")
        
        self.log("==============================")


    def io_port_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== I/O Port and USB Check =====")
        usb_devices = run_shell_command(
            'powershell -NoProfile -Command "Get-PnpDevice -Class USB | Where-Object {$_.Status -eq \'OK\'} | Select-Object FriendlyName,Manufacturer,Status | Format-Table -AutoSize"'
        )
        storage_devices = run_shell_command(
            'powershell -NoProfile -Command "Get-PnpDevice -Class DiskDrive | Select-Object FriendlyName,Status | Format-Table -AutoSize"'
        )
        external_video = run_shell_command(
            'powershell -NoProfile -Command "Get-PnpDevice | Where-Object {$_.FriendlyName -match \'HDMI|DisplayPort|DP\'} | Select-Object FriendlyName,Status | Format-Table -AutoSize"'
        )
        self.log("USB devices:")
        self.log(usb_devices or "No USB devices detected.")
        self.log("Storage / card reader devices:")
        self.log(storage_devices or "No disk drive information available.")
        self.log("External video port candidates:")
        self.log(external_video or "No HDMI/DisplayPort devices detected.")
        self.log("==============================")

    def wireless_health_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== Wireless Health Test =====")
        output = run_shell_command("netsh wlan show interfaces")
        self.log(output or "No wireless interface information available.")
        self.log("==============================")

    def power_on_hours(self) -> None:
        if not self.require_windows():
            return

        self.log("===== System Age =====")
        output = run_shell_command("systeminfo")
        for line in output.splitlines():
            if "Original Install Date" in line:
                self.log(line.strip())
        uptime_hours = round((time.time() - psutil.boot_time()) / 3600, 2)
        self.log(f"Current session uptime: {uptime_hours} hours")
        if uptime_hours < 5:
            self.log("Status: Good")
        self.log("======================")

    def wifi6_detection(self) -> None:
        if not self.require_windows():
            return

        self.log("===== WiFi 6 Detection =====")
        output = run_shell_command("netsh wlan show interfaces")
        self.log(output or "No network interface information available.")
        standard, status = detect_wifi_standard(output)
        self.log(f"Result: {standard}")
        self.log(f"Status: {status}")
        self.log("=============================")

    def wifi_speed_test(self) -> None:
        if not self.require_windows():
            return

        self.log("===== WiFi Speed Test =====")
        ping_output = run_shell_command("ping google.com -n 4")
        self.log("Ping summary:")
        self.log(ping_output)
        try:
            self.log("Starting download speed measurement...")
            speed_mbps = measure_download_speed()
            self.log(f"Download result: {speed_mbps:.2f} Mbps")
            status = "Excellent" if speed_mbps > 50 else "Good" if speed_mbps > 20 else "Slow"
            self.log(f"Status: {status}")
        except Exception as error:
            self.log(f"WiFi test error: {error}")
        self.log("===========================")
