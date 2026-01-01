from dataclasses import dataclass

@dataclass
class ImageGenConfig:
    model: str = "gpt-image-1"
    model_edit: str = "gpt-4o"
    quality: str = "medium"
    size: str = "1024x1536"