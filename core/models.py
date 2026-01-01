from enum import Enum


class AttachmentType(Enum):
    """Robot attachment types."""
    MARKER = "marker"
    ERASER = "eraser"
    PEN = "pen"
    EMPTY = "empty"
    
class SpeedType(Enum):
    """Robot speed types."""
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"
    
class RobotState(Enum):
    """Robot positional states."""
    MOVING = "moving"
    PAUSED = "paused"
    CENTRED = "resting"
    DOCKED = "docked"
    TOOL_CHANGE = "tool_change"
    UNKNOWN = "unknown"
    CALCULATING = "calculating"
    