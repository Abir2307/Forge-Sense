import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog
from PySide6.QtGui import Qt
from PySide6.QtGui import QPixmap, QFont, QIcon

class QrPopup(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hazard Access QR Codes")
        self.resize(500, 550)
        
        self.images = image_paths or []
        self.index = 0

        # Style for Industrial Aesthetic
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: #e0e0e0; font-size: 14px; }
            QPushButton { 
                background-color: #2196F3; color: white; 
                padding: 8px 15px; border-radius: 5px; font-weight: bold; 
            }
            QPushButton:disabled { background-color: #555; }
        """)

        # UI Elements
        self.image_label = QLabel("Loading QR...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #000; border: 2px solid #333; border-radius: 10px;")

        self.counter_label = QLabel("0 / 0")
        self.counter_label.setAlignment(Qt.AlignCenter)

        # Buttons
        self.btn_prev = QPushButton("◀ Prev")
        self.btn_next = QPushButton("Next ▶")
        self.btn_save = QPushButton("Save QR")
        self.btn_close = QPushButton("Close")

        self.btn_prev.clicked.connect(self.prev_image)
        self.btn_next.clicked.connect(self.next_image)
        self.btn_save.clicked.connect(self.save_qr)
        self.btn_close.clicked.connect(self.close)

        # Layout
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.btn_prev)
        nav_row.addWidget(self.counter_label)
        nav_row.addWidget(self.btn_next)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label, stretch=1)
        layout.addLayout(nav_row)
        layout.addLayout(btn_row)

        self.show_image()

    def show_image(self):
        if not self.images:
            self.image_label.setText("No QR image available")
            self.counter_label.setText("0 / 0")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            return

        image_path = self.images[self.index]
        if not os.path.exists(image_path):
            self.image_label.setText(f"QR image missing:\n{image_path}")
            self.counter_label.setText(f"Hazard QR {self.index + 1} / {len(self.images)}")
            self.btn_prev.setEnabled(self.index > 0)
            self.btn_next.setEnabled(self.index < len(self.images) - 1)
            return

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("QR image could not be loaded")
        
        self.counter_label.setText(f"Hazard QR {self.index + 1} / {len(self.images)}")
        self.btn_prev.setEnabled(self.index > 0)
        self.btn_next.setEnabled(self.index < len(self.images) - 1)

    def save_qr(self):
        """Allows user to export the QR code to their local machine."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export QR", f"hazard_qr_{self.index}.png", "PNG Files (*.png)")
        if file_path:
            pixmap = QPixmap(self.images[self.index])
            pixmap.save(file_path)

    def prev_image(self):
        if self.index > 0:
            self.index -= 1
            self.show_image()

    def next_image(self):
        if self.index < len(self.images) - 1:
            self.index += 1
            self.show_image()