import sys
import os
import ctypes
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from safetwin.auth.ui.login import LoginWindow

def resource_path(relative_path):
    """
    Get absolute path to resource.
    Works for both development and PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main():

    myappid = "forgesense.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)

    app.setStyleSheet(
        """
        QMessageBox {
            background-color: #e8f5e9;
        }
        QMessageBox QLabel {
            color: #1b5e20;
            font-size: 13px;
            font-weight: 600;
        }
        QMessageBox QPushButton {
            background-color: #2e7d32;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            min-width: 72px;
        }
        QMessageBox QPushButton:hover {
            background-color: #388e3c;
        }
        QMessageBox QPushButton:pressed {
            background-color: #1b5e20;
        }
        """
    )

    icon_path = resource_path("assets/logo.ico")
    icon = QIcon(icon_path)
    
    # Application icon (taskbar / Alt+Tab)
    app.setWindowIcon(icon)

    window = LoginWindow()

    # Window icon (top-left of window)
    window.setWindowIcon(icon)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()