import cv2
import time
from PySide6.QtCore import QThread, Signal

class VideoStreamThread(QThread):
    """Background thread to read a video file and emit frames continuously."""
    frame_ready = Signal(object)  # Emits the raw numpy array (OpenCV frame)

    def __init__(self, video_path="assets/demo_factory.mp4"):
        super().__init__()
        self.video_path = video_path
        self.running = False

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.video_path)
        
        # Calculate delay to play at normal speed
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = 1.0 / fps if fps > 0 else 0.033  # Default to ~30 FPS

        while self.running:
            ret, frame = cap.read()
            if not ret:
                # Video ended, loop back to the beginning
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            self.frame_ready.emit(frame)
            time.sleep(delay)
            
        cap.release()

    def stop(self):
        self.running = False
        self.wait()