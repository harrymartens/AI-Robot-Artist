import numpy as np
from numpy.typing import NDArray

from scipy.spatial import distance


from config.config import Config
from services.image_processing_service import ImageProcessingService

import utils.image_utils as image_utils


class PathPlanningService:
    def __init__(self, config: Config, image_processing_service: ImageProcessingService):
    
        self.config = config
        self.image_processing_service = image_processing_service
            
    def convert_image_to_vectors(self, line_image: NDArray[np.uint8]) -> list:
        """
        Convert a image to a vector collection.
        """
                
        return self._extract_contours(line_image)
       
       
    def _extract_contours(self, orig_image: NDArray[np.uint8]) -> list:
        """
        Extract contours from canny image.
        """
        h, w = orig_image.shape
        visited = np.zeros((h, w), dtype=bool)
        contours = []
        
        # Define 8-connected neighbor offsets.
        neighbor_offsets = [(-1, -1), (-1, 0), (-1, 1),
                            ( 0, -1),           ( 0, 1),
                            ( 1, -1), ( 1, 0),  ( 1, 1)]
        
        def dfs(start_i, start_j):
            contour = []
            stack = [(start_i, start_j)]
            
            while stack:
                i, j = stack.pop()
                if visited[i, j]:
                    continue
                visited[i, j] = True
                contour.append((j, i))  # store as (x, y)
                for di, dj in neighbor_offsets:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w:
                        if not visited[ni, nj] and orig_image[ni, nj] != 0:
                            stack.append((ni, nj))
            return contour

        def reorder_contour(points):
            """
            Reorder a list of points using a nearest neighbor approach. If the nearest unvisited
            point is too far (exceeding a maximum squared distance), break the chain and start
            a new segment.
            """
            # Maximum allowed squared distance between connected points.
            # Since adjacent pixels are 1 or sqrt(2) apart, a threshold of 5 works well.
            max_distance_sq = 5  
            segments = []
            # Work on a copy so as not to modify the original list.
            points = points.copy()
            
            while points:
                current_segment = []
                # Start with the first available point.
                current = points.pop(0)
                current_segment.append(current)
                while points:
                    nearest_index = None
                    nearest_distance = None
                    for i, pt in enumerate(points):
                        dx = pt[0] - current[0]
                        dy = pt[1] - current[1]
                        dist_sq = dx*dx + dy*dy
                        if nearest_distance is None or dist_sq < nearest_distance:
                            nearest_distance = dist_sq
                            nearest_index = i
                    # If the nearest point is within the allowed distance, add it.
                    if nearest_distance is not None and nearest_distance <= max_distance_sq:
                        current = points.pop(nearest_index)
                        current_segment.append(current)
                    else:
                        # Otherwise, break this segment and start a new one.
                        break
                segments.append(current_segment)
            return segments

        # Iterate over every pixel.
        for i in range(h):
            for j in range(w):
                if orig_image[i, j] != 0 and not visited[i, j]:
                    raw_contour = dfs(i, j)
                    if len(raw_contour) > 1:
                        # Reorder the DFS points using nearest neighbor.
                        ordered_segments = reorder_contour(raw_contour)
                        for seg in ordered_segments:
                            # Only add segments with at least 2 points.
                            if len(seg) > 1:
                                contours.append(seg)
        return contours
    
    def plan_erase_path(self, image: NDArray[np.uint8]) -> list:
        """
        Plan an erase path for the given image.
        """
        eraser_w_px = 80
        eraser_h_px = 40
        bin_img = image_utils.binarize_drawing(image)        
            
        centers, rects = self._plan_eraser_centers(bin_img, eraser_w_px, eraser_h_px)
        vectors = [centers]
        
        return vectors
    
    def _plan_eraser_centers(bin_img, rect_w, rect_h):
        """
        Plan minimal-movement eraser path using dynamic region coverage.
        Ensures all ink is erased, avoids unnecessary extra steps.
        """
        h, w = bin_img.shape
        covered = np.zeros_like(bin_img, dtype=bool)

        # 1. Get all ink pixel coordinates
        ink_coords = np.argwhere(bin_img > 0)
        if len(ink_coords) == 0:
            return [], []

        erase_centers = []
        rects = []

        # 2. Start from top-left ink pixel
        remaining = set(map(tuple, ink_coords))
        current = min(remaining, key=lambda pt: pt[1] + pt[0])  # top-left
        current = tuple(current)

        def mark_covered(center):
            """Mark the region covered by an erase centered at `center`."""
            cx, cy = center
            x1 = max(0, cx - rect_h // 2)
            y1 = max(0, cy - rect_w // 2)
            x2 = min(h, cx + rect_h // 2)
            y2 = min(w, cy + rect_w // 2)
            covered[x1:x2, y1:y2] = True

        while remaining:
            cx, cy = current
            erase_centers.append((cy, cx))  # switch to (x, y) format for consistency
            rects.append((cy - rect_w // 2, cx - rect_h // 2))
            mark_covered((cx, cy))

            # 3. Remove covered ink pixels
            newly_remaining = []
            for pt in remaining:
                if not covered[pt]:
                    newly_remaining.append(pt)
            remaining = set(newly_remaining)

            if not remaining:
                break

            # 4. Pick the nearest uncovered ink point to current position
            dists = distance.cdist([current], list(remaining))
            current = list(remaining)[np.argmin(dists)]

        return erase_centers, rects
    