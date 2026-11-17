import warnings
from typing import IO

import numpy as np
from PIL import Image


def decode_image_with_pillow(stream: IO | str) -> np.ndarray:
    """Decodes an image using `Pillow` package and handles potential warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return np.array(Image.open(stream))
