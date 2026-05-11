# Laptop Open Box Delivery Checker

A Windows-only diagnostic utility for laptop inspection and functional testing.

## Features

- Dead pixel screen validation
- System information summary
- Display resolution and refresh rate check
- 2-minute CPU stress test
- Speaker tone playback
- Battery wear reporting
- SSD detection and media metadata
- System uptime / original install date lookup
- WiFi speed and WiFi 6 / adapter capability checks

## Requirements

- Python 3.10+
- Windows 10 / Windows 11
- `PyQt6`
- `psutil`
- `numpy`
- `sounddevice`
- `wmi`

## Installation

```powershell
python -m pip install -r requirements.txt
```

## Development dependencies

```powershell
python -m pip install -r requirements-dev.txt
```

## Usage

```powershell
python obd.py
```

## Notes

- The application provides a simple graphical interface for laptop inspection tasks.
- Windows command utilities are used for network and system queries, so the tool is not portable to Linux/macOS.
- Application logic is now separated into the `obd` package with `ui`, `diagnostics`, and `app` modules.
