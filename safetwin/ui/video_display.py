from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class _VideoReaderThread(QThread):
    frame_ready = Signal(object)
    status_message = Signal(str)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        capture = cv2.VideoCapture(self.source)
        if not capture.isOpened():
            self.status_message.emit(f"Unable to open video source: {self.source}")
            return

        is_local_file = isinstance(self.source, (str, Path)) and Path(str(self.source)).exists()
        frame_delay_ms = int(1000 / max(capture.get(cv2.CAP_PROP_FPS), 25))

        while self._running:
            ret, frame = capture.read()
            if not ret:
                if is_local_file:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                self.msleep(25)
                continue

            self.frame_ready.emit(frame)
            self.msleep(frame_delay_ms)

        capture.release()


class VideoDisplay(QWidget):
    """Display a video file, webcam feed, or RTSP stream without blocking the UI."""

    def __init__(self, parent=None, title: str = "Video Feed"):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._current_source = None
        self._reader_thread = None
        self._last_pixmap = QPixmap()

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.title_label.setStyleSheet(
            "background-color: rgba(2, 48, 89, 220); color: white; padding: 6px; border-radius: 4px;"
        )

        self.video_label = QLabel("Select a video file or start a live source")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(320)
        self.video_label.setStyleSheet("background: #111827; color: #cbd5e1; border: 1px solid #334155;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.video_label, stretch=1)

    def set_source(self, source):
        self.stop()
        self._current_source = source
        self.video_label.setText("Connecting to source...")
        self.video_label.setPixmap(QPixmap())

        self._reader_thread = _VideoReaderThread(source, self)
        self._reader_thread.frame_ready.connect(self._update_frame)
        self._reader_thread.status_message.connect(self.video_label.setText)
        self._reader_thread.start()

    def stop(self):
        if self._reader_thread is None:
            return

        self._reader_thread.stop()
        self._reader_thread.wait(1500)
        self._reader_thread.deleteLater()
        self._reader_thread = None

    def clear(self):
        self.stop()
        self._last_pixmap = QPixmap()
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("Stream stopped")

    def _update_frame(self, frame):
        if frame is None:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self._apply_scaled_pixmap()

    def show_frame(self, frame):
        """Display a processed BGR `frame` (numpy array) immediately in the widget.

        This is used by the analysis pipeline to show annotated frames instead
        of the raw reader thread frames.
        """
        if frame is None:
            return

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            return

        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self._apply_scaled_pixmap()

    def show_frame(self, frame):
        """Display a processed BGR `frame` (numpy array) immediately in the widget.

        This is used by the analysis pipeline to show annotated frames instead
        of the raw reader thread frames.
        """
        if frame is None:
            return

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            return

        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self._apply_scaled_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self):
        if self._last_pixmap.isNull():
            return

        scaled = self._last_pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)
