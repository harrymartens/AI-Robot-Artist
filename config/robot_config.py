from dataclasses import dataclass
from enum import Enum
from typing import Dict

from core.models import AttachmentType, SpeedType, RobotState

@dataclass
class RobotConfig:
    ip: str = "192.168.1.239"
    speed: float = 100.0
    
    current_attachment: AttachmentType = AttachmentType.MARKER
    
    current_state: RobotState = RobotState.UNKNOWN
    
    roll: float = 180.0
    pitch: float = 0.0
    yaw: float = 0.0
    
    mvacc: float = 100.0
    max_step: float = 0.05
    
    centred_position: Dict[str, float] = None
    change_tool_position: Dict[str, float] = None
    docked_position: Dict[str, float] = None
    
    speeds: Dict[str, float] = None
    attachment_z_heights: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        if self.speeds is None:
            self.speeds = {
                SpeedType.FAST: 300.0,
                SpeedType.NORMAL: 100.0,
                SpeedType.SLOW: 50.0,
            }
            
        if self.attachment_z_heights is None:
            self.attachment_z_heights = {
                AttachmentType.MARKER: {"lowered": 118.0, "raised": 125.0},
                AttachmentType.ERASER: {"lowered": 59.0, "raised": 80.0},
                AttachmentType.PEN: {"lowered": 120.0, "raised": 127.0},
                AttachmentType.EMPTY: {"lowered": 158.0, "raised": 170.0},
            }
        if self.centred_position is None:
            self.centred_position = {
                "x": 200,
                "y": 0,
            }
        if self.change_tool_position is None:
            self.change_tool_position = {
                "x": 350,
                "y": 0,
                "z": 300
            }
        if self.docked_position is None:
            self.docked_position = {
                "x": 100,
                "y": -250,
            }
            
    def get_speed(self, speed_type: SpeedType) -> float:
        """Get speed value by type."""
        return self.speeds.get(speed_type, self.speeds[SpeedType.NORMAL])
    
    def set_speed(self, speed_type: SpeedType, value: float):
        """Set speed value."""
        self.speeds[speed_type] = value
    
    def set_attachment(self, attachment: AttachmentType):
        """Change the current attachment."""
        if attachment in self.attachment_z_heights:
            self.current_attachment = attachment
        else:
            raise ValueError(f"Unknown attachment z-height: {attachment}")
        
    
    @property
    def z_lowered(self) -> float:
        """Get Z height for lowered position with current attachment."""
        return self.attachment_z_heights[self.current_attachment]["lowered"]
    
    @property
    def z_raised(self) -> float:
        """Get Z height for raised position with current attachment."""
        return self.attachment_z_heights[self.current_attachment]["raised"]
