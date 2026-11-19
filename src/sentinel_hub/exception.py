import warnings

import requests


class BaseSHException(Exception):
    """A base package exception."""


class ImageDecodingError(BaseSHException):
    """This exception is raised when downloaded image is not properly decoded."""


class DownloadFailedException(BaseSHException):
    """General exception which is raised whenever download fails"""

    def __init__(
        self, msg: str, *, request_exception: requests.RequestException | None = None
    ) -> None:
        super().__init__(msg)
        self.request_exception = request_exception


class HashedNameCollisionException(BaseSHException):
    """This exception is raised when two different requests are assigned the same hashed name."""


class MissingDataInRequestException(BaseSHException):
    """This exception is raised when an iteration is performed on a request without data."""


class SHRuntimeWarning(RuntimeWarning):
    """A custom runtime warning for sentinel-hub package."""


class SHUserWarning(UserWarning):
    """A custom user warning for sentinel-hub package."""


warnings.simplefilter("always", SHRuntimeWarning)
warnings.simplefilter("default", SHUserWarning)
