from numpy.typing import NDArray
from typing import List

import numpy as np
import cv2


from config.config import Config
from services.robot_service import RobotService

class MovementService:
    """Service for managing robot movements."""
    
    def __init__(self, config: Config, robot_service: RobotService):
        self.config = config
        self.robot_service = robot_service
        
    def _map_pixel_to_canvas(self, pixel, scaling_factor):
        min_x = self.config.canvas.min_x
        min_y = self.config.canvas.min_y
        max_x = self.config.canvas.max_x
        max_y = self.config.canvas.max_y
        
        x_pixel, y_pixel = pixel

        x_robot = min_x + x_pixel * scaling_factor
        y_robot = min_y + y_pixel * scaling_factor

        x_robot = max(min_x, min(max_x, x_robot))
        y_robot = max(min_y, min(max_y, y_robot))

        return int(x_robot), int(y_robot)



    def _simplify_segment(self, segment, epsilon=2.0):
        """
        Simplifies a list of (x, y) points using the Ramer-Douglas-Peucker algorithm.
        """
        if len(segment) < 3:
            return segment  # Not enough points to simplify

        # Convert to format required by cv2.approxPolyDP
        pts = np.array(segment, dtype=np.int32).reshape((-1, 1, 2))
        simplified = cv2.approxPolyDP(pts, epsilon=epsilon, closed=False)
        
        return [tuple(pt[0]) for pt in simplified]
        
    
    def follow_vectors(self, vectors: List, line_image: NDArray[np.uint8], simplify: bool = True):
        """
        Follow a collection of vectors on the canvas.
        """

        canvas_width, canvas_height = self.config.canvas.dimensions
        
        drawing_height, drawing_width = line_image.shape[:2]
        
        scale_x = canvas_width / drawing_width
        scale_y = canvas_height / drawing_height
        scaling_factor = min(scale_x, scale_y)

        for seg in vectors:
            if not seg:
                continue

            if simplify:
                seg = self._simplify_segment(seg)


            first_pt = seg[0]
            start_x, start_y = self._map_pixel_to_canvas(first_pt, scaling_factor)
            
            self.robot_service.move_canvas_position(start_x, start_y)

            for pt in seg:
                x_robot, y_robot = self._map_pixel_to_canvas(pt, scaling_factor)
                self.robot_service.move_canvas_position(x_robot, y_robot, raised=False)

            self.robot_service.move_canvas_position(x_robot, y_robot, raised=False)