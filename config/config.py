from .robot_config import RobotConfig
from .canvas_config import CanvasConfig
from .ai_config import ImageGenConfig
from .camera_config import CameraConfig

class Config:
    def __init__(self):
        self.robot = RobotConfig()
        self.canvas = CanvasConfig()
        self.ai = ImageGenConfig()
        self.camera = CameraConfig()