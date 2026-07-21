from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, 
    QGraphicsOpacityEffect, QGraphicsColorizeEffect
)
from PySide6.QtGui import QCloseEvent, QTextCursor, QColor
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
class LogPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Safety Monitor Log")
        self.setGeometry(500, 200, 600, 400)

        # Style updated to look more "Industrial"
        self.setStyleSheet("""
            QDialog { background: #1a1a1a; border-radius: 10px; }
            QTextEdit { 
                background: #000; color: #00ff00; 
                font-family: 'Courier New'; padding: 10px; 
            }
            QPushButton { 
                background: #d32f2f; color: white; font-weight: bold; 
                border-radius: 5px; padding: 8px; 
            }
        """)

        layout = QVBoxLayout(self)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.stop_btn = QPushButton("STOP MONITORING")
        self.stop_btn.clicked.connect(self.request_stop)
        
        layout.addWidget(self.log_text)
        layout.addWidget(self.stop_btn)

    def append_log(self, message, color="#ffffff"):
        """Append permanent logs (alerts, system starts)"""
        timestamp = QTimer().singleShot(0, lambda: None) # placeholder logic
        html = f'<span style="color: {color};">[{message}]</span><br>'
        self.log_text.insertHtml(html)
        self.log_text.moveCursor(QTextCursor.End)

    def update_status(self, message):
        """
        Refactored: Instead of creating new logs, this method can update 
        a status header or refresh a specific line to avoid log flooding.
        """
        # Logic to update a single "Status Line" at the top of the log
        pass

    def request_stop(self):
        if self.parent_window and hasattr(self.parent_window, 'stop_flag'):
            self.parent_window.stop_flag["stop"] = True
            self.append_log("⛔ Stop signal sent to engine...", color="#ff4444")
            self.stop_btn.setEnabled(False)

    def trigger_alert_flash(self):
        """Flashes red when a Safety Hazard is detected."""
        effect = QGraphicsColorizeEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"color")
        anim.setDuration(400)
        anim.setStartValue(QColor(255, 0, 0, 0))
        anim.setKeyValueAt(0.5, QColor(255, 0, 0, 150))
        anim.setEndValue(QColor(255, 0, 0, 0))
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        anim.start()