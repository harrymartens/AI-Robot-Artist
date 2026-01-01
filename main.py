#!/usr/bin/env python3
"""
Main entry point for the Creative Robotic Assistant.
This file provides a clean interface to use the drawing tools functionality.
"""

import sys
import os
import argparse
import traceback
from typing import Optional

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pyfiglet import Figlet
f = Figlet(font='slant')


from config.config import Config
from services.image_generation_service import ImageGenerationService
from services.image_processing_service import ImageProcessingService
from services.path_planning_service import PathPlanningService
from services.movement_service import MovementService
from services.robot_service import RobotService
from services.camera_service import CameraService
from tools.drawing_tool import DrawingTools

from core.models import  SpeedType

BANNER_ARM_ART = r"""
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░█████████████████████████████░
░█████████████████████████████░
░█████████████▓▓▒░░▒▒▒▓███████░
░████████████▒████████████████░
░████████████████░░░░░░███████░
░███████▓▓▒▓█░░▓████████▓█████░
░██████▓█████████░▓▓░░░█░▒████░
░█████▓████▒░██▓█▓▒██▒░███████░
░██████░█▓▓███▓█████▒██▓▓▒████░
░█████▓███████▓█████░██▓█▒████░
░████▒████▓██▒███▓░░▓███▓▓█▓██░
░██▓▒░██████▒██████████▓▒█▓███░
░▓▒█████░░▒▓█████▒▓█░░▓▒██████░
░▓████▒▓█████████████████▓████░
░▓▒▓▒▓▓██████████░░░░█▒▒██████░
░█████████████████████████████░
░██████████████▓█▓▒▒▒█▓███████░
░█████████████▓▒█▒░░░█▒▒▓█████░
░█████████████████████████████░
░█████████████▓▒▒▒░░░▒▒▓▓█████░
░█████████████████████████████░
░█████████████████████████████░
░█████████████████████████████░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
"""


def print_banner() -> None:
    """Render the figlet title and place the robot art to its right."""
    figlet_lines = f.renderText("Creative Robotic Assistant").rstrip("\n").splitlines()
    art_lines = BANNER_ARM_ART.strip("\n").splitlines()

    # Vertically center the two blocks by padding the shorter one.
    figlet_len, art_len = len(figlet_lines), len(art_lines)
    if figlet_len < art_len:
        top_pad = (art_len - figlet_len) // 2
        figlet_lines = [""] * top_pad + figlet_lines + [""] * (art_len - figlet_len - top_pad)
    elif art_len < figlet_len:
        top_pad = (figlet_len - art_len) // 2
        art_lines = [""] * top_pad + art_lines + [""] * (figlet_len - art_len - top_pad)

    left_width = max((len(line) for line in figlet_lines), default=0)
    spacer = "   "
    for left, right in zip(figlet_lines, art_lines):
        print(f"{left.ljust(left_width)}{spacer}{right}")

class CreativeRoboticAssistant:
    """
    Main class that orchestrates all services and provides drawing functionality.
    """
    
    def __init__(self):
        """Initialize all services and the drawing tools."""
        print("Initializing Creative Robotic Assistant...")
        
        # Initialize configuration
        self.config = Config()
        
        # Initialize services in dependency order
        # 1. Basic services that only need config
        self.image_generation_service = ImageGenerationService(self.config)
        self.image_processing_service = ImageProcessingService(self.config)
        self.robot_service = RobotService(self.config)
        self.camera_service = CameraService(self.config)
        
        # 2. Services that depend on other services
        self.path_planning_service = PathPlanningService(self.config, self.image_processing_service)
        self.movement_service = MovementService(self.config, self.robot_service)
        
        # Initialize drawing tools
        self.drawing_tools = DrawingTools(
            image_generation_service=self.image_generation_service,
            image_processing_service=self.image_processing_service,
            path_planning_service=self.path_planning_service,
            movement_service=self.movement_service,
            robot_service=self.robot_service,
            camera_service=self.camera_service
        )
        
        print("Creative Robotic Assistant initialized successfully!")
        
        # Show any existing errors
        error_summary = self.robot_service.get_error_summary()
        if "No errors recorded" not in error_summary:
            print("\n⚠️  Robot Error Summary:")
            print(error_summary)
    
    def generate_and_draw(self, prompt: str):
        """
        Generate an image from a prompt and draw it on the canvas.
        
        Args:
            prompt (str): Text description of the image to generate and draw
        """
        print(f"Generating and drawing: {prompt}")
        try:
            self.drawing_tools.generate_and_draw(prompt)
            print("✅ Image generated and drawn successfully!")
        except Exception as e:
            print(f"❌ Error during generate and draw: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    def edit_and_draw(self, prompt: str):
        """
        Edit the current canvas based on a prompt and draw the result.
        
        Args:
            prompt (str): Text description of how to edit the current drawing
        """
        print(f"Editing and drawing: {prompt}")
        try:
            self.drawing_tools.edit_and_draw(prompt)
            print("✅ Image edited and drawn successfully!")
        except Exception as e:
            print(f"❌ Error during edit and draw: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    def draw_image(self, image_path: str):
        """
        Draw an existing image from a file path.
        
        Args:
            image_path (str): Path to the image file to draw
        """
        print(f"Drawing image from: {image_path}")
        try:
            import cv2
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            self.drawing_tools.draw_image(image)
            print("✅ Image drawn successfully!")
        except Exception as e:
            print(f"❌ Error during image drawing: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    def erase_canvas(self):
        """Erase the entire canvas."""
        print("Erasing canvas...")
        try:
            # Capture current canvas to get dimensions for erasing
            canvas_image = self.drawing_tools.capture_canvas()
            self.drawing_tools.erase_canvas(canvas_image)
            print("✅ Canvas erased successfully!")
        except Exception as e:
            print(f"❌ Error during canvas erasing: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    def capture_canvas(self, save_path: Optional[str] = None):
        """
        Capture an image of the current canvas.
        
        Args:
            save_path (str, optional): Path to save the captured image. If None, returns the image array.
        """
        print("Capturing canvas...")
        try:
            canvas_image = self.drawing_tools.capture_canvas()
            
            if save_path:
                import cv2
                cv2.imwrite(save_path, canvas_image)
                print(f"✅ Canvas captured and saved to: {save_path}")
            else:
                print("✅ Canvas captured successfully!")
                return canvas_image
                
        except Exception as e:
            print(f"❌ Error during canvas capture: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise


def main():
    """Main entry point with command line interface."""
    parser = argparse.ArgumentParser(description="Creative Robotic Assistant - Drawing Tool")
    parser.add_argument("--action", "-a", required=True, 
                       choices=["generate", "edit", "draw", "erase", "capture"],
                       help="Action to perform")
    parser.add_argument("--prompt", "-p", 
                       help="Text prompt for generation or editing")
    parser.add_argument("--path", "-p", 
                       help="Path to image file for input or output")
    
    args = parser.parse_args()
    
    # Initialize the assistant
    assistant = CreativeRoboticAssistant()
    
    try:
        if args.action == "generate":
            if not args.prompt:
                print("❌ Error: --prompt is required for generate action")
                sys.exit(1)
            assistant.generate_and_draw(args.prompt)
            
        elif args.action == "edit":
            if not args.prompt:
                print("❌ Error: --prompt is required for edit action")
                sys.exit(1)
            assistant.edit_and_draw(args.prompt)
            
        elif args.action == "draw":
            if not args.path:
                print("❌ Error: --path is required for image drawing action")
                sys.exit(1)
            assistant.draw_image(args.path)
            
        elif args.action == "erase":
            assistant.erase_canvas()
            
        elif args.action == "capture":
            assistant.capture_canvas(args.path)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Example usage without command line arguments
    if len(sys.argv) == 1:

        print_banner()
        print("═" * 60)
        print("Talk to the robot with the commands below:")
        print("  1) ✨ generate <prompt>   • Imagine an image and draw it")
        print("  2) 🪄 edit <prompt>       • Tweak the current canvas")
        print("  3) 🖼️ draw <image_path>    • Trace an existing image")
        print("  4) 🧽 erase               • Clear the canvas")
        print("  5) 📸 capture [save_path] • Snapshot the canvas")
        print("  6) 🚦 errors              • Show robot status")
        print("  7) 🚪 quit                • Exit")
        print("═" * 60)
        
        assistant = CreativeRoboticAssistant()
        
        while True:
            try:
                command = input("\nEnter command: ").strip().split()
                if not command:
                    continue
                    
                action = command[0].lower()
                
                if action == "quit" or action == "exit":
                    print("Goodbye!")
                    break
                    
                elif action == "generate":
                    if len(command) < 2:
                        print("❌ Error: Please provide a prompt")
                        continue
                    prompt = " ".join(command[1:])
                    assistant.generate_and_draw(prompt)
                    
                elif action == "edit":
                    if len(command) < 2:
                        print("❌ Error: Please provide a prompt")
                        continue
                    prompt = " ".join(command[1:])
                    assistant.edit_and_draw(prompt)
                    
                elif action == "draw":
                    if len(command) < 2:
                        print("❌ Error: Please provide an image path")
                        continue
                    image_path = command[1]
                    assistant.draw_image(image_path)
                    
                elif action == "erase":
                    assistant.erase_canvas()
                    
                elif action == "capture":
                    save_path = command[1] if len(command) > 1 else None
                    assistant.capture_canvas(save_path)
                    
                elif action == "errors":
                    error_summary = assistant.robot_service.get_error_summary()
                    print(error_summary)
                    
                else:
                    print(f"❌ Unknown command: {action}")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Full traceback:")
                traceback.print_exc()
    else:
        # Run with command line arguments
        main()
