from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtGui import Qt
import sys
from pathlib import Path

from safetwin.auth.security_code import (
    generate_security_code,
    generate_captcha_pixmap
)
from safetwin.db.database import get_email_by_username, verify_user


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


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forge-Sense")
        self.setFixedSize(800, 450)

        self.security_code = generate_security_code()
        self.generated_otp = None
        self.user_email = None

        self.setStyleSheet("""
            LoginWindow {
                background-color: #4682B4;
            }
            QLineEdit {
                background-color: rgba(147, 184, 152, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 5px;
                padding: 5px;
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

    # ---------------- CAPTCHA ---------------- #

    def refresh_captcha(self):
        self.security_code = generate_security_code()
        captcha_bytes = generate_captcha_pixmap(self.security_code)

        pixmap = QPixmap()
        pixmap.loadFromData(captcha_bytes)
        self.code_label.setPixmap(pixmap)

    # ---------------- UI ---------------- #

    def init_ui(self):
        main_layout = QHBoxLayout()

        # -------- Left Logo -------- #
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

        # -------- Right Form -------- #
        form = QVBoxLayout()

        title = QLabel("<h2>Login</h2>")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
                            font-size:25px;
                            font-weight:bold; 
                            font-family: 'Segoe UI', Arial; 
                            font-weight:700; 
                            color:#0963ab;""")
        form.addWidget(title)

        def subheading(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight:600; font-size:13px; color:#333; margin-top:8px;")
            return lbl

        # Username
        form.addWidget(subheading("Username"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter your username")
        self.username.setFixedHeight(35)
        form.addWidget(self.username)

        # Password
        form.addWidget(subheading("Password"))
        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(35)
        form.addWidget(self.password)

        # -------- CAPTCHA -------- #
        form.addWidget(subheading("Security Verification"))

        captcha_layout = QHBoxLayout()

        self.code_label = QLabel()
        self.code_label.setFixedSize(180, 60)
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px dashed rgba(0, 0, 0, 0.5);
                border-radius: 5px;
                padding: 6px;
            }
        """)

        self.refresh_captcha()

        # 🔄 Refresh Button (Round)
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setToolTip("Refresh CAPTCHA")
        refresh_btn.clicked.connect(self.refresh_captcha)
        refresh_btn.setStyleSheet("""
            QPushButton {
                border-radius: 18px;
                background-color: #2196F3;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)

        captcha_layout.addWidget(self.code_label)
        captcha_layout.addWidget(refresh_btn)
        captcha_layout.addStretch()

        form.addLayout(captcha_layout)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Type the code shown above")
        self.code_input.setFixedHeight(35)
        form.addWidget(self.code_input)

        # Login Button
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        login_btn.clicked.connect(self.handle_final_login)
        form.addWidget(login_btn)

        # Links
        links = QHBoxLayout()

        register_btn = QPushButton("New User? Register")
        register_btn.setFlat(True)
        register_btn.setStyleSheet("""
            QPushButton {
                color: #0e1fe3;                 /* Bright Cyan for better visibility */
                background: transparent;
                text-decoration: underline;
                font-size: 13px;                /* Slightly larger */
                font-weight: bold;              /* Make it Bold */
                font-family: 'Segoe UI', Arial; /* Modern font style */
            }
            QPushButton:hover {
                color: #000000;                 /* Turns white when hovering */
            }
        """)
        register_btn.clicked.connect(self.open_register)

        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setFlat(True)
        forgot_btn.setStyleSheet("""
            QPushButton {
                color: #bf0420;                 /* Bright Cyan for better visibility */
                background: transparent;
                text-decoration: underline;
                font-size: 13px;                /* Slightly larger */
                font-weight: bold;              /* Make it Bold */
                font-family: 'Segoe UI', Arial; /* Modern font style */
            }
            QPushButton:hover {
                color: #000000;                 /* Turns white when hovering */
            }
        """)
        forgot_btn.clicked.connect(self.open_forgot_password)

        links.addWidget(register_btn)
        links.addStretch()
        links.addWidget(forgot_btn)

        form.addLayout(links)
        form.addStretch()

        main_layout.addWidget(logo, 1)
        main_layout.addLayout(form, 2)
        self.setLayout(main_layout)

    # ---------------- Logic ---------------- #

    def handle_final_login(self):
        if self.code_input.text().strip() != self.security_code:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Invalid security code")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            self.code_input.clear()
            self.refresh_captcha()
            return

        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Please enter username and password")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        self.user_email = get_email_by_username(username)
        if not self.user_email:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("User not found")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        user = verify_user(self.user_email, password)
        if not user:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Invalid password")
            msg.setIcon(QMessageBox.Warning)
            style_messagebox(msg)
            msg.exec()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Success")
        msg.setText(f"Welcome back, {user[2]}!")
        msg.setIcon(QMessageBox.Information)
        style_messagebox(msg)
        msg.exec()

        try:
            if user[6] == 0:
                from safetwin.ui.main_window import MainWindow
                self.main_window = MainWindow(username=user[1])
                self.main_window.show()
            else:
                from safetwin.ui.admin.admin_dashboard import AdminDashboardWindow
                self.admin_dashboard = AdminDashboardWindow()
                self.admin_dashboard.show()

            self.close()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"Unable to open dashboard: {e}")
            msg.setIcon(QMessageBox.Critical)
            style_messagebox(msg)
            msg.exec()

    # ---------------- Navigation ---------------- #

    def open_register(self):
        from .register import RegisterWindow
        self.register_window = RegisterWindow()
        self.register_window.show()
        self.close()

    def open_forgot_password(self):
        from .forgot_password import ForgotPasswordWindow
        self.forgot_window = ForgotPasswordWindow()
        self.forgot_window.show()
        self.close()
