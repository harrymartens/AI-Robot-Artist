
from services.image_generation_service import ImageGenerationService
from services.image_processing_service import ImageProcessingService
from services.path_planning_service import PathPlanningService
from services.movement_service import MovementService
from services.robot_service import RobotService
from services.camera_service import CameraService

import numpy as np
from numpy.typing import NDArray
import cv2

from core.models import RobotState, SpeedType, AttachmentType

class DrawingTools:
    def __init__(self, 
                 image_generation_service: ImageGenerationService, 
                 image_processing_service: ImageProcessingService, 
                 path_planning_service: PathPlanningService,
                 movement_service: MovementService,
                 robot_service: RobotService,
                 camera_service: CameraService):
        self.image_generation_service = image_generation_service
        self.image_processing_service = image_processing_service
        self.path_planning_service = path_planning_service
        self.movement_service = movement_service
        self.robot_service = robot_service
        self.camera_service = camera_service
        
        
    def generate_and_draw(self, prompt: str):
        """
        Generate an image from a prompt and convert it to a vector collection for drawing.
        """
        
        generated_image = self.image_generation_service.generate_image(prompt)
        
        self.draw_image(generated_image)
        
        
        
    def edit_and_draw(self, prompt: str):
        """
        Edit an existing image based on a prompt.
        """
        
        cropped_canvas_image = self.capture_canvas()
        
        generated_edit_image = self.image_generation_service.edit_image(cropped_canvas_image, prompt)
                
        # Erase Image
        self.erase_canvas(cropped_canvas_image)

        # Draw Image
        self.draw_image(generated_edit_image)
        
        
        
    def draw_image(self, image: NDArray[np.uint8]):
        line_image = self.image_processing_service.convert_to_line_image(image)
        
        vector_collection = self.path_planning_service.convert_image_to_vectors(line_image)
        
        if self.robot_service.get_attachment() != AttachmentType.MARKER:
            self._change_attachment(AttachmentType.MARKER)
            
        self.movement_service.follow_vectors(vector_collection, line_image)
        
        self.robot_service.move_docked_position()
        
        print("Drawing completed successfully.")
        
        
    def erase_canvas(self, image: NDArray[np.uint8]):
        """
        Erase the entire canvas.
        """
            
        if (self.robot_service.get_attachment() != AttachmentType.ERASER):
            self._change_attachment(AttachmentType.ERASER)
        
        # Erase Image
        erase_vectors = self.path_planning_service.plan_erase_path(image)
        self.movement_service.follow_vectors(erase_vectors, image)
        
        self.robot_service.move_docked_position()

        print("Erasing completed successfully.")
        
        
        
    def capture_canvas(self) -> NDArray[np.uint8]:
        """
        Capture an image of the canvas using the camera service.
        """
        if self.robot_service.get_robot_state() != RobotState.DOCKED:
            self.robot_service.move_docked_position(SpeedType.SLOW)
        
        canvas_image = self.camera_service.capture_photo(save=False)
        cropped_canvas_image = self.image_processing_service.crop_to_AprilTags(canvas_image)
        
        return cropped_canvas_image
        
        
        
    def _change_attachment(self, attachment: AttachmentType):
        """
        Change the robot's attachment.
        """
            
        self.robot_service.move_change_tool_position()
        
        _ = input(f"Change to {attachment.name} and press Enter to continue...")
        self.robot_service.change_attachment(attachment)
        
        self.robot_service.move_centred_position()
        
        
        
        
        
        
        

        
        
        
        
