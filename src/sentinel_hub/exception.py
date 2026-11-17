class BaseSHException(Exception):
    """A base package exception."""


class ImageDecodingError(BaseSHException):
    """This exception is raised when downloaded image is not properly decoded."""
