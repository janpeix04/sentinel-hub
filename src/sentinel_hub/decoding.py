import struct
import warnings
from typing import IO

import numpy as np
from PIL import Image


def decode_image_with_pillow(stream: IO | str) -> np.ndarray:
    """Decodes an image using `Pillow` package and handles potential warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return np.array(Image.open(stream))


def get_jp2_bit_depth(stream: IO) -> int:
    """Reads a bit encoding depth of jpeg2000 file in binary stream format."""
    stream.seek(0)

    while True:
        read_buffer = stream.read(8)
        if len(read_buffer) < 8:
            raise ValueError("Image header Box not found in JPEG2000 file.")

        _, box_id = struct.unpack(">I4s", read_buffer)

        if box_id == b"ihdr":
            read_buffer = stream.read(14)
            params = struct.unpack(">IIHBBBB", read_buffer)
            return (params[3] & 0x7F) + 1


def fix_jp2_image(image: np.ndarray, bit_depth: int) -> np.ndarray:
    """
    Because Pillow library incorrectly reads JPEG2000 images with 15-bit
    encoding this function corrects the values in image.
    """
    if bit_depth in [8, 16]:
        return image
    if bit_depth == 15:
        try:
            return image >> 1
        except TypeError as exception:
            raise OSError(
                "Failed to read JPEG2000 image correctly. Most likely reason "
                "is that Pillow did not install OpenJPEG library correctly. "
                "Try reinstalling Pillow from a wheel."
            ) from exception

    raise ValueError(f"Bit depth {bit_depth} of jp2 is currently not supported.")


def decode_jp2_image(stream: IO) -> np.ndarray:
    """Tries to decode a JPEG2000 image using `Pillow` package."""
    image = decode_image_with_pillow(stream)
    bit_depth = get_jp2_bit_depth(stream)
    return fix_jp2_image(image, bit_depth)
