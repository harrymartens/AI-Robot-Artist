"""
Image service for generating and editing images using OpenAI.
"""

import numpy as np
from numpy.typing import NDArray

from openai import OpenAI
try:
    from yaspin import yaspin
    from yaspin.spinners import Spinners
except Exception:  # pragma: no cover - optional dependency
    yaspin = None
    Spinners = None
import contextlib

from config.config import Config
from utils.image_utils import base64_to_numpy, numpy_to_openai_format

class ImageGenerationService:
    """
    Service for generating and editing images using OpenAI.
    """
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI()
        
    def generate_image(self, prompt: str) -> NDArray[np.uint8]:
        """
        Generate an image from a text prompt.
        """
        spinner_ctx = (
            yaspin(text="Generating image", color="cyan", spinner=Spinners.pong)
            if yaspin and Spinners else
            (yaspin(text="Generating image", color="cyan") if yaspin else contextlib.nullcontext())
        )
        with spinner_ctx as sp:
            result = self.client.images.generate(
                model=self.config.ai.model,
                prompt=prompt,
                quality=self.config.ai.quality,
                size=self.config.ai.size,
            )
            image_base64 = result.data[0].b64_json
            if yaspin and sp:
                sp.ok("✅")
            return base64_to_numpy(image_base64)
        

    def edit_image(self, original_image: NDArray[np.uint8], prompt: str) -> NDArray[np.uint8]: 
        """
        Generate an image from a text prompt.
        """
        spinner_ctx = (
            yaspin(text="Editing image", color="cyan", spinner=Spinners.pong)
            if yaspin and Spinners else
            (yaspin(text="Editing image", color="cyan") if yaspin else contextlib.nullcontext())
        )
        with spinner_ctx as sp:
            # Convert numpy array to OpenAI-compatible format
            image_bytes = numpy_to_openai_format(original_image)
            
            response = self.client.images.edit(
                model=self.config.ai.model_edit,
                image=image_bytes,
                prompt=prompt,
                size=self.config.ai.size,
            )
            image_base64 = response.data[0].b64_json
            if yaspin and sp:
                sp.ok("✅")
            return base64_to_numpy(image_base64) 
    
    def describe_image(self, image: NDArray[np.uint8]) -> str:
        """
        Get a description of an image.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the object in the drawing in 50 words or less."},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{image}",
                        },
                    ],
                }
            ],
        )
        
        return response.choices[0].message.content