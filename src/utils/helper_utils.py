import numpy as np
from numpy.typing import NDArray
from typing import Optional
import cv2



def show_images(*images: NDArray[np.uint8], wait: bool = True, window_name: str = "Images") -> None:
    """
    Display multiple images side by side.
    """
    if not images:
        return

    heights = [img.shape[0] for img in images]
    min_h = min(heights)
    resized = [
        cv2.resize(img, (int(img.shape[1] * min_h / img.shape[0]), min_h), interpolation=cv2.INTER_AREA)
        for img in images
    ]

    n_channels = [1 if img.ndim == 2 else img.shape[2] for img in resized]
    if len(set(n_channels)) > 1:
        resized = [cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img for img in resized]

    combined = np.hstack(resized)

    cv2.imshow(window_name, combined)
    if wait:
        cv2.waitKey(0)
        cv2.destroyAllWindows()