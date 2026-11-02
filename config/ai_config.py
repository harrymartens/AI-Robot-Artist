from dataclasses import dataclass

@dataclass
class ImageGenConfig:
    # The images.edit endpoint only accepts GPT-image models; the drawings reported in
    # the ACRA 2026 paper used gpt-image-1 for both generation and editing. gpt-image-1
    # was retired by OpenAI in October 2026 -- switch both to its successor when upgrading.
    model: str = "gpt-image-1"
    model_edit: str = "gpt-image-1"
    quality: str = "medium"
    size: str = "1024x1536"