from dataclasses import dataclass

@dataclass
class CameraConfig:
    """Camera configuration for capturing images."""
    camera_index: int = 0
    warmup: float = 1.0
    save: bool = True
    out_dir: str = "images/captured"