import os

import numpy as np
import pytest
from requests import Response

from sentinel_hub.decoding import (
    decode_image,
    decode_sentinel_hub_error_msg,
    decode_tar,
    get_data_format,
)


@pytest.mark.parametrize(
    ("filename", "expected_shape", "expected_dtype", "expected_mean"),
    [
        ("img.png", (2048, 2048, 3), np.uint8, 52.33736),
        ("img.jpg", (2048, 2048, 3), np.uint8, 52.41242),
        ("img.tif", (2048, 2048, 3), np.uint16, 13577.49491),
        ("img-8bit.jp2", (343, 343, 3), np.uint8, 47.09060),
        ("img-15bit.jp2", (1830, 1830), np.uint16, 0.3041897),
        ("img-16bit.jp2", (1830, 1830), np.uint16, 0.3041897),
    ],
)
def test_decode_image(
    input_folder: str,
    filename: str,
    expected_shape: tuple[int, ...],
    expected_dtype: type,
    expected_mean: float,
) -> None:
    with open(os.path.join(input_folder, filename), "rb") as image_file:
        image_bytes = image_file.read()

    image = decode_image(image_bytes, get_data_format(filename))

    assert isinstance(image, np.ndarray)
    assert image.shape == expected_shape
    assert image.dtype == expected_dtype
    assert np.mean(image) == pytest.approx(expected_mean, rel=1e-4)


def test_tar(input_folder: str) -> None:
    tar_path = os.path.join(input_folder, "img.tar")
    with open(tar_path, "rb") as tar_file:
        tar_bytes = tar_file.read()

    tar_dict = decode_tar(tar_bytes)
    image, metadata = tar_dict["default.tif"], tar_dict["userdata.json"]

    assert isinstance(image, np.ndarray)
    assert image.shape == (856, 512, 3)

    assert "norm_factor" in metadata
    assert metadata["norm_factor"] == 0.0001


HTML_RESPONSE = (
    '<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>\n<title>Error 500 Request'
    " failed.</title>\n</head>\n<body><h2>HTTP ERROR 500</h2>\n<p>Problem accessing /oauth/tokeninfo. Reason:\n<pre>"
    " Request failed.</pre></p>\n</body>\n</html>\n"
)
PARSED_HTML = (
    "HTTP ERROR 500 Problem accessing /oauth/tokeninfo. Reason: Request failed."
)


@pytest.mark.parametrize(
    ("content", "expected_message"),
    [
        (None, ""),
        (False, ""),
        ("Text message!", "Text message!"),
        ('{"error": "Json message!"}', "Json message!"),
        ('{ "foo":  {"bar"  : 42}\n }', '{"foo": {"bar": 42}}'),
        (HTML_RESPONSE, PARSED_HTML),
    ],
)
def test_decode_sentinel_hub_error_msg(
    content: str | bool | None, expected_message: str
) -> None:
    response = Response()
    response._content = content.encode() if isinstance(content, str) else content

    decoded_message = decode_sentinel_hub_error_msg(response)
    assert decoded_message == expected_message
