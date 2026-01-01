
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Union
import base64
import io
from numpy.typing import NDArray


def base64_to_numpy(base64_str: str) -> NDArray[np.uint8]:
    """
    Convert a base64 encoded string to a numpy array.
    """
    import base64
    image_data = base64.b64decode(base64_str)
    image_array = np.frombuffer(image_data, dtype=np.uint8)
    # Decode the image using cv2.imdecode to get proper 2D array
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode base64 image data")
    return image


def scale_image(image: NDArray[np.uint8], target_dimensions: Tuple[float, float] ) -> NDArray[np.uint8]:
    target_width, target_height = target_dimensions

    original_height, original_width = image.shape[:2]

    width_ratio = target_width / original_width
    height_ratio = target_height / original_height
    scale_factor = min(width_ratio, height_ratio)

    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)

    resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return resized_image

def convert_to_grayscale(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def apply_gaussian_blur(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return cv2.GaussianBlur(image, (5, 5), 1)

def apply_canny_edge_detection(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return cv2.Canny(image, 50, 100)

def binarize_drawing(image, threshold=128):
    gray = convert_to_grayscale(image)
    blurred = apply_gaussian_blur(gray)

    _, binarized = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY_INV)

    return binarized

def numpy_to_openai_format(image: NDArray[np.uint8]) -> Union[bytes, io.BytesIO]:
    """
    Convert a numpy array to the format expected by OpenAI API.
    Returns bytes that can be passed to OpenAI's image edit API.
    """
    # Convert BGR to RGB (OpenCV uses BGR, but most APIs expect RGB)
    if len(image.shape) == 3 and image.shape[2] == 3:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        image_rgb = image
    
    # Convert to PIL Image
    pil_image = Image.fromarray(image_rgb)
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr