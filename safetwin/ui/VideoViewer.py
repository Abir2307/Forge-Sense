import cv2
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QImage

class VideoViewer(QWidget):
    """
    Handles real-time video stream visualization using OpenCV frames.
    """
    def __init__(self, title="Live CCTV Feed"):
        super().__init__()
        # Title
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 12, QFont.Bold))
        self.title.setStyleSheet("background-color: rgba(33, 150, 243, 200); color: white; padding: 6px; border-radius: 4px;")

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        # Video Display Label
        self.video_label = QLabel("Waiting for Stream...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("color: #666; font-style: italic;")
        self.scroll_area.setWidget(self.video_label)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.scroll_area)

    def update_frame(self, frame):
        """
        Processes a BGR numpy array from OpenCV into a displayable QPixmap.
        """
        if frame is None:
            return

        # Convert OpenCV BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # Convert to QImage and then QPixmap
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # Scale to current label size
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

    def clear(self):
        """Reset the view."""
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("Stream Disconnected")