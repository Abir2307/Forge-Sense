import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QCheckBox, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtGui import Qt

from ..otp import generate_otps
from ..email_service import send_email_otp


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


class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Forge-Sense")
        self.setFixedSize(840, 550)

        # ---- GLOBAL STYLE (MATCH LOGIN) ----
        self.setStyleSheet("""
            QWidget {
                background-color: #4682B4;
            }
            QLineEdit {
                background-color: rgba(147, 184, 152, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 5px;
                padding: 6px;
                min-height: 18px;
                color: black;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.3);
                border: 1px solid #2196F3;
            }
            QCheckBox {
                font-size: 12px;
                font-weight: 600;
                color: #222;
                margin-top: 6px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

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

        header = QLabel("Create Account")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 25px;
                font-weight:bold; 
                font-weight: 700;
                font-family: 'Segoe UI', Arial;
                color: #0963ab;
            }
        """)
        form.addWidget(header)

        def subheading(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "font-weight:600; font-size:13px; color:#333; margin-top:8px;"
            )
            return lbl

        # -------- INPUT FIELDS --------
        form.addWidget(subheading("Full Name"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("Enter your full name")
        form.addWidget(self.name)

        form.addWidget(subheading("Username"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("e.g. user_name")
        self.username.textChanged.connect(self.check_username_availability)
        form.addWidget(self.username)

        self.username_status = QLabel()
        self.username_status.setStyleSheet("font-size:10px; color: gray;")
        form.addWidget(self.username_status)

        form.addWidget(subheading("Email Address"))
        self.email = QLineEdit()
        self.email.setPlaceholderText("example@domain.com")
        form.addWidget(self.email)

        form.addWidget(subheading("Password"))
        self.password = QLineEdit()
        self.password.setPlaceholderText("Minimum 8 characters")
        self.password.setEchoMode(QLineEdit.Password)
        form.addWidget(self.password)

        form.addWidget(subheading("Confirm Password"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Repeat your password")
        self.confirm_password.setEchoMode(QLineEdit.Password)
        form.addWidget(self.confirm_password)

        form.addWidget(subheading("Secret Code"))
        self.secret_code = QLineEdit()
        self.secret_code.setPlaceholderText("Used for account recovery")
        self.secret_code.setEchoMode(QLineEdit.Password)
        form.addWidget(self.secret_code)

        # -------- OTP OPTION --------
        self.use_otp = QCheckBox("Use OTP verification via email")
        form.addWidget(self.use_otp)

        # -------- REGISTER BUTTON --------
        form.addSpacing(12)
        register_btn = QPushButton("Register")
        register_btn.setMinimumHeight(35)
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #095a9d;
            }
        """)
        register_btn.clicked.connect(self.register)
        form.addWidget(register_btn)

        # -------- LOGIN LINK --------
        login_link = QPushButton("Already have an account? Login")
        login_link.setFlat(True)
        login_link.setStyleSheet("""
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
        login_link.clicked.connect(self.open_login)
        form.addWidget(login_link)

        form.addStretch()

        # -------- FINAL LAYOUT --------
        main_layout.addWidget(logo, 1)
        main_layout.addLayout(form, 2)
        self.setLayout(main_layout)

    # ---------------- LOGIC  ----------------

    def check_username_availability(self):
        from safetwin.db.database import username_exists
        username = self.username.text().strip()

        if not username:
            self.username_status.setText("")
            return

        if len(username) < 3:
            self.username_status.setText("❌ Username must be at least 3 characters")
            self.username_status.setStyleSheet("color:red; font-size:10px;")
            return

        if not username.replace('_', '').replace('-', '').isalnum():
            self.username_status.setText("❌ Only letters, numbers, _ and - allowed")
            self.username_status.setStyleSheet("color:red; font-size:10px;")
            return

        if username_exists(username):
            self.username_status.setText(f"❌ '{username}' is already taken")
            self.username_status.setStyleSheet("color:red; font-size:10px;")
        else:
            self.username_status.setText(f"✓ '{username}' is available")
            self.username_status.setStyleSheet("color:green; font-size:10px;")

    def register(self):
        if not all([
            self.name.text(),
            self.username.text(),
            self.email.text(),
            self.secret_code.text()
        ]):
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("All fields are required")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        if self.password.text() != self.confirm_password.text():
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Passwords do not match")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        if len(self.password.text()) < 8:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Password must be at least 8 characters")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        username = self.username.text().strip()

        if self.use_otp.isChecked():
            from safetwin.db.database import username_exists
            if username_exists(username):
                QMessageBox.warning(self, "Error", f"Username '{username}' already exists")
                return

            email = self.email.text().strip()
            email_otp, _ = generate_otps(email)

            sent, error_msg = send_email_otp(email, email_otp)
            if not sent:
                msg = QMessageBox(self)
                msg.setWindowTitle("Error")
                msg.setText(f"OTP send failed:\n{error_msg}")
                msg.setIcon(QMessageBox.Critical)
                style_messagebox(msg)
                msg.exec()
                return

            from .otp_verify import OTPWindow
            self.otp_window = OTPWindow(
                user_id=email,
                email=email,
                mode="register",
                user_data={
                    "name": self.name.text(),
                    "username": username,
                    "email": email,
                    "password": self.password.text(),
                    "secret_code": self.secret_code.text()
                }
            )
            self.otp_window.show()
            self.close()
        else:
            from ...db.database import register_user, username_exists
            if username_exists(username):
                msg = QMessageBox(self)
                msg.setWindowTitle("Error")
                msg.setText(f"Username '{username}' already exists")
                msg.setIcon(QMessageBox.Warning)
                style_messagebox(msg)
                msg.exec()
                return

            success = register_user(
                username,
                self.name.text(),
                self.email.text().strip(),
                self.password.text(),
                self.secret_code.text()
            )

            if success:
                msg = QMessageBox(self)
                msg.setWindowTitle("Success")
                msg.setText("Registration successful! Please login.")
                msg.setIcon(QMessageBox.Information)
                style_messagebox(msg)
                msg.exec()
                self.open_login()
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle("Error")
                msg.setText("Registration failed. Email may already exist.")
                msg.setIcon(QMessageBox.Warning)
                style_messagebox(msg)
                msg.exec()

    def open_login(self):
        from .login import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()
