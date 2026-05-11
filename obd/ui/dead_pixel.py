from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget


class DeadPixelWindow(QWidget):
    """Full-screen dead pixel testing window."""

    COLORS = [
        ("BLACK", QColor(0, 0, 0)),
        ("WHITE", QColor(255, 255, 255)),
        ("RED", QColor(255, 0, 0)),
        ("GREEN", QColor(0, 255, 0)),
        ("BLUE", QColor(0, 0, 255)),
        ("GRAY", QColor(128, 128, 128)),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.index = 0
        self.setWindowTitle("Dead Pixel Test")
        self.showFullScreen()
        self.change_color()

    def change_color(self) -> None:
        name, color = self.COLORS[self.index]
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setWindowTitle(f"Dead Pixel Test — {name}")

    def next_color(self) -> None:
        self.index = (self.index + 1) % len(self.COLORS)
        self.change_color()

    def mousePressEvent(self, event) -> None:
        self.next_color()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.next_color()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
