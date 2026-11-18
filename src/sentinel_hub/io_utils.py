import csv
import json
import logging
import os
from collections.abc import Callable
from typing import IO, Any, Literal
from xml.etree import ElementTree

import numpy as np
import tifffile as tiff
from PIL import Image

from sentinel_hub.constants import MimeType
from sentinel_hub.decoding import (
    decode_image_with_pillow,
    decode_jp2_image,
    decode_tar,
    get_data_format,
)

logger = logging.getLogger(__name__)

CSV_DELIMITER = ";"


def read_data(filename: str, data_format: MimeType | None = None) -> Any:
    """
    Read image data from file.

    This function reads input data from file. The format of the file
    can be specified in `data_format`. If not specified, the format is
    guessed from the extension of the filename.
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Filename {filename} does not exist.")

    if not isinstance(data_format, MimeType):
        data_format = get_data_format(filename)

    reader = _get_reader(data_format)

    try:
        return reader(filename)
    except BaseException:
        # In case a procedure would read a lot of files and one would be
        # corrupt this helps us figure out which one.
        logger.debug("Filed to read from file: %s", filename)
        raise


def _get_reader(data_format: MimeType) -> Callable[[str], Any]:
    """Provides a function for reading data in a given data format."""
    if data_format is MimeType.TIFF:
        return tiff.imread
    if data_format is MimeType.JP2:
        return _open_file_and_read(decode_jp2_image, "rb")
    if data_format.is_image_format():
        return decode_image_with_pillow

    available_readers: dict[MimeType, Callable[[str], Any]] = {
        MimeType.TAR: _open_file_and_read(decode_tar, "rb"),
        MimeType.TXT: _open_file_and_read(lambda file: file.read(), "r"),
        MimeType.RAW: _open_file_and_read(lambda file: file.read(), "rb"),
        MimeType.JSON: _open_file_and_read(json.load, "rb"),
        MimeType.CSV: _read_csv,
        MimeType.XML: ElementTree.parse,
        MimeType.GML: ElementTree.parse,
        MimeType.SAFE: ElementTree.parse,
        MimeType.NPY: np.load,
    }

    if data_format not in available_readers:
        raise ValueError(f"Reading data format {data_format} is not supported.")

    return available_readers[data_format]


def _open_file_and_read(
    reader: Callable[[IO], Any], mode: Literal["r", "rb"]
) -> Callable[[str], Any]:
    def new_reader(filename: str) -> Any:
        with open(filename, mode) as file:
            return reader(file)

    return new_reader


def _read_csv(filename: str, delimiter: str = CSV_DELIMITER) -> list:
    """Read data from CSV file."""
    with open(filename) as file:
        return list(csv.reader(file, delimiter=delimiter))


def write_data(
    filename: str,
    data: Any,
    data_format: MimeType | None = None,
    compress: bool = False,
    add: bool = False,
) -> None:
    """
    Write image data to file.

    Function to write image data to specified file. If file format is not provided
    explicitly, it is guessed from the filename extension. If format is TIFF, geo
    information and compression can be optionally added.
    """
    _create_parent_folder(filename)

    if not isinstance(data_format, MimeType):
        data_format = get_data_format(filename)

    if data_format is MimeType.TIFF:
        tiff.imwrite(filename, data, compression=("lmza" if compress else None))
    elif data_format.is_image_format():
        Image.fromarray(data).save(filename)
    elif data_format is MimeType.NPY:
        np.save(filename, data)
    elif data_format in (MimeType.XML, MimeType.GML):
        data.write(filename)
    elif data_format is MimeType.TXT:
        with open(filename, "a" if add else "w") as file:
            print(data, end="", file=file)
    elif data_format is MimeType.RAW:
        with open(filename, "wb") as file:
            file.write(data)
    elif data_format is MimeType.CSV:
        with open(filename, "w") as file:
            csv_writer = csv.writer(file, delimiter=CSV_DELIMITER)
            for line in data:
                csv_writer.writerow(line)
    elif data_format is MimeType.JSON:
        with open(filename, "w") as file:
            json.dump(data, file, indent=4, sort_keys=True)
    else:
        raise ValueError(f"Writting data format {data_format} is not supported.")


def _create_parent_folder(filename: str) -> None:
    path = os.path.dirname(filename)
    if path != "":
        os.makedirs(path, exist_ok=True)
