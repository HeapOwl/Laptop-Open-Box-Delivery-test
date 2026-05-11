import os
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from obd.ui import LaptopChecker


def is_windows_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(__import__("ctypes") .windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def try_elevate() -> bool:
    if os.name != "nt":
        return False

    script_path = os.path.abspath(sys.argv[0])
    if not os.path.isfile(script_path):
        script_path = os.path.abspath(__file__)

    args = [script_path] + sys.argv[1:]
    params = subprocess.list2cmdline(args[1:]) if len(args) > 1 else ""

    try:
        rc = __import__("ctypes").windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script_path}" {params}'.strip(),
            None,
            1,
        )
        return rc > 32
    except Exception:
        return False


def main() -> int:
    if os.name == "nt" and not is_windows_admin():
        if try_elevate():
            return 0
        print("Administrator privileges are required to run this tool.")
        return 1

    app = QApplication(sys.argv)
    window = LaptopChecker()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())