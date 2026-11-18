import json
import struct
import tarfile
import warnings
from io import BytesIO
from typing import IO, Any

import numpy as np
import tifffile as tiff
from PIL import Image
from xml.etree import ElementTree

from sentinel_hub.constants import MimeType
from sentinel_hub.exception import ImageDecodingError


def decode_data(response_content: bytes, data_type: MimeType) -> Any:
    """Interprets downloaded data and returns it."""
    if data_type is MimeType.JSON:
        response_text = response_content.decode("utf-8")
        if not response_text:
            return response_text
        return json.loads(response_text)
    if data_type is MimeType.TAR:
        return decode_tar(response_content)
    if MimeType.is_image_format(data_type):
        return decode_image(response_content, data_type)
    if (
        data_type is MimeType.XML
        or data_type is MimeType.GML
        or data_type is MimeType.SAFE
    ):
        return ElementTree.fromstring(response_content)

    try:
        return {
            MimeType.RAW: response_content,
            MimeType.TXT: response_content,
            MimeType.ZIP: BytesIO(response_content),
        }[data_type]
    except KeyError as exception:
        raise ValueError(
            f"Decoding data format {data_type} is not supported."
        ) from exception


def decode_image(data: bytes, image_type: MimeType) -> np.ndarray:
    """
    Decodes the image provided in various formats, i.e. png, 16-bit float tiff,
    32-bit float tiff, jp2 and returns it as a numpy array.
    """
    bytes_data = BytesIO(data)

    if image_type is MimeType.TIFF:
        image = tiff.imread(bytes_data)
    elif image_type is MimeType.JP2:
        image = decode_jp2_image(bytes_data)
    else:
        image = decode_image_with_pillow(bytes_data)

    if image is None:
        raise ImageDecodingError("Unable to decode image.")
    return image


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


def decode_tar(data: bytes | BytesIO) -> dict[str, object]:
    """A decoder to convert response bytes into a dictionary of {filename: value}."""
    if isinstance(data, bytes):
        data = BytesIO(data)

    with tarfile.open(fileobj=data) as tar:
        decoded_files = {}
        for member in tar.getmembers():
            file = tar.extractfile(member)
            if file is not None:
                decoded_files[member.name] = decode_data(
                    file.read(), get_data_format(member.name)
                )
        return decoded_files


def get_data_format(filename: str) -> MimeType:
    """Util function to guess format from filename extension."""
    extension = filename.split(".")[-1]
    return MimeType.from_string(extension)
