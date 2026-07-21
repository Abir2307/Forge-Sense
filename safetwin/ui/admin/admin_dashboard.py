from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QMessageBox, QComboBox, QTextEdit, QSizePolicy
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from safetwin.db.database import fetch_sessions, fetch_session_by_id, fetch_analysis_results_by_session
from safetwin.core.report import generate_pdf_report
from safetwin.auth.ui.login import LoginWindow
from datetime import datetime
import os
import sqlite3
from pathlib import Path


class ImageViewer(QWidget):
    """Small fallback image viewer used by the admin dashboard when the full viewer module is unavailable."""

    def __init__(self, title="Images", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: white;")
        self.image_list = QTextEdit()
        self.image_list.setReadOnly(True)
        self.image_list.setMinimumHeight(180)
        layout.addWidget(self.title_label)
        layout.addWidget(self.image_list)

    def set_images(self, image_paths):
        self.image_list.setPlainText("\n".join(image_paths))

    def clear(self):
        self.image_list.clear()

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "safetwin.db"


class AdminDashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        self.setMinimumSize(1024, 768)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.s = None  
        self.init_ui()

    def init_ui(self):
        # Create main container with background
        main_container = QFrame()
        main_container.setObjectName("MainContainer")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top Navbar
        navbar = QFrame()
        navbar.setMinimumHeight(50)
        navbar.setMaximumHeight(70)
        navbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        navbar.setStyleSheet("QFrame { background-color: #1f2933; }")
        nav_layout = QHBoxLayout(navbar)

        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")

        logout_btn = QPushButton("Logout")
        logout_btn.setMinimumWidth(80)
        logout_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                padding: 6px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        logout_btn.clicked.connect(self.logout)

        nav_layout.addWidget(title)
        nav_layout.addStretch()
        nav_layout.addWidget(logout_btn)

        # Body Layout
        body_layout = QVBoxLayout()

        # User Selection
        user_layout = QHBoxLayout()
        user_label = QLabel("Select User:")
        user_label.setFont(QFont("Arial", 12))
        self.user_combo = QComboBox()
        self.user_combo.setFont(QFont("Segoe UI", 10))
        self.user_combo.setMinimumWidth(200)
        self.user_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.user_combo.addItem("Select User")
        self.load_users()
        self.user_combo.currentIndexChanged.connect(self.load_user_sessions)

        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_combo)
        user_layout.addStretch()

        # Session Selection
        session_layout = QHBoxLayout()
        session_label = QLabel("Select Session:")
        session_label.setFont(QFont("Arial", 12))
        self.session_combo = QComboBox()
        self.session_combo.setFont(QFont("Segoe UI", 10))
        self.session_combo.setMinimumWidth(200)
        self.session_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.session_combo.addItem("Select Session")
        self.session_combo.currentIndexChanged.connect(self.load_session_details)

        session_layout.addWidget(session_label)
        session_layout.addWidget(self.session_combo)
        session_layout.addStretch()

        # Session Details
        details_layout = QVBoxLayout()
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(100)
        self.details_text.setMaximumHeight(150)
        self.details_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        details_layout.addWidget(QLabel("Session Details:"))
        details_layout.addWidget(self.details_text)

        # Image Viewers
        img_layout = QHBoxLayout()
        self.input_viewer = ImageViewer("Input Images")
        self.output_viewer = ImageViewer("Output Images")
        img_layout.addWidget(self.input_viewer)
        img_layout.addWidget(self.output_viewer)

        # Report Button
        report_btn = QPushButton("View Report")
        report_btn.setFont(QFont("Segoe UI", 11))
        report_btn.setMinimumWidth(150)
        report_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        report_btn.clicked.connect(self.generate_report)

        body_layout.addLayout(user_layout)
        body_layout.addLayout(session_layout)
        body_layout.addLayout(details_layout)
        body_layout.addLayout(img_layout)
        body_layout.addWidget(report_btn)

        main_layout.addWidget(navbar)
        main_layout.addLayout(body_layout)

        # Set the main container as central widget
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(main_container)
        self.setLayout(container_layout)

        # Apply dashboard styles without requiring a local background asset
        main_container.setStyleSheet("""
            QFrame#MainContainer {
                background-color: #0f172a;
                background-repeat: no-repeat;
                background-position: center;
                background-attachment: fixed;
            }
        """)

        self.setStyleSheet("""
            AdminDashboardWindow {{
                background: transparent;
            }}

            QWidget {{
                background: transparent;
            }}

            QPushButton {{
                background-color: rgba(10, 100, 229, 210);
                color: white;
                padding: 7px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: rgba(30, 10, 160, 190);
            }}

            QPushButton:pressed {{
                background-color: rgba(160, 50, 20, 255);
            }}

            QComboBox {{
                background-color: rgba(10, 100, 229, 210);
                color: white;
                padding: 5px;
                border: 1px solid #333;
                border-radius: 4px;
            }}

            QComboBox:hover {{
                background-color: rgba(30, 10, 160, 190);
            }}

            QTextEdit, QLineEdit {{
                background-color: rgba(30, 30, 30, 220);
                color: white;
            }}

            QFrame {{
                background-color: transparent;
            }}

            ImageViewer {{
                background-color: rgba(20, 20, 25, 230);
            }}

            ImageViewer QLabel {{
                background-color: rgba(20, 20, 25, 230);
                color: rgba(150, 150, 150, 200);
                border: 1px solid rgba(60, 60, 70, 180);
            }}
        """)

    def load_users(self):
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cur = conn.cursor()
                cur.execute("SELECT username, name FROM users WHERE admin = 0")
                users = cur.fetchall()
            for user in users:
                self.user_combo.addItem(f"{user[0]} - {user[1]}", user[0])
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Failed to load users:\n{e}")

    def load_user_sessions(self, index):
        if index == 0:
            self.session_combo.clear()
            self.session_combo.addItem("Select Session")
            return

        username = self.user_combo.itemData(index)
        sessions = fetch_sessions()
        self.session_combo.clear()
        self.session_combo.addItem("Select Session")
        for row in sessions:
            if row[1] == username:  # match username
                self.session_combo.addItem(f"{row[0]} - {row[8]}", row[0])

    def load_session_details(self, index):
        if index == 0:
            self.details_text.clear()
            self.input_viewer.clear()
            self.output_viewer.clear()
            return

        session_id = self.session_combo.itemData(index)
        if not session_id:
            return
            
        self.s = fetch_session_by_id(session_id)
        if not self.s:
            QMessageBox.warning(self, "Error", "Session not found")
            return

        details = f"""
Username: {self.s[1]}
Site ID: {self.s[2]}
Location: {self.s[3]}
Created At: {self.s[4]}
"""
        self.details_text.setPlainText(details.strip())

        # Load input images
        input_images = []
        input_dir = None
        if len(self.s) > 4:
            input_dir = self.s[4] if isinstance(self.s[4], str) and os.path.isdir(self.s[4]) else None
        if input_dir:
            input_images = [
                os.path.join(input_dir, f)
                for f in os.listdir(input_dir)
                if f.lower().endswith((".jpg", ".png")) and os.path.isfile(os.path.join(input_dir, f))
            ]

        # Load output images
        output_images = []
        output_dir = None
        if len(self.s) > 5:
            output_dir = self.s[5] if isinstance(self.s[5], str) and os.path.isdir(self.s[5]) else None
        if output_dir:
            for root, _, files in os.walk(output_dir):
                for f in files:
                    if f.lower().endswith((".png", ".jpg")):
                        full_path = os.path.join(root, f)
                        if os.path.isfile(full_path):
                            output_images.append(full_path)

        if input_images:
            self.input_viewer.set_images(input_images)
        else:
            self.input_viewer.clear()
            
        if output_images:
            self.output_viewer.set_images(output_images)
        else:
            self.output_viewer.clear()

    def generate_report(self):
        if not self.s:
            QMessageBox.warning(self, "Error", "No session selected")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"admin_report_{timestamp}.pdf"
        
        from PySide6.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report As",
            default_filename,
            "PDF Files (*.pdf);;All Files (*.*)"
        )
        
        if not save_path:
            return

        # Fetch analysis results for this session
        session_id = self.s[0]
        analysis_results_raw = fetch_analysis_results_by_session(session_id)

        # Convert to the simple risk-report shape expected by generate_pdf_report
        risk_data = []
        for result in analysis_results_raw:
            hazard_level = result[2] if len(result) > 2 and result[2] else "Unknown"
            description = result[3] if len(result) > 3 and result[3] else "No details"
            risk_data.append({
                "zone": description,
                "level": hazard_level,
                "gas": 0,
                "worker": "N/A",
            })

        if not risk_data:
            risk_data = [{"zone": "No data", "level": "Unknown", "gas": 0, "worker": "N/A"}]

        try:
            generate_pdf_report(
                output_path=save_path,
                manager_name=self.s[1],
                site_id=self.s[2],
                risk_data=risk_data,
                timestamp=timestamp
            )
            QMessageBox.information(self, "Report Generated", f"Report saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{str(e)}")

    def logout(self):
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.login = LoginWindow()
            self.login.show()
            self.close()
