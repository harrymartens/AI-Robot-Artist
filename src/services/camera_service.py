import cv2
import time
from datetime import datetime
from pathlib import Path
import platform
import numpy as np
from numpy.typing import NDArray

from config.config import Config

class CameraService:
    """
    Service for managing camera operations.
    """
    def __init__(self, config: Config):
        self.config = config
        self.camera = None
        
    def capture_photo(self, save:bool = False) -> NDArray[np.uint8]:
        # Validate camera index and ensure it's an int
        index = self.config.camera.camera_index
        try:
            index = int(index)
        except Exception:
            print(f"Invalid camera_index in config: {self.config.camera.camera_index}")
            return None

        # Try opening with a sequence of backends for robustness (macOS prefers AVFoundation)
        backends = []
        if platform.system() == 'Darwin':
            backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        cap = None
        for backend in backends:
            try:
                cap = cv2.VideoCapture(index, backend)
            except TypeError:
                # Some builds require both args; fall back to single-arg if needed
                cap = cv2.VideoCapture(index)
            if cap is not None and cap.isOpened():
                break

        if cap is None or not cap.isOpened():
            print(f"Cannot open camera (index={index}) with backends {backends}")
            return None

        start = time.time()
        while time.time() - start < self.config.camera.warmup:
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Failed to grab frame")
            return None

        if save:
            Path(self.config.camera.out_dir).mkdir(parents=True, exist_ok=True)
            filename = Path(self.config.camera.out_dir) / f"photo_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            cv2.imwrite(str(filename), frame)
            print(f"Image captured and saved to {filename}")
        else:
            print("Image captured (not saved)")

        return frame
