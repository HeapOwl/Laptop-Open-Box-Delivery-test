import platform
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .dead_pixel import DeadPixelWindow
from .diagnostic_runner import DiagnosticRunner

APP_TITLE = "Laptop Open Box Delivery Checker"
LOG_PREFIX = "[INFO]"


class LaptopChecker(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(900, 720)
        self.runner = DiagnosticRunner(self.log, self._open_window)
        self._build_interface()
        self.runner.startup_report()

    def _open_window(self, window_class: type) -> None:
        """Open a new window instance"""
        window = window_class()
        window.show()

    def _build_interface(self) -> None:
        self.setObjectName("mainWindow")
        self.setStyleSheet(
            "QWidget#mainWindow { background: #020202; color: #7CFC00; }"
            "QLabel#header { color: #78ff78; font-size: 26px; font-weight: bold; }"
            "QLabel#subtitle { color: #9cff9c; font-size: 11px; letter-spacing: 1px; }"
            "QFrame#controlPanel { background: #060606; border: 1px solid #0f0; border-radius: 10px; }"
            "QFrame#outputPanel { background: #010101; border: 1px solid #2bff2b; border-radius: 10px; }"
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b470b, stop:1 #1fbf1f);"
            "  color: #020202;"
            "  border: 1px solid #20d020;"
            "  border-radius: 8px;"
            "  padding: 10px 12px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2bff2b, stop:1 #18b918); }"
            "QPushButton:pressed { background: #0f7f0f; }"
            "QPlainTextEdit { background: #000; color: #7cff7c; selection-background-color: #2c2; border:none; }"
        )

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(18, 18, 18, 18)

        header = QLabel("OBD TERMINAL")
        header.setObjectName("header")
        header.setFont(QFont("Consolas", 24, QFont.Weight.Bold))

        subtitle = QLabel("Laptop diagnostic console")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Consolas", 10))

        top_bar = QVBoxLayout()
        top_bar.addWidget(header)
        top_bar.addWidget(subtitle)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        control_panel = QFrame()
        control_panel.setObjectName("controlPanel")
        control_panel_layout = QVBoxLayout(control_panel)
        control_panel_layout.setContentsMargins(12, 12, 12, 12)
        control_panel_layout.setSpacing(12)

        section_title = QLabel("COMMANDS")
        section_title.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #9cff9c; margin-bottom: 8px;")
        control_panel_layout.addWidget(section_title)

        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(10)
        button_grid.setVerticalSpacing(10)

        actions = [
            ("Startup Report", self.runner.startup_report),
            ("Run Diagnostics", self.run_diagnostics),
            ("Dead Pixel Test", self.dead_pixel_test),
            ("System Info", self.runner.system_info),
            ("Display Info", self.runner.refresh_rate),
            ("RAM Integrity", self.runner.ram_integrity_test),
            ("Display Verification", self.runner.display_verification),
            ("Camera / Mic Check", self.runner.camera_microphone_test),
            ("I/O Port Check", self.runner.io_port_test),
            ("Wireless Health", self.runner.wireless_health_test),
            ("2 Min Stress Test", self.runner.stress_test),
            ("Speaker Test", self.runner.speaker_test),
            ("Battery Health", self.runner.battery_wear),
            ("SSD Info", self.runner.ssd_health),
            ("SSD Age/TBW", self.runner.ssd_age_tbw_test),
            ("Open Box Summary", self.runner.open_box_summary),
            ("System Age", self.runner.power_on_hours),
            ("WiFi Speed Test", self.runner.wifi_speed_test),
            ("WiFi 6 Detection", self.runner.wifi6_detection),
            ("Clear Logs", self.clear_logs),
        ]

        for index, (label, handler) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(handler)
            button.setMinimumHeight(42)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button_grid.addWidget(button, index // 2, index % 2)

        control_panel_layout.addLayout(button_grid)
        control_panel_layout.addStretch(1)

        output_panel = QFrame()
        output_panel.setObjectName("outputPanel")
        output_layout = QVBoxLayout(output_panel)
        output_layout.setContentsMargins(12, 12, 12, 12)
        output_layout.setSpacing(10)

        terminal_title = QLabel("TERMINAL OUTPUT")
        terminal_title.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        terminal_title.setStyleSheet("color: #9cff9c;")

        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.info.setFont(QFont("Consolas", 11))
        self.info.setPlaceholderText("Awaiting command... press a button to start diagnostics.")

        output_layout.addWidget(terminal_title)
        output_layout.addWidget(self.info)

        body_layout.addWidget(control_panel, 0)
        body_layout.addWidget(output_panel, 1)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(body_layout)
        self.setLayout(main_layout)

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.info.appendPlainText(f"{timestamp} {LOG_PREFIX} {message}")
        self.info.verticalScrollBar().setValue(
            self.info.verticalScrollBar().maximum()
        )
        QApplication.processEvents()

    def clear_logs(self) -> None:
        self.info.clear()
        self.log("Cleared log output.")


    def run_diagnostics(self) -> None:
        if getattr(self, "_diagnostic_running", False):
            self.log("Diagnostics are already running.")
            return

        self._diagnostic_queue = [
            self.runner.system_info,
            self.runner.refresh_rate,
            self.runner.ram_integrity_test,
            self.runner.display_verification,
            self.runner.camera_microphone_test,
            self.runner.io_port_test,
            self.runner.wireless_health_test,
            self.runner.speaker_test,
            self.runner.battery_wear,
            self.runner.ssd_health,
            self.runner.ssd_age_tbw_test,
            self.runner.power_on_hours,
            self.runner.wifi_speed_test,
            self.runner.wifi6_detection,
        ]
        self._diagnostic_index = 0
        self._diagnostic_running = True
        self.log("===== RUNNING DIAGNOSTICS =====")
        self._run_next_diagnostic()

    def _run_next_diagnostic(self) -> None:
        if self._diagnostic_index >= len(self._diagnostic_queue):
            self._diagnostic_running = False
            self.log("===== DIAGNOSTICS COMPLETE =====")
            return

        handler = self._diagnostic_queue[self._diagnostic_index]
        self._diagnostic_index += 1
        handler()
        QTimer.singleShot(650, self._run_next_diagnostic)

    def dead_pixel_test(self) -> None:
        if not self.runner.require_windows():
            return
        self.dp_window = DeadPixelWindow()
        self.dp_window.show()
