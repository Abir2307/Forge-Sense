from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtGui import Qt
import sys
from pathlib import Path

from safetwin.db.database import (
    verify_secret_code,
    get_email_by_username,
    update_password
)
from safetwin.auth.ui.login import LoginWindow


def get_asset_path(relative_path):
    """Get asset path that works in both dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        base = Path(sys.executable).parent / "_internal"
    else:
        # Running as script
        base = Path(__file__).resolve().parents[3]
    return base / relative_path


LOGO_PATH = get_asset_path("safetwin/auth/assets/logo.png")


def style_messagebox(msg_box):
    """Apply theme styling to message box."""
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #4682B4;
        }
        QMessageBox QLabel {
            color: #333;
            font-size: 13px;
        }
        QPushButton {
            background-color: #2196F3;
            color: white;
            border-radius: 5px;
            padding: 6px 16px;
            font-weight: 600;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #0b7dda;
        }
        QPushButton:pressed {
            background-color: #095a9d;
        }
    """)


class ForgotPasswordWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forge-Sense")
        self.setFixedSize(840, 500)

        # -------- GLOBAL STYLE (MATCH LOGIN / REGISTER) --------
        self.setStyleSheet("""
            QWidget {
                background-color: #4682B4;
            }
            QLineEdit {
                background-color: rgba(147, 184, 152, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 5px;
                padding: 7px;
                color: black;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.3);
                border: 1px solid #2196F3;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)

        # -------- LEFT LOGO --------
        class CoverLogoLabel(QLabel):
            def __init__(self):
                super().__init__()
                self._pixmap = None
                self.setAlignment(Qt.AlignCenter)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            def set_logo(self, pixmap):
                self._pixmap = pixmap
                self._update_pixmap()

            def resizeEvent(self, event):
                super().resizeEvent(event)
                self._update_pixmap()

            def _update_pixmap(self):
                if not self._pixmap or self.width() <= 0 or self.height() <= 0:
                    return
                scaled = self._pixmap.scaled(
                    self.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.setPixmap(scaled)

        logo = CoverLogoLabel()
        pixmap = QPixmap(str(LOGO_PATH))
        if not pixmap.isNull():
            logo.set_logo(pixmap)
        else:
            logo.setText("[Logo]")

        # -------- RIGHT FORM --------
        form = QVBoxLayout()
        form.setSpacing(10)

        header = QLabel("Reset Password")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial;
                color: #0963ab;
                margin-bottom: 10px;
            }
        """)
        form.addWidget(header)

        def subheading(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "font-weight:600; font-size:13px; color:#333; margin-top:6px;"
            )
            return lbl

        # -------- INPUTS --------
        form.addWidget(subheading("Username"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Registered username")
        form.addWidget(self.username)

        form.addWidget(subheading("Secret Code"))
        self.secret_code = QLineEdit()
        self.secret_code.setPlaceholderText("Account recovery secret")
        self.secret_code.setEchoMode(QLineEdit.Password)
        form.addWidget(self.secret_code)

        form.addWidget(subheading("New Password"))
        self.new_pass = QLineEdit()
        self.new_pass.setPlaceholderText("Minimum 8 characters")
        self.new_pass.setEchoMode(QLineEdit.Password)
        form.addWidget(self.new_pass)

        form.addWidget(subheading("Confirm New Password"))
        self.repeat_pass = QLineEdit()
        self.repeat_pass.setPlaceholderText("Repeat new password")
        self.repeat_pass.setEchoMode(QLineEdit.Password)
        form.addWidget(self.repeat_pass)

        # -------- RESET BUTTON --------
        form.addSpacing(12)
        reset_btn = QPushButton("Reset Password")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        reset_btn.clicked.connect(self.reset_password)
        form.addWidget(reset_btn)

        # -------- BACK TO LOGIN --------
        back_link = QPushButton("Back to Login")
        back_link.setFlat(True)
        back_link.setStyleSheet("""
            QPushButton {
                color: #0e1fe3;
                font-weight: bold;
                text-decoration: underline;
                font-size: 12px;
                background: transparent;
            }
            QPushButton:hover {
                color: #000000;
            }
        """)
        back_link.clicked.connect(self.back_to_login)
        form.addWidget(back_link)

        form.addStretch()

        # -------- FINAL LAYOUT --------
        main_layout.addWidget(logo, 1)
        main_layout.addLayout(form, 2)
        self.setLayout(main_layout)

    # ---------------- LOGIC ----------------

    def reset_password(self):
        username = self.username.text().strip()
        secret_code = self.secret_code.text().strip()
        new_pass = self.new_pass.text()
        repeat_pass = self.repeat_pass.text()

        if not username or not secret_code or not new_pass or not repeat_pass:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("All fields are required")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        if new_pass != repeat_pass:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Passwords do not match")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        if len(new_pass) < 8:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Password must be at least 8 characters")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        if not verify_secret_code(username, secret_code):
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Invalid username or secret code")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        email = get_email_by_username(username)
        if not email:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Invalid credentials")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        success, message = update_password(email, new_pass)
        if not success:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(message)
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Success")
        msg.setText("Password updated successfully. Please login.")
        msg.setIcon(QMessageBox.Information)
        style_messagebox(msg)
        msg.exec()
        self.back_to_login()

    def back_to_login(self):
        self.login = LoginWindow()
        self.login.show()
        self.close()
