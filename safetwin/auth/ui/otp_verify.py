from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton,
    QVBoxLayout, QLabel, QMessageBox
)
from PySide6.QtGui import QTimer, Qt
from PySide6.QtGui import QFont

from ..otp import verify_email_otp, generate_otps, OTP_EXPIRY
from ..email_service import send_email_otp
from ...db.database import register_user

class OTPWindow(QWidget):
    def __init__(self, user_id, email, mode="login", user_data=None):
        super().__init__()
        self.user_id = user_id # This is the 'username'
        self.email = email
        self.mode = mode
        self.user_data = user_data
        self.username = user_id  # for login mode
        self.time_left = OTP_EXPIRY
        self._open_register_on_close = True

        self.setWindowTitle("OTP Verification")
        self.setFixedSize(350, 280)

        self.init_ui()

        # Start the countdown timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Title
        title = QLabel("<b>Verify Your Email</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 12))
        layout.addWidget(title)

        # 🔹 SHOW EMAIL ADDRESS (Masked for privacy)
        user_part, domain_part = self.email.split('@')
        masked_email = f"{user_part[0:3]}****@{domain_part}"
        
        info_lbl = QLabel(f"A 6-digit code has been sent to:<br><b>{masked_email}</b>")
        info_lbl.setTextFormat(Qt.RichText)
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # OTP Input
        self.email_otp = QLineEdit()
        self.email_otp.setPlaceholderText("Enter 6-digit OTP")
        self.email_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_otp.setFixedHeight(40)
        self.email_otp.setStyleSheet("font-size: 16px; letter-spacing: 5px;")
        layout.addWidget(self.email_otp)

        # Verify Button
        self.verify_btn = QPushButton("Verify & Proceed")
        self.verify_btn.setFixedHeight(40)
        self.verify_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.verify_btn.clicked.connect(self.verify)
        layout.addWidget(self.verify_btn)

        # Resend Button
        self.resend_btn = QPushButton(f"Resend OTP ({self.time_left}s)")
        self.resend_btn.setEnabled(False)
        self.resend_btn.setFlat(True)
        self.resend_btn.clicked.connect(self.resend_otp)
        layout.addWidget(self.resend_btn)

        self.setLayout(layout)

    def update_timer(self):
        self.time_left -= 1
        if self.time_left > 0:
            self.resend_btn.setText(f"Resend OTP ({self.time_left}s)")
        else:
            self.timer.stop()
            self.resend_btn.setEnabled(True)
            self.resend_btn.setText("Resend OTP")
            self.resend_btn.setStyleSheet("color: blue; font-weight: bold;")

    def resend_otp(self):
        # Regenerate and send
        email_otp, _ = generate_otps(self.user_id)
        sent, error_msg = send_email_otp(self.email, email_otp)
        if not sent:
            QMessageBox.warning(self, "Error", f"OTP send failed:\n{error_msg}")
            return
        
        # Reset Timer
        self.time_left = OTP_EXPIRY
        self.resend_btn.setEnabled(False)
        self.resend_btn.setStyleSheet("")
        self.timer.start(1000)
        QMessageBox.information(self, "Sent", "A new OTP has been sent to your email.")

    def verify(self):
        # 1. Validate OTP
        if not verify_email_otp(self.user_id, self.email_otp.text().strip()):
            QMessageBox.warning(self, "Error", "Invalid or expired OTP")
            return

        # 2. Handle Logic based on Mode
        if self.mode == "register":
            # Pass all 5 required fields: username, name, email, phone, password
            success = register_user(
                self.user_data.get("username"),
                self.user_data.get("name"),
                self.user_data.get("email"),
                self.user_data.get("password"),
                self.user_data.get("secret_code")
            )

            if success:
                QMessageBox.information(self, "Success", "Registration successful! Please login.")
                from .login import LoginWindow
                self.login = LoginWindow()
                self.login.show()
                self._open_register_on_close = False
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Registration failed. User might already exist.")
        
        else:
            # LOGIN FLOW
            from safetwin.ui.main_window import MainWindow
            QMessageBox.information(self, "Success", "Login verified successfully!")
            self.main_window = MainWindow(username=self.username)
            self.main_window.show()
            self.close()

    def closeEvent(self, event):
        if self.mode == "register" and self._open_register_on_close:
            from .register import RegisterWindow
            self.register_window = RegisterWindow()
            self.register_window.show()
        event.accept()