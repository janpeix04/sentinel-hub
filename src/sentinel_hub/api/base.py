from abc import ABCMeta, abstractmethod

from sentinel_hub.config import SHConfig
from sentinel_hub.download.sh_client import SHDownloadClient


class SHService(metaclass=ABCMeta):
    """A base class for classes interacting with different Sentinel Hub APIs."""

    _DEFAULT_RETRY_TIME = 30

    def __init__(self, config: SHConfig | None = None):
        self.config = config or SHConfig()

        base_url = self.config.sh_base_url.rstrip("/")
        self.service_url = self._get_service_url(base_url)

        self.client = SHDownloadClient(
            config=self.config, default_retry_time=self._DEFAULT_RETRY_TIME
        )

    @staticmethod
    @abstractmethod
    def _get_service_url(base_url: str) -> str:
        """Provides the URL to a specific service."""
