import copy
import json
import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tomli_w

from sentinel_hub.constants import ServiceUrl

DEFAULT_PROFILE = "default-profile"
SH_PROFILE_ENV_VAR = "SH_PROFILE"
SH_CLIENT_ID_ENV_VAR = "SH_CLIENT_ID"
SH_CLIENT_SECRET_ENV_VAR = "SH_CLIENT_SECRET"


@dataclass(repr=False)
class _SHConfig:
    sh_client_id: str = ""
    sh_client_secret: str = ""
    sh_base_url: str = ServiceUrl.CDSE
    sh_token_url: str = ServiceUrl.CDSE_TOKEN
    max_download_attempts: int = 4
    download_sleep_time: float = 5.0
    download_timeout_seconds: float = 120.0
    number_of_download_processes: int = 1
    max_retries: int | None = None


class SHConfig(_SHConfig):
    """A sentinel-hub package configuration class."""

    CREDENTIALS = ("sh_client_id", "sh_client_secret")

    def __init__(
        self, profile: str | None = None, *, use_defaults: bool = False, **kwargs: Any
    ):
        profile = self._get_profile(profile)

        if not use_defaults:
            env_kwargs = {
                "sh_client_id": os.environ.get(SH_CLIENT_ID_ENV_VAR),
                "sh_client_secret": os.environ.get(SH_CLIENT_SECRET_ENV_VAR),
            }
            env_kwargs = {k: v for k, v in env_kwargs.items() if v is not None}

            # load from config.toml
            loaded_kwargs = SHConfig.load(profile=profile).to_dict(
                mask_credentials=False
            )

            kwargs = {
                **loaded_kwargs,
                **env_kwargs,
                **kwargs,
            }  # precedence: init params > env > loaded

        super().__init__(**kwargs)

    def __str__(self) -> str:
        """Content of `SHConfig` in json schema. Credentials are masked for safety."""
        return json.dumps(self.to_dict(mask_credentials=True), indent=2)

    def __repr__(self) -> str:
        """Representation of `SHConfig`. Credentials are masked for safety."""
        config_dict = self.to_dict(mask_credentials=True)
        content = ",\n ".join(f"{k}={v!r}" for k, v in config_dict.items())
        return f"{self.__class__.__name__}(\n {content},\n)"

    @staticmethod
    def _get_profile(profile: str | None) -> str:
        return (
            profile
            if profile is not None
            else os.environ.get(SH_PROFILE_ENV_VAR, default=DEFAULT_PROFILE)
        )

    @classmethod
    def get_config_location(cls) -> str:
        """Returns the configuration file from the parent of the repository."""
        return str(Path(__file__).resolve().parents[2] / "config.toml")

    @classmethod
    def load(cls, profile: str | None = None) -> SHConfig:
        """
        Loads configuration parameters from the config file at
        `SHConfig.get_config_location()`.
        """
        profile = cls._get_profile(profile=profile)
        filename = cls.get_config_location()

        if not os.path.exists(filename):
            cls(use_defaults=True).save()

        with open(filename, "rb") as file:
            configurations_dict = tomllib.load(file)

        if profile not in configurations_dict:
            raise KeyError(f"Profile `{profile}` not found in configuration file.")

        profile_config = {k.lower(): v for k, v in configurations_dict[profile].items()}
        return cls(use_defaults=True, **profile_config)

    def to_dict(self, mask_credentials: bool = True) -> dict[str, Any]:
        """Get a dictionary representation of the `SHConfig` class."""
        config_params = asdict(self)

        if mask_credentials:
            for param in self.CREDENTIALS:
                config_params[param] = self._mask_credentials(config_params[param])
        return config_params

    def _mask_credentials(self, value: str) -> str:
        """In case a parameter that holds credentials is given it will mask its value."""
        hide_size = min(max(len(value) - 4, 10), len(value))
        return "*" * hide_size + value[hide_size:]

    def save(self, profile: str | None = None) -> None:
        """
        Saves configuration parameters to the config file at
        `SHConfig.get_config_location()`.
        """
        profile = self._get_profile(profile=profile)
        file_path = Path(self.get_config_location())
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            with open(file_path, "rb") as file:
                current_configuration = tomllib.load(file)
        else:
            current_configuration = {}

        current_configuration[profile] = self._get_dict_of_diffs_from_defaults()
        with open(file_path, "wb") as file:
            tomli_w.dump(current_configuration, file)

    def _get_dict_of_diffs_from_defaults(self) -> dict[str, Any]:
        """
        Returns a dictionary containing key: value pairs for parameters
        that have values different from defaults.
        """
        current_profile_config = self.to_dict(mask_credentials=False)
        default_values = SHConfig(use_defaults=True).to_dict(mask_credentials=False)
        return {
            k: v for k, v in current_profile_config.items() if default_values[k] != v
        }

    def copy(self) -> SHConfig:
        """Makes a copy of an instance of `SHConfig`."""
        return copy.copy(self)
