from dataclasses import dataclass
from typing import Tuple


@dataclass
class CanvasConfig:
    """Canvas configuration for drawing."""
    min_x: float = 235.0
    max_x: float = 415.0
    min_y: float = -190.0
    max_y: float = 190.0
    
    width: float = max_x-min_x
    height: float = max_y-min_y
    
    @property
    def dimensions(self) -> Tuple[float, float]:
        """Get canvas dimensions - (width,height)."""
        return (self.width, self.height)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get canvas center coordinates - (x,y)."""
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)
    
    def is_within_bounds(self, x: float, y: float) -> bool:
        """Check if coordinates are within canvas bounds."""
        return (self.min_x <= x <= self.max_x and 
                self.min_y <= y <= self.max_y)
